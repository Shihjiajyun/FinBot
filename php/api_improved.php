<?php
require_once 'config.php';

// 檢查登入狀態
if (!isset($_SESSION['user_id'])) {
    json_response(['success' => false, 'error' => '請先登入'], 401);
}

$user_id = $_SESSION['user_id'];
$action = $_GET['action'] ?? $_POST['action'] ?? '';

try {
    $db = new Database();
    $pdo = $db->getConnection();

    switch ($action) {
        case 'ask':
            handleAsk();
            break;
        case 'stats':
            // 獲取統計資訊
            $stats = [];

            // 總財報數量
            $stmt = $pdo->query("SELECT COUNT(*) as count FROM filings");
            $stats['total_filings'] = $stmt->fetch()['count'];

            // 總問題數量
            $stmt = $pdo->query("SELECT COUNT(*) as count FROM questions");
            $stats['total_questions'] = $stmt->fetch()['count'];

            // 用戶問題數量
            $stmt = $pdo->prepare("SELECT COUNT(*) as count FROM user_questions WHERE user_id = ?");
            $stmt->execute([$user_id]);
            $stats['user_questions'] = $stmt->fetch()['count'];

            json_response(['success' => true, 'data' => $stats] + $stats);
            break;

        case 'get_conversations':
            getConversations();
            break;

        case 'get_conversation':
            getConversation();
            break;

        case 'new_conversation':
            // 創建新對話室
            $title = sanitize_input($_POST['title'] ?? '新對話');
            $conversation_id = createNewConversation($user_id, $pdo, $title);

            json_response(['success' => true, 'conversation_id' => $conversation_id]);
            break;

        case 'rename_conversation':
            renameConversation();
            break;

        default:
            json_response(['success' => false, 'error' => '無效的操作'], 400);
    }
} catch (Exception $e) {
    error_log("API Error: " . $e->getMessage());
    json_response(['success' => false, 'error' => '系統錯誤，請稍後再試'], 500);
}

function handleAsk()
{
    $question = sanitize_input($_POST['question'] ?? '');
    $conversation_id = $_POST['conversation_id'] ?? null;

    if (empty($question)) {
        throw new Exception('問題不能為空');
    }

    // 從問題中提取股票代碼
    $stock_symbol = extractStockSymbol($question);
    if (!$stock_symbol) {
        throw new Exception('請在問題中包含股票代碼，格式：[股票代碼] 您的問題');
    }

    $db = new Database();
    $pdo = $db->getConnection();

    // 初始化日誌數組
    $gpt_logs = [];

    // 步驟1: 檢查問題是否已經被問過
    $previous_answer = checkQuestionHistory($pdo, $question, $stock_symbol);
    if ($previous_answer) {
        error_log("=== 找到相同問題的歷史記錄 ===");

        // 保存對話（如果需要）
        if (!$conversation_id) {
            $conversation_id = createConversation($pdo, $question);
        }
        saveMessage($pdo, $conversation_id, $question, $previous_answer);

        json_response([
            'success' => true,
            'answer' => $previous_answer . "\n\n*（此答案來自歷史記錄）*",
            'conversation_id' => $conversation_id,
            'from_history' => true
        ]);
        return;
    }

    // 步驟2: 讓GPT分析問題需要什麼財報數據
    error_log("=== GPT 第一次通信 - 分析問題需要的財報類型 ===");
    $data_analysis = analyzeQuestionWithGPT($question, $stock_symbol, $gpt_logs);

    // 步驟3: 檢查資料庫是否有所需的財報數據
    $data_analysis_array = json_decode($data_analysis, true);
    if (!$data_analysis_array) {
        // 如果GPT分析失敗，預設獲取一些基本數據
        $data_analysis_array = [
            'need_form4' => false,
            'need_10k_years' => [2024, 2023],
            'need_10k_items' => ['item_7_content', 'item_8_content'],
            'need_13f_hr' => false,
            'need_13f_hr_years' => []
        ];
    }

    $missing_data = checkMissingFilingData($pdo, $stock_symbol, $data_analysis_array);

    // 步驟4: 如果缺少財報數據，自動下載和處理
    if (!empty($missing_data)) {
        error_log("=== 發現缺少財報數據，開始自動下載和處理 ===");
        $download_success = downloadAndProcessFilings($stock_symbol, $missing_data, $gpt_logs);

        if (!$download_success) {
            // 提供更詳細的錯誤信息
            $missing_info = formatMissingDataInfo($missing_data, $stock_symbol);
            throw new Exception("無法自動獲取所需的財報數據。缺少的數據：{$missing_info}。請檢查Python環境或稍後再試。");
        }
    }

    // 步驟5: 根據分析結果從資料庫抓取相關財報數據
    $filing_data = getRelevantFilingData($pdo, $stock_symbol, $data_analysis);

    // 步驟6: 將問題和財報數據一起發送給GPT獲得答案
    error_log("=== GPT 第二次通信 - 分析財報數據並回答問題 ===");
    $answer = getAnswerFromGPT($question, $stock_symbol, $filing_data, $data_analysis, $gpt_logs);

    // 保存對話
    if (!$conversation_id) {
        $conversation_id = createConversation($pdo, $question);
    }

    saveMessage($pdo, $conversation_id, $question, $answer);

    json_response([
        'success' => true,
        'answer' => $answer,
        'conversation_id' => $conversation_id,
        'data_analysis' => $data_analysis,
        'filing_data_summary' => summarizeFilingData($filing_data),
        'gpt_logs' => $gpt_logs,
        'missing_data_processed' => !empty($missing_data)
    ]);
}

function extractStockSymbol($question)
{
    // 從問題中提取股票代碼，格式如 [AAPL] 或 [AMZN]
    if (preg_match('/\[([A-Z]{1,5})\]/', $question, $matches)) {
        return $matches[1];
    }
    return null;
}

function analyzeQuestionWithGPT($question, $stock_symbol, &$gpt_logs)
{
    $system_prompt = "你是一個財報分析專家。請分析用戶的問題，判斷需要什麼類型的財報數據來回答問題。

我們的資料庫中有以下財報類型：
1. Form 4 (內部人交易數據) - 包含欄位: non_derivative_table, derivative_table
2. 10-K (年報數據) - 包含以下具體項目：
   - item_1_content (Item 1. Business - 業務描述)
   - item_1a_content (Item 1A. Risk Factors - 風險因素)
   - item_2_content (Item 2. Properties - 物業)
   - item_7_content (Item 7. MD&A - 管理層討論與分析)
   - item_7a_content (Item 7A. Market Risk - 市場風險)
   - item_8_content (Item 8. Financial Statements - 財務報表)
3. 13F-HR (機構持股報告) - 包含欄位: form_13f_hr_content (完整的13F-HR持股數據)

請根據問題內容，具體指定需要哪些財報文件和項目：

請只返回JSON格式，包含：
{
    \"need_form4\": true/false,
    \"need_10k_years\": [2024, 2023, ...] (需要哪些年份的10-K，如果不需要則為空陣列),
    \"need_10k_items\": [\"item_1_content\", \"item_7_content\", ...] (需要10-K中的哪些具體項目),
    \"need_13f_hr\": true/false,
    \"need_13f_hr_years\": [2024, 2023, ...] (需要哪些年份的13F-HR，如果不需要則為空陣列),
    \"analysis_reason\": \"簡短說明為什麼需要這些特定年份和項目的數據\",
    \"specific_requirements\": \"例如：需要AMZN 2024年10-K的業務描述和管理層分析，以及2023-2024年的13F-HR持股數據\"
}";

    $user_prompt = "股票代碼: {$stock_symbol}\n問題: {$question}";

    // 記錄第一次GPT通信
    $gpt_logs['first_request'] = [
        'purpose' => '分析問題需要的財報類型',
        'system_prompt' => $system_prompt,
        'user_prompt' => $user_prompt,
        'timestamp' => date('Y-m-d H:i:s')
    ];

    error_log("GPT第一次請求 - System Prompt: " . $system_prompt);
    error_log("GPT第一次請求 - User Prompt: " . $user_prompt);

    $response = callOpenAI($system_prompt, $user_prompt);

    $gpt_logs['first_response'] = [
        'response' => $response,
        'timestamp' => date('Y-m-d H:i:s')
    ];

    error_log("GPT第一次回應: " . $response);

    return $response;
}

function getRelevantFilingData($pdo, $stock_symbol, $data_analysis)
{
    $data_analysis_array = json_decode($data_analysis, true);
    if (!$data_analysis_array) {
        // 如果GPT分析失敗，預設獲取一些基本數據
        $data_analysis_array = [
            'need_form4' => false,
            'need_10k_years' => [2024, 2023],
            'need_10k_items' => ['item_7_content', 'item_8_content'],
            'need_13f_hr' => false,
            'need_13f_hr_years' => [2024, 2023]
        ];
    }

    $filing_data = [];

    // 根據股票代碼映射到公司名稱
    $company_mapping = [
        'AMZN' => 'AMAZON COM INC',
        'AAPL' => 'APPLE INC',
        'MSFT' => 'MICROSOFT CORP',
        'TSLA' => 'TESLA INC',
        'META' => 'META PLATFORMS INC'
    ];

    $company_name = $company_mapping[$stock_symbol] ?? $stock_symbol;

    // 記錄查詢信息
    error_log("正在查詢財報數據 - 公司: {$company_name}, 股票代碼: {$stock_symbol}");
    error_log("GPT需求分析: " . json_encode($data_analysis_array, JSON_UNESCAPED_UNICODE));

    // 獲取Form 4數據
    if ($data_analysis_array['need_form4']) {
        $form4_sql = "SELECT * FROM filings 
                      WHERE filing_type = '4' 
                      AND (company_name LIKE ? OR cik IN (SELECT DISTINCT cik FROM filings WHERE company_name LIKE ?))
                      ORDER BY report_date DESC 
                      LIMIT 10";

        $stmt = $pdo->prepare($form4_sql);
        $search_pattern = "%{$company_name}%";
        $stmt->execute([$search_pattern, $search_pattern]);
        $filing_data['form4_data'] = $stmt->fetchAll();

        error_log("找到 Form 4 數據: " . count($filing_data['form4_data']) . " 筆");
    }

    // 獲取10-K數據
    if (!empty($data_analysis_array['need_10k_items'])) {
        $columns = ['id', 'cik', 'company_name', 'filing_type', 'filing_year', 'report_date', 'accession_number'];
        $columns = array_merge($columns, $data_analysis_array['need_10k_items']);
        $columns_str = implode(', ', $columns);

        // 構建年份條件
        $year_condition = "";
        $params = ["%{$company_name}%", "%{$company_name}%"];

        if (!empty($data_analysis_array['need_10k_years'])) {
            $year_placeholders = str_repeat('?,', count($data_analysis_array['need_10k_years']) - 1) . '?';
            $year_condition = " AND filing_year IN ({$year_placeholders})";
            $params = array_merge($params, $data_analysis_array['need_10k_years']);
        }

        $form10k_sql = "SELECT {$columns_str} FROM filings 
                        WHERE filing_type = '10-K' 
                        AND (company_name LIKE ? OR cik IN (SELECT DISTINCT cik FROM filings WHERE company_name LIKE ?))
                        {$year_condition}
                        ORDER BY filing_year DESC 
                        LIMIT 10";

        error_log("10-K 查詢SQL: " . $form10k_sql);
        error_log("查詢參數: " . json_encode($params));

        $stmt = $pdo->prepare($form10k_sql);
        $stmt->execute($params);
        $filing_data['form10k_data'] = $stmt->fetchAll();

        error_log("找到 10-K 數據: " . count($filing_data['form10k_data']) . " 筆");

        // 記錄找到的具體年份
        if (!empty($filing_data['form10k_data'])) {
            $found_years = array_unique(array_column($filing_data['form10k_data'], 'filing_year'));
            error_log("找到的10-K年份: " . implode(', ', $found_years));
        }
    }

    // 獲取13F-HR數據
    if ($data_analysis_array['need_13f_hr']) {
        $year_condition = "";
        $params = ["%{$company_name}%", "%{$company_name}%"];

        if (!empty($data_analysis_array['need_13f_hr_years'])) {
            $year_placeholders = str_repeat('?,', count($data_analysis_array['need_13f_hr_years']) - 1) . '?';
            $year_condition = " AND filing_year IN ({$year_placeholders})";
            $params = array_merge($params, $data_analysis_array['need_13f_hr_years']);
        }

        $form13f_sql = "SELECT id, cik, company_name, filing_type, filing_year, report_date, accession_number, form_13f_hr_content
                        FROM filings 
                        WHERE filing_type = '13F-HR' 
                        AND (company_name LIKE ? OR cik IN (SELECT DISTINCT cik FROM filings WHERE company_name LIKE ?))
                        {$year_condition}
                        ORDER BY filing_year DESC, report_date DESC 
                        LIMIT 10";

        error_log("13F-HR 查詢SQL: " . $form13f_sql);
        error_log("查詢參數: " . json_encode($params));

        $stmt = $pdo->prepare($form13f_sql);
        $stmt->execute($params);
        $filing_data['form13f_data'] = $stmt->fetchAll();

        error_log("找到 13F-HR 數據: " . count($filing_data['form13f_data']) . " 筆");

        // 記錄找到的具體年份
        if (!empty($filing_data['form13f_data'])) {
            $found_years = array_unique(array_column($filing_data['form13f_data'], 'filing_year'));
            error_log("找到的13F-HR年份: " . implode(', ', $found_years));
        }
    }

    return $filing_data;
}

function getAnswerFromGPT($question, $stock_symbol, $filing_data, $data_analysis, &$gpt_logs)
{
    $system_prompt = "你是一個專業的財報分析師，專門分析美國上市公司的SEC財報文件。

請根據提供的財報數據回答用戶問題。注意：
1. 只基於提供的實際財報數據進行分析
2. 如果數據不足以回答問題，請說明
3. 提供具體的數字和日期
4. 解釋財務指標的含義
5. 回答要專業但容易理解
6. 用繁體中文回答

財報數據說明：
- Form 4: 內部人交易報告，包含高管和董事的股票交易
- 10-K Item 1: 業務描述
- 10-K Item 1A: 風險因素  
- 10-K Item 2: 物業資訊
- 10-K Item 7: 管理層討論與分析(MD&A)
- 10-K Item 7A: 市場風險
- 10-K Item 8: 財務報表
- 13F-HR: 機構持股報告，包含機構投資者的持股資訊";

    // 解析GPT的第一次分析結果
    $analysis_result = json_decode($data_analysis, true);

    // 準備財報數據摘要
    $data_summary = "股票代碼: {$stock_symbol}\n";
    $data_summary .= "GPT分析需求: {$data_analysis}\n\n";

    // 處理Form 4數據
    if (!empty($filing_data['form4_data'])) {
        $data_summary .= "=== 找到的 Form 4 內部人交易數據 ===\n";
        $data_summary .= "共找到 " . count($filing_data['form4_data']) . " 筆Form 4記錄\n\n";

        foreach (array_slice($filing_data['form4_data'], 0, 5) as $index => $form4) {
            $form_number = $index + 1;
            $data_summary .= "Form 4 #{$form_number}:\n";
            $data_summary .= "- 公司: {$form4['company_name']}\n";
            $data_summary .= "- 報告日期: {$form4['report_date']}\n";
            $data_summary .= "- 申報編號: {$form4['accession_number']}\n";

            if (!empty($form4['non_derivative_table'])) {
                $data_summary .= "- 非衍生性證券交易:\n" . substr($form4['non_derivative_table'], 0, 800) . "...\n";
            }
            if (!empty($form4['derivative_table'])) {
                $data_summary .= "- 衍生性證券交易:\n" . substr($form4['derivative_table'], 0, 800) . "...\n";
            }
            $data_summary .= "---\n\n";
        }
    }

    // 處理10-K數據
    if (!empty($filing_data['form10k_data'])) {
        $data_summary .= "=== 找到的 10-K 年報數據 ===\n";
        $data_summary .= "共找到 " . count($filing_data['form10k_data']) . " 筆10-K記錄\n\n";

        foreach ($filing_data['form10k_data'] as $index => $form10k) {
            $form_number = $index + 1;
            $data_summary .= "10-K #{$form_number}:\n";
            $data_summary .= "- 公司: {$form10k['company_name']}\n";
            $data_summary .= "- 財報年份: {$form10k['filing_year']}\n";
            $data_summary .= "- 報告日期: {$form10k['report_date']}\n";
            $data_summary .= "- 申報編號: {$form10k['accession_number']}\n";

            // 根據需要的項目添加數據
            $items_mapping = [
                'item_1_content' => 'Item 1. Business (業務描述)',
                'item_1a_content' => 'Item 1A. Risk Factors (風險因素)',
                'item_2_content' => 'Item 2. Properties (物業)',
                'item_7_content' => 'Item 7. Management Discussion and Analysis (管理層討論與分析)',
                'item_7a_content' => 'Item 7A. Market Risk (市場風險)',
                'item_8_content' => 'Item 8. Financial Statements (財務報表)'
            ];

            foreach ($items_mapping as $column => $description) {
                if (!empty($form10k[$column])) {
                    $content_length = strlen($form10k[$column]);
                    $data_summary .= "\n{$description} (長度: {$content_length} 字符):\n";
                    $data_summary .= substr($form10k[$column], 0, 4000) . "...\n";
                }
            }
            $data_summary .= "================\n\n";
        }
    }

    // 處理13F-HR數據
    if (!empty($filing_data['form13f_data'])) {
        $data_summary .= "=== 找到的 13F-HR 機構持股數據 ===\n";
        $data_summary .= "共找到 " . count($filing_data['form13f_data']) . " 筆13F-HR記錄\n\n";

        foreach ($filing_data['form13f_data'] as $index => $form13f) {
            $form_number = $index + 1;
            $data_summary .= "13F-HR #{$form_number}:\n";
            $data_summary .= "- 公司: {$form13f['company_name']}\n";
            $data_summary .= "- 財報年份: {$form13f['filing_year']}\n";
            $data_summary .= "- 報告日期: {$form13f['report_date']}\n";
            $data_summary .= "- 申報編號: {$form13f['accession_number']}\n";

            if (!empty($form13f['form_13f_hr_content'])) {
                $content_length = strlen($form13f['form_13f_hr_content']);
                $data_summary .= "\n13F-HR 持股報告內容 (長度: {$content_length} 字符):\n";
                $data_summary .= substr($form13f['form_13f_hr_content'], 0, 3000) . "...\n";
            }
            $data_summary .= "================\n\n";
        }
    }

    if (empty($filing_data['form4_data']) && empty($filing_data['form10k_data']) && empty($filing_data['form13f_data'])) {
        $data_summary .= "未找到相關財報數據。可能原因：\n";
        $data_summary .= "1. 股票代碼不正確\n";
        $data_summary .= "2. 該公司的財報數據尚未處理\n";
        $data_summary .= "3. 目前只有AMZN的完整數據\n";
    }

    $user_prompt = "問題: {$question}\n\n財報數據:\n{$data_summary}";

    // 記錄第二次GPT通信
    $gpt_logs['second_request'] = [
        'purpose' => '分析財報數據並回答問題',
        'system_prompt' => $system_prompt,
        'user_prompt' => $user_prompt,
        'data_summary_length' => strlen($data_summary),
        'filing_data_info' => [
            'form4_count' => !empty($filing_data['form4_data']) ? count($filing_data['form4_data']) : 0,
            'form10k_count' => !empty($filing_data['form10k_data']) ? count($filing_data['form10k_data']) : 0,
            'form13f_count' => !empty($filing_data['form13f_data']) ? count($filing_data['form13f_data']) : 0
        ],
        'timestamp' => date('Y-m-d H:i:s')
    ];

    error_log("GPT第二次請求 - System Prompt: " . $system_prompt);
    error_log("GPT第二次請求 - User Prompt (前1000字符): " . substr($user_prompt, 0, 1000));
    error_log("GPT第二次請求 - 完整數據長度: " . strlen($user_prompt) . " 字符");

    $response = callOpenAI($system_prompt, $user_prompt);

    $gpt_logs['second_response'] = [
        'response' => $response,
        'response_length' => strlen($response),
        'timestamp' => date('Y-m-d H:i:s')
    ];

    error_log("GPT第二次回應 (前500字符): " . substr($response, 0, 500));
    error_log("GPT第二次回應完整長度: " . strlen($response) . " 字符");

    return $response;
}

function callOpenAI($system_prompt, $user_prompt)
{
    $api_key = defined('OPENAI_API_KEY') ? OPENAI_API_KEY : (getenv('OPENAI_API_KEY') ?: 'your-openai-api-key-here');

    $data = [
        'model' => 'gpt-4o-mini',
        'messages' => [
            [
                'role' => 'system',
                'content' => $system_prompt
            ],
            [
                'role' => 'user',
                'content' => $user_prompt
            ]
        ],
        'max_tokens' => 2000,
        'temperature' => 0.3
    ];

    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, 'https://api.openai.com/v1/chat/completions');
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: application/json',
        'Authorization: Bearer ' . $api_key
    ]);

    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($httpCode !== 200) {
        throw new Exception('OpenAI API 調用失敗：' . $response);
    }

    $result = json_decode($response, true);

    if (!isset($result['choices'][0]['message']['content'])) {
        throw new Exception('OpenAI API 返回格式錯誤');
    }

    return $result['choices'][0]['message']['content'];
}

function summarizeFilingData($filing_data)
{
    $summary = [];

    if (!empty($filing_data['form4_data'])) {
        $summary['form4_count'] = count($filing_data['form4_data']);
        $summary['form4_date_range'] = [
            'latest' => $filing_data['form4_data'][0]['report_date'] ?? null,
            'earliest' => end($filing_data['form4_data'])['report_date'] ?? null
        ];
    }

    if (!empty($filing_data['form10k_data'])) {
        $summary['form10k_count'] = count($filing_data['form10k_data']);
        $years = array_column($filing_data['form10k_data'], 'filing_year');
        $summary['form10k_years'] = array_unique($years);
    }

    if (!empty($filing_data['form13f_data'])) {
        $summary['form13f_count'] = count($filing_data['form13f_data']);
        $years = array_column($filing_data['form13f_data'], 'filing_year');
        $summary['form13f_years'] = array_unique($years);
        $summary['form13f_date_range'] = [
            'latest' => $filing_data['form13f_data'][0]['report_date'] ?? null,
            'earliest' => end($filing_data['form13f_data'])['report_date'] ?? null
        ];
    }

    return $summary;
}

function createConversation($pdo, $question)
{
    $stmt = $pdo->prepare("INSERT INTO conversations (user_id, title, created_at) VALUES (?, ?, NOW())");
    $title = mb_substr($question, 0, 50) . (mb_strlen($question) > 50 ? '...' : '');
    $stmt->execute([$_SESSION['user_id'], $title]);
    return $pdo->lastInsertId();
}

function saveMessage($pdo, $conversation_id, $question, $answer)
{
    // 先插入到 questions 表
    $stmt = $pdo->prepare("INSERT INTO questions (conversation_id, question, answer, created_by, created_at) VALUES (?, ?, ?, ?, NOW())");
    $stmt->execute([$conversation_id, $question, $answer, $_SESSION['user_id']]);

    $question_id = $pdo->lastInsertId();

    // 再插入到 user_questions 表
    $stmt = $pdo->prepare("INSERT INTO user_questions (user_id, question_id, conversation_id, asked_at) VALUES (?, ?, ?, NOW())");
    $stmt->execute([$_SESSION['user_id'], $question_id, $conversation_id]);
}

function getConversations()
{
    $db = new Database();
    $pdo = $db->getConnection();

    $stmt = $pdo->prepare("
        SELECT c.*, 
               (SELECT question FROM questions WHERE conversation_id = c.id ORDER BY created_at DESC LIMIT 1) as last_question
        FROM conversations c 
        WHERE c.user_id = ? 
        ORDER BY c.updated_at DESC, c.created_at DESC 
        LIMIT 20
    ");
    $stmt->execute([$_SESSION['user_id']]);
    $conversations = $stmt->fetchAll();

    json_response(['success' => true, 'conversations' => $conversations]);
}

function getConversation()
{
    $conversation_id = $_GET['id'] ?? '';

    if (empty($conversation_id)) {
        throw new Exception('對話ID不能為空');
    }

    $db = new Database();
    $pdo = $db->getConnection();

    $stmt = $pdo->prepare("SELECT * FROM questions WHERE conversation_id = ? ORDER BY created_at ASC");
    $stmt->execute([$conversation_id]);
    $messages = $stmt->fetchAll();

    json_response([
        'success' => true,
        'messages' => $messages
    ]);
}

function renameConversation()
{
    $conversation_id = $_POST['conversation_id'] ?? '';
    $title = sanitize_input($_POST['title'] ?? '');

    if (empty($conversation_id) || empty($title)) {
        throw new Exception('對話ID和標題不能為空');
    }

    $db = new Database();
    $pdo = $db->getConnection();

    $stmt = $pdo->prepare("UPDATE conversations SET title = ?, updated_at = NOW() WHERE id = ? AND user_id = ?");
    $stmt->execute([$title, $conversation_id, $_SESSION['user_id']]);

    if ($stmt->rowCount() === 0) {
        throw new Exception('更新失敗，請檢查權限');
    }

    json_response([
        'success' => true,
        'message' => '對話標題已更新'
    ]);
}

function checkQuestionHistory($pdo, $question, $stock_symbol)
{
    // 檢查是否有相同的問題（考慮股票代碼）
    $normalized_question = normalizeQuestion($question);

    $stmt = $pdo->prepare("
        SELECT answer FROM questions 
        WHERE LOWER(TRIM(question)) = LOWER(TRIM(?)) 
        AND question LIKE CONCAT('%[', ?, ']%')
        ORDER BY created_at DESC 
        LIMIT 1
    ");
    $stmt->execute([$normalized_question, $stock_symbol]);
    $result = $stmt->fetch();

    return $result ? $result['answer'] : null;
}

function normalizeQuestion($question)
{
    // 移除股票代碼部分，只保留問題本身
    $question = preg_replace('/\[[A-Z]{1,5}\]\s*/', '', $question);
    return trim($question);
}

function checkMissingFilingData($pdo, $stock_symbol, $data_analysis)
{
    $missing_data = [];

    // 根據股票代碼映射到公司名稱
    $company_mapping = [
        'AMZN' => 'AMAZON COM INC',
        'AAPL' => 'APPLE INC',
        'MSFT' => 'MICROSOFT CORP',
        'TSLA' => 'TESLA INC',
        'META' => 'META PLATFORMS INC',
        'GOOGL' => 'ALPHABET INC',
        'GOOG' => 'ALPHABET INC',
        'NVDA' => 'NVIDIA CORP'
    ];

    $company_name = $company_mapping[$stock_symbol] ?? $stock_symbol;

    // 檢查Form 4數據
    if ($data_analysis['need_form4']) {
        $stmt = $pdo->prepare("
            SELECT COUNT(*) as count FROM filings 
            WHERE filing_type = '4' 
            AND (company_name LIKE ? OR cik IN (SELECT DISTINCT cik FROM filings WHERE company_name LIKE ?))
        ");
        $search_pattern = "%{$company_name}%";
        $stmt->execute([$search_pattern, $search_pattern]);
        $count = $stmt->fetch()['count'];

        if ($count == 0) {
            $missing_data['form4'] = true;
        }
    }

    // 檢查10-K數據
    if (!empty($data_analysis['need_10k_years'])) {
        foreach ($data_analysis['need_10k_years'] as $year) {
            $stmt = $pdo->prepare("
                SELECT COUNT(*) as count FROM filings 
                WHERE filing_type = '10-K' 
                AND filing_year = ?
                AND (company_name LIKE ? OR cik IN (SELECT DISTINCT cik FROM filings WHERE company_name LIKE ?))
            ");
            $search_pattern = "%{$company_name}%";
            $stmt->execute([$year, $search_pattern, $search_pattern]);
            $count = $stmt->fetch()['count'];

            if ($count == 0) {
                if (!isset($missing_data['10k_years'])) {
                    $missing_data['10k_years'] = [];
                }
                $missing_data['10k_years'][] = $year;
            }
        }
    }

    // 檢查13F-HR數據
    if ($data_analysis['need_13f_hr'] && !empty($data_analysis['need_13f_hr_years'])) {
        foreach ($data_analysis['need_13f_hr_years'] as $year) {
            $stmt = $pdo->prepare("
                SELECT COUNT(*) as count FROM filings 
                WHERE filing_type = '13F-HR' 
                AND filing_year = ?
                AND (company_name LIKE ? OR cik IN (SELECT DISTINCT cik FROM filings WHERE company_name LIKE ?))
            ");
            $search_pattern = "%{$company_name}%";
            $stmt->execute([$year, $search_pattern, $search_pattern]);
            $count = $stmt->fetch()['count'];

            if ($count == 0) {
                if (!isset($missing_data['13f_hr_years'])) {
                    $missing_data['13f_hr_years'] = [];
                }
                $missing_data['13f_hr_years'][] = $year;
            }
        }
    }

    return $missing_data;
}

function testPythonEnvironment()
{
    // 常見的Python路徑（根據您的環境調整）
    $python_paths = [
        'C:\\Users\\shihj\\anaconda3\\python.exe',  // 您的Anaconda路徑
        'python',     // 嘗試PATH中的python
        'python3',    // 嘗試PATH中的python3
        'C:\\Python39\\python.exe',
        'C:\\Python38\\python.exe',
        'C:\\Python37\\python.exe'
    ];

    // 獲取正確的工作目錄和腳本路徑
    $current_dir = dirname(__DIR__);  // FinBot目錄
    $script_path = $current_dir . DIRECTORY_SEPARATOR . 'test_basic.py';

    foreach ($python_paths as $python_path) {
        $command = "\"{$python_path}\" \"{$script_path}\"";
        error_log("測試Python路徑: {$command}");
        error_log("測試工作目錄: {$current_dir}");

        // 切換到正確的工作目錄
        $old_cwd = getcwd();
        chdir($current_dir);

        $output = [];
        $return_code = 0;
        exec($command . ' 2>&1', $output, $return_code);

        // 恢復原來的工作目錄
        chdir($old_cwd);

        error_log("Python測試輸出: " . implode("\n", $output));
        error_log("Python測試返回碼: {$return_code}");

        if ($return_code === 0) {
            return [
                'success' => true,
                'output' => $output,
                'return_code' => $return_code,
                'python_command' => $python_path
            ];
        }
    }

    // 所有路徑都失敗
    return [
        'success' => false,
        'output' => ['所有Python路徑都測試失敗'],
        'return_code' => 9009,
        'error' => 'No working Python installation found'
    ];
}

function downloadAndProcessFilings($stock_symbol, $missing_data, &$gpt_logs)
{
    error_log("開始下載缺少的財報數據: " . json_encode($missing_data));

    // 首先測試Python環境
    $python_test = testPythonEnvironment();
    $gpt_logs['python_test'] = $python_test;

    if (!$python_test['success']) {
        error_log("Python環境測試失敗，無法繼續");
        error_log("Python錯誤詳情: " . print_r($python_test, true));
        return false;
    }

    // 獲取正確的Python命令
    $python_command = $python_test['python_command'] ?? 'python';

    // 準備要下載的財報類型
    $filing_types = [];
    $years_to_download = [];

    if (isset($missing_data['form4'])) {
        $filing_types[] = '4';
    }

    if (isset($missing_data['10k_years'])) {
        $filing_types[] = '10-K';
        $years_to_download = array_merge($years_to_download, $missing_data['10k_years']);
    }

    if (isset($missing_data['13f_hr_years'])) {
        $filing_types[] = '13F-HR';
        $years_to_download = array_merge($years_to_download, $missing_data['13f_hr_years']);
    }

    if (empty($filing_types)) {
        return true; // 沒有需要下載的
    }

    $years_to_download = array_unique($years_to_download);

    // 記錄下載過程
    $gpt_logs['download_process'] = [
        'stock_symbol' => $stock_symbol,
        'filing_types' => $filing_types,
        'years' => $years_to_download,
        'start_time' => date('Y-m-d H:i:s')
    ];

    // 步驟1: 執行下載
    $download_success = executeDownloadScript($stock_symbol, $filing_types, $years_to_download, $python_command);

    if (!$download_success) {
        error_log("下載財報失敗: {$stock_symbol}");
        return false;
    }

    // 步驟2: 處理下載的文件
    $process_success = executeProcessScript($stock_symbol, $python_command);

    if (!$process_success) {
        error_log("處理財報失敗: {$stock_symbol}");
        return false;
    }

    $gpt_logs['download_process']['end_time'] = date('Y-m-d H:i:s');
    $gpt_logs['download_process']['success'] = true;

    error_log("成功下載並處理財報數據: {$stock_symbol}");
    return true;
}

function executeDownloadScript($stock_symbol, $filing_types, $years, $python_command = 'python')
{
    // 獲取正確的工作目錄和腳本路徑
    $current_dir = dirname(__DIR__);  // FinBot目錄
    $script_path = $current_dir . DIRECTORY_SEPARATOR . 'download_filings.py';

    // 構建命令
    $filing_types_str = implode(',', $filing_types);
    $years_str = !empty($years) ? implode(',', $years) : '';

    $command = "\"{$python_command}\" \"{$script_path}\" {$stock_symbol} \"{$filing_types_str}\"";
    if (!empty($years_str)) {
        $command .= " \"{$years_str}\"";
    }

    error_log("執行下載命令: {$command}");
    error_log("工作目錄: {$current_dir}");

    // 切換到正確的工作目錄並執行命令
    $old_cwd = getcwd();
    chdir($current_dir);

    $output = [];
    $return_code = 0;
    exec($command . ' 2>&1', $output, $return_code);

    // 恢復原來的工作目錄
    chdir($old_cwd);

    error_log("下載腳本輸出: " . implode("\n", $output));
    error_log("下載腳本返回碼: {$return_code}");

    return $return_code === 0;
}

function executeProcessScript($stock_symbol, $python_command = 'python')
{
    // 獲取正確的工作目錄和腳本路徑
    $current_dir = dirname(__DIR__);  // FinBot目錄
    $script_path = $current_dir . DIRECTORY_SEPARATOR . 'process_filings.py';

    $command = "\"{$python_command}\" \"{$script_path}\" {$stock_symbol}";

    error_log("執行處理命令: {$command}");
    error_log("工作目錄: {$current_dir}");

    // 切換到正確的工作目錄並執行命令
    $old_cwd = getcwd();
    chdir($current_dir);

    $output = [];
    $return_code = 0;
    exec($command . ' 2>&1', $output, $return_code);

    // 恢復原來的工作目錄
    chdir($old_cwd);

    error_log("處理腳本輸出: " . implode("\n", $output));
    error_log("處理腳本返回碼: {$return_code}");

    return $return_code === 0;
}

function formatMissingDataInfo($missing_data, $stock_symbol)
{
    $info_parts = [];

    if (isset($missing_data['form4'])) {
        $info_parts[] = "Form 4 內部人交易數據";
    }

    if (isset($missing_data['10k_years']) && !empty($missing_data['10k_years'])) {
        $years = implode(', ', $missing_data['10k_years']);
        $info_parts[] = "10-K 年報數據 ({$years}年)";
    }

    if (isset($missing_data['13f_hr_years']) && !empty($missing_data['13f_hr_years'])) {
        $years = implode(', ', $missing_data['13f_hr_years']);
        $info_parts[] = "13F-HR 機構持股數據 ({$years}年)";
    }

    return $stock_symbol . ' - ' . implode(', ', $info_parts);
}
