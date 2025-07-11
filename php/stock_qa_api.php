<?php
require_once 'config.php';

header('Content-Type: application/json');

// 檢查登入狀態
if (!isset($_SESSION['user_id'])) {
    echo json_encode(['success' => false, 'error' => '請先登入']);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(['success' => false, 'error' => '僅支援 POST 請求']);
    exit;
}

$action = $_POST['action'] ?? '';
$ticker = strtoupper(trim($_POST['ticker'] ?? ''));

// 某些操作不需要股票代號
$actionsWithoutTicker = ['get_conversation_history', 'get_conversation_messages'];

if (!in_array($action, $actionsWithoutTicker)) {
    if (empty($ticker)) {
        echo json_encode(['success' => false, 'error' => '股票代號不能為空']);
        exit;
    }

    // 驗證股票代號格式
    if (!preg_match('/^[A-Z0-9]{1,10}$/', $ticker)) {
        echo json_encode(['success' => false, 'error' => '股票代號格式錯誤']);
        exit;
    }
}

try {
    $db = new Database();
    $pdo = $db->getConnection();

    switch ($action) {
        case 'get_stock_qa_history':
            getStockQAHistory($pdo, $ticker);
            break;

        case 'ask_stock_question':
            askStockQuestion($pdo, $ticker);
            break;

        case 'ask_10k_question':
            ask10KQuestion($pdo, $ticker);
            break;

        case 'get_conversation_history':
            getConversationHistory($pdo);
            break;

        case 'get_conversation_messages':
            getConversationMessages($pdo);
            break;

        case 'update_conversation_title':
            $conversationId = $_POST['conversation_id'] ?? '';
            $newTitle = trim($_POST['new_title'] ?? '');

            if (empty($conversationId) || empty($newTitle)) {
                echo json_encode(['success' => false, 'error' => '參數不完整']);
                exit;
            }

            $result = updateConversationTitle($pdo, $conversationId, $newTitle, $_SESSION['user_id']);
            echo json_encode($result);
            exit;

        default:
            echo json_encode(['success' => false, 'error' => '未知的操作']);
    }
} catch (Exception $e) {
    error_log("股票問答API錯誤: " . $e->getMessage());
    echo json_encode(['success' => false, 'error' => '伺服器錯誤，請稍後再試']);
}

/**
 * 獲取股票問答歷史
 */
function getStockQAHistory($pdo, $ticker)
{
    try {
        // 查詢該股票的對話記錄
        $stmt = $pdo->prepare("
            SELECT 
                c.id as conversation_id,
                c.title,
                c.created_at as conversation_created_at
            FROM conversations c 
            WHERE c.user_id = ? AND c.title = ?
            ORDER BY c.updated_at DESC
            LIMIT 1
        ");
        $stmt->execute([$_SESSION['user_id'], $ticker]);
        $conversation = $stmt->fetch(PDO::FETCH_ASSOC);

        if (!$conversation) {
            echo json_encode(['success' => true, 'qa_history' => []]);
            return;
        }

        // 獲取該對話的問答記錄
        $stmt = $pdo->prepare("
            SELECT 
                q.id,
                q.question,
                q.answer,
                q.created_at,
                CASE 
                    WHEN EXISTS (
                        SELECT 1 FROM questions q2 
                        WHERE q2.question = q.question 
                        AND q2.id < q.id 
                        AND q2.created_by != q.created_by
                    ) THEN 1 
                    ELSE 0 
                END as is_cached
            FROM questions q
            WHERE q.conversation_id = ?
            ORDER BY q.created_at ASC
        ");
        $stmt->execute([$conversation['conversation_id']]);
        $qaHistory = $stmt->fetchAll(PDO::FETCH_ASSOC);

        echo json_encode([
            'success' => true,
            'qa_history' => $qaHistory,
            'conversation_id' => $conversation['conversation_id']
        ]);
    } catch (Exception $e) {
        error_log("獲取問答歷史錯誤: " . $e->getMessage());
        echo json_encode(['success' => false, 'error' => '獲取對話歷史失敗']);
    }
}

/**
 * 處理股票問題
 */
function askStockQuestion($pdo, $ticker)
{
    $question = trim($_POST['question'] ?? '');

    if (empty($question)) {
        echo json_encode(['success' => false, 'error' => '問題不能為空']);
        return;
    }

    try {
        // 1. 檢查是否有相同問題的快取答案
        $cachedAnswer = getCachedAnswer($pdo, $question);
        $isCached = false;

        if ($cachedAnswer) {
            $answer = $cachedAnswer;
            $isCached = true;
            error_log("使用快取答案: " . substr($question, 0, 50) . "...");
        } else {
            // 2. 獲取10-K摘要資料
            $summaryData = getTenKSummaryData($pdo, $ticker);

            if (!$summaryData) {
                echo json_encode([
                    'success' => false,
                    'error' => "目前沒有 $ticker 的 10-K 報告摘要資料，請稍後再試"
                ]);
                return;
            }

            // 3. 調用GPT生成答案
            $answer = generateGPTAnswer($question, $summaryData, $ticker);

            if (!$answer) {
                echo json_encode(['success' => false, 'error' => 'GPT 回答生成失敗，請稍後再試']);
                return;
            }
        }

        // 4. 獲取或創建對話
        $conversationId = getOrCreateConversation($pdo, $_SESSION['user_id'], $ticker);

        // 5. 儲存問答記錄
        $questionId = saveQuestionAnswer($pdo, $conversationId, $question, $answer, $_SESSION['user_id']);

        // 6. 記錄用戶問題歷史
        saveUserQuestionHistory($pdo, $_SESSION['user_id'], $questionId, $conversationId);

        echo json_encode([
            'success' => true,
            'answer' => $answer,
            'is_cached' => $isCached,
            'question_id' => $questionId,
            'conversation_id' => $conversationId
        ]);
    } catch (Exception $e) {
        error_log("處理股票問題錯誤: " . $e->getMessage());
        echo json_encode(['success' => false, 'error' => '處理問題時發生錯誤']);
    }
}

/**
 * 獲取快取答案
 */
function getCachedAnswer($pdo, $question)
{
    $stmt = $pdo->prepare("
        SELECT answer 
        FROM questions 
        WHERE question = ? 
        ORDER BY created_at DESC 
        LIMIT 1
    ");
    $stmt->execute([$question]);
    $result = $stmt->fetch(PDO::FETCH_ASSOC);

    return $result ? $result['answer'] : null;
}

/**
 * 獲取10-K摘要資料
 */
function getTenKSummaryData($pdo, $ticker)
{
    try {
        $filing = null;

        // 現在 company_name 欄位直接存儲股票代號，可以直接比對
        $stmt = $pdo->prepare("
            SELECT id, company_name, report_date, file_name
            FROM ten_k_filings 
            WHERE UPPER(TRIM(company_name)) = UPPER(TRIM(?))
            ORDER BY report_date DESC 
            LIMIT 1
        ");
        $stmt->execute([$ticker]);
        $filing = $stmt->fetch(PDO::FETCH_ASSOC);

        error_log("直接查詢股票代號 $ticker: " . ($filing ? "找到" : "未找到"));

        // 如果直接查詢找不到，嘗試部分匹配
        if (!$filing) {
            $stmt = $pdo->prepare("
                SELECT id, company_name, report_date, file_name
                FROM ten_k_filings 
                WHERE company_name LIKE ? OR file_name LIKE ?
                ORDER BY report_date DESC 
                LIMIT 1
            ");
            $stmt->execute(["%$ticker%", "%$ticker%"]);
            $filing = $stmt->fetch(PDO::FETCH_ASSOC);

            error_log("部分匹配查詢 $ticker: " . ($filing ? "找到" : "未找到"));
        }

        if (!$filing) {
            error_log("找不到 $ticker 的 10-K 檔案");
            return null;
        }

        // 獲取摘要資料
        $stmt = $pdo->prepare("
            SELECT * FROM ten_k_filings_summary 
            WHERE original_filing_id = ? 
            AND processing_status = 'completed'
            ORDER BY summary_completed_at DESC 
            LIMIT 1
        ");
        $stmt->execute([$filing['id']]);
        $summary = $stmt->fetch(PDO::FETCH_ASSOC);

        if (!$summary) {
            error_log("找不到 $ticker 的 10-K 摘要資料");
            return null;
        }

        return [
            'company_name' => $filing['company_name'],  // 現在這裡會是股票代號
            'report_date' => $filing['report_date'],
            'file_name' => $filing['file_name'],
            'summary' => $summary
        ];
    } catch (Exception $e) {
        error_log("獲取 10-K 摘要資料錯誤: " . $e->getMessage());
        return null;
    }
}

/**
 * 生成GPT答案
 */
function generateGPTAnswer($question, $summaryData, $ticker)
{
    // 從環境變量或配置中獲取 OpenAI API 金鑰
    $openaiApiKey = defined('OPENAI_API_KEY') ? OPENAI_API_KEY : (getenv('OPENAI_API_KEY') ?: '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');

    try {
        // 構建所有可用的摘要內容 - 現在提供完整的10-K摘要給GPT
        $allSummaries = [];
        $summary = $summaryData['summary'];

        // 包含所有有內容的Item摘要
        $itemMappings = [
            'item_1_summary' => '業務概況 (Item 1)',
            'item_1a_summary' => '風險因素 (Item 1A)',
            'item_1b_summary' => '未解決的員工評論 (Item 1B)',
            'item_2_summary' => '物業 (Item 2)',
            'item_3_summary' => '法律程序 (Item 3)',
            'item_4_summary' => '礦業安全披露 (Item 4)',
            'item_5_summary' => '市場資訊 (Item 5)',
            'item_6_summary' => '選定財務數據 (Item 6)',
            'item_7_summary' => '管理層討論與分析 (Item 7)',
            'item_7a_summary' => '量化和定性市場風險披露 (Item 7A)',
            'item_8_summary' => '財務報表和補充數據 (Item 8)',
            'item_9_summary' => '與會計師的分歧和會計披露 (Item 9)',
            'item_9a_summary' => '披露控制和程序 (Item 9A)',
            'item_9b_summary' => '其他資訊 (Item 9B)',
            'item_10_summary' => '董事、高管和公司治理 (Item 10)',
            'item_11_summary' => '高管薪酬 (Item 11)',
            'item_12_summary' => '證券擁有權和相關股東事項 (Item 12)',
            'item_13_summary' => '某些關係和關聯交易 (Item 13)',
            'item_14_summary' => '主要會計費用和服務 (Item 14)',
            'item_15_summary' => '展示和財務報表時間表 (Item 15)',
            'item_16_summary' => 'Form 10-K摘要 (Item 16)'
        ];

        foreach ($itemMappings as $field => $title) {
            if (!empty($summary[$field])) {
                $allSummaries[$title] = $summary[$field];
            }
        }

        if (empty($allSummaries)) {
            return "抱歉，目前沒有找到 $ticker 的 10-K 報告摘要資料。";
        }

        // 構建完整的摘要文本
        $summaryText = "";
        foreach ($allSummaries as $section => $content) {
            $summaryText .= "\n\n=== $section ===\n$content";
        }

        $prompt = "
基於以下 {$summaryData['company_name']} ({$ticker}) 的完整 10-K 報告摘要資料，請回答用戶的問題。

**重要回答準則（必須嚴格遵守）：**

1. **沒有自信的不要回答** - 如果提供的摘要資料中沒有明確、具體的數據支持你的回答，請明確說明「摘要資料中沒有足夠的具體資訊回答此問題」
2. **沒有數據的不要回答** - 只能基於摘要中的實際數據、比率、百分比、金額等量化資訊回答，不能進行推測或添加摘要中沒有的資訊
3. **回答了要說明理由** - 每個論點都必須明確引用來自哪個章節(Item)的具體數據作為依據
4. **保留並呈現支持論點的數據** - 必須完整呈現所有相關的數字、比率、金額、百分比等量化資訊，不能省略或簡化

**回答格式要求：**
- 使用繁體中文回答，支援Markdown格式
- 使用適當的標題(##、###)、粗體(**text**)、項目列表等Markdown語法
- 對於每個論點，明確標註數據來源：「根據[章節名稱]，[具體數據]...」
- 如果某個問題涉及多個層面但只有部分有數據支持，請分別說明哪些有數據支持、哪些沒有
- 如果完全沒有相關數據，直接說明「10-K摘要資料中沒有提供此問題相關的具體數據」

**圖表回應格式：**
如果問題適合用圖表呈現（如趨勢、比較、佔比等），請在回答末尾加上圖表數據，格式如下：

```chart
{
  \"type\": \"line|bar|pie|area\",
  \"title\": \"圖表標題\",
  \"data\": {
    \"labels\": [\"2021\", \"2022\", \"2023\"],
    \"datasets\": [{
      \"label\": \"營收（百萬美元）\",
      \"data\": [1000, 1200, 1300],
      \"backgroundColor\": \"rgba(54, 162, 235, 0.2)\",
      \"borderColor\": \"rgba(54, 162, 235, 1)\"
    }]
  },
  \"options\": {
    \"responsive\": true,
    \"scales\": {
      \"y\": {
        \"beginAtZero\": true
      }
    }
  }
}
```

10-K 報告完整摘要資料（報告日期：{$summaryData['report_date']}）：
$summaryText

用戶問題：$question

請嚴格按照上述準則提供專業的回答：
";

        // 調用 OpenAI API
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, 'https://api.openai.com/v1/chat/completions');
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_HTTPHEADER, [
            'Content-Type: application/json',
            'Authorization: Bearer ' . $openaiApiKey
        ]);

        $data = [
            'model' => 'gpt-4-turbo',
            'messages' => [
                [
                    'role' => 'system',
                    'content' => '你是一個嚴謹的財務分析師，專門分析 SEC 10-K 檔案。你必須嚴格遵守「只基於具體數據回答、沒有數據不回答、回答必須說明數據來源」的原則。你絕不進行推測、猜測或添加檔案中沒有的資訊。每個回答都必須有明確的數據支撐和章節來源引用。'
                ],
                [
                    'role' => 'user',
                    'content' => $prompt
                ]
            ],
            'max_tokens' => 2000,
            'temperature' => 0.1
        ];

        curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));

        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        if ($httpCode !== 200) {
            error_log("OpenAI API 錯誤: HTTP $httpCode - $response");
            return null;
        }

        $result = json_decode($response, true);

        if (!$result || !isset($result['choices'][0]['message']['content'])) {
            error_log("OpenAI API 回應格式錯誤: " . $response);
            return null;
        }

        return trim($result['choices'][0]['message']['content']);
    } catch (Exception $e) {
        error_log("GPT 答案生成錯誤: " . $e->getMessage());
        return null;
    }
}

/**
 * 獲取或創建對話
 */
function getOrCreateConversation($pdo, $userId, $ticker)
{
    // 查找現有對話
    $stmt = $pdo->prepare("
        SELECT id FROM conversations 
        WHERE user_id = ? AND title = ?
        ORDER BY updated_at DESC 
        LIMIT 1
    ");
    $stmt->execute([$userId, $ticker]);
    $existing = $stmt->fetch(PDO::FETCH_ASSOC);

    if ($existing) {
        // 更新最後活動時間
        $stmt = $pdo->prepare("UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?");
        $stmt->execute([$existing['id']]);
        return $existing['id'];
    }

    // 創建新對話
    $stmt = $pdo->prepare("
        INSERT INTO conversations (user_id, title, created_at, updated_at) 
        VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    ");
    $stmt->execute([$userId, $ticker]);
    return $pdo->lastInsertId();
}

/**
 * 儲存問答記錄
 */
function saveQuestionAnswer($pdo, $conversationId, $question, $answer, $userId)
{
    $stmt = $pdo->prepare("
        INSERT INTO questions (conversation_id, question, answer, created_by, created_at) 
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    ");
    $stmt->execute([$conversationId, $question, $answer, $userId]);
    return $pdo->lastInsertId();
}

/**
 * 儲存用戶問題歷史
 */
function saveUserQuestionHistory($pdo, $userId, $questionId, $conversationId)
{
    $stmt = $pdo->prepare("
        INSERT INTO user_questions (user_id, question_id, conversation_id, asked_at) 
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    ");
    $stmt->execute([$userId, $questionId, $conversationId]);
}

/**
 * 處理10-K檔案問題
 */
function ask10KQuestion($pdo, $ticker)
{
    $question = trim($_POST['question'] ?? '');
    $filename = trim($_POST['filename'] ?? '');

    if (empty($question)) {
        echo json_encode(['success' => false, 'error' => '問題不能為空']);
        return;
    }

    if (empty($filename)) {
        echo json_encode(['success' => false, 'error' => '檔案名稱不能為空']);
        return;
    }

    // 處理從對話歷史點擊進入的情況，將中文檔案名轉換為系統識別的格式
    if ($filename === '所有10K檔案') {
        $filename = 'ALL';
    }

    try {
        // 1. 檢查是否有相同問題的快取答案
        $cacheKey = $ticker . '_' . $filename . '_' . md5($question);
        $cachedAnswer = get10KCachedAnswer($pdo, $cacheKey);
        $isCached = false;

        if ($cachedAnswer) {
            $answer = $cachedAnswer;
            $isCached = true;
            error_log("使用10-K快取答案: " . substr($question, 0, 50) . "...");
        } else {
            // 2. 獲取10-K摘要內容
            global $pdo;
            $pdo = $pdo; // 確保全域變數可用
            $tenKContent = get10KFileContent($ticker, $filename);

            if (!$tenKContent) {
                echo json_encode([
                    'success' => false,
                    'error' => "無法讀取 $ticker 的 10-K 摘要資料：$filename"
                ]);
                return;
            }

            // 3. 調用GPT生成答案
            $answer = generate10KGPTAnswer($question, $tenKContent, $ticker, $filename);

            if (!$answer) {
                echo json_encode(['success' => false, 'error' => 'GPT 回答生成失敗，請稍後再試']);
                return;
            }

            // 4. 快取答案
            cache10KAnswer($pdo, $cacheKey, $answer);
        }

        // 5. 獲取或創建10-K對話
        $conversationTitle = $filename === 'ALL' ?
            "{$ticker}_所有10K檔案" :
            "{$ticker}_{$filename}";
        $conversationId = getOrCreate10KConversation($pdo, $_SESSION['user_id'], $conversationTitle);

        // 6. 儲存問答記錄
        $questionId = saveQuestionAnswer($pdo, $conversationId, $question, $answer, $_SESSION['user_id']);

        // 7. 儲存用戶問題歷史記錄
        saveUserQuestionHistory($pdo, $_SESSION['user_id'], $questionId, $conversationId);

        echo json_encode([
            'success' => true,
            'answer' => $answer,
            'is_cached' => $isCached,
            'question_id' => $questionId,
            'conversation_id' => $conversationId
        ]);
    } catch (Exception $e) {
        error_log("處理10-K問題錯誤: " . $e->getMessage());
        echo json_encode(['success' => false, 'error' => '處理問題時發生錯誤']);
    }
}

/**
 * 獲取10-K快取答案
 */
function get10KCachedAnswer($pdo, $cacheKey)
{
    try {
        $stmt = $pdo->prepare("
            SELECT answer 
            FROM tenk_qa_cache 
            WHERE cache_key = ? 
            AND created_at > DATE_SUB(NOW(), INTERVAL 7 DAY)
            ORDER BY created_at DESC 
            LIMIT 1
        ");
        $stmt->execute([$cacheKey]);
        $result = $stmt->fetch(PDO::FETCH_ASSOC);

        return $result ? $result['answer'] : null;
    } catch (Exception $e) {
        error_log("獲取10-K快取答案錯誤: " . $e->getMessage());
        return null;
    }
}

/**
 * 快取10-K答案
 */
function cache10KAnswer($pdo, $cacheKey, $answer)
{
    try {
        $stmt = $pdo->prepare("
            INSERT INTO tenk_qa_cache (cache_key, answer, created_at) 
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON DUPLICATE KEY UPDATE 
            answer = VALUES(answer), 
            created_at = VALUES(created_at)
        ");
        $stmt->execute([$cacheKey, $answer]);
    } catch (Exception $e) {
        error_log("快取10-K答案錯誤: " . $e->getMessage());
    }
}

/**
 * 獲取10-K檔案摘要內容
 */
function get10KFileContent($ticker, $filename)
{
    try {
        global $pdo;
        if (!$pdo) {
            $db = new Database();
            $pdo = $db->getConnection();
        }

        if ($filename === 'ALL') {
            // 獲取該股票所有10-K檔案的摘要內容
            $stmt = $pdo->prepare("
                SELECT 
                    s.*,
                    f.file_name as original_file_name,
                    f.company_name,
                    f.report_date
                FROM ten_k_filings_summary s
                INNER JOIN ten_k_filings f ON s.original_filing_id = f.id
                WHERE f.company_name LIKE ? OR f.company_name = ?
                ORDER BY f.report_date DESC
            ");
            $stmt->execute(["%$ticker%", $ticker]);
            $summaries = $stmt->fetchAll(PDO::FETCH_ASSOC);

            if (empty($summaries)) {
                error_log("找不到 $ticker 的10-K摘要資料");
                return null;
            }

            // 生成基本資訊摘要
            $basicInfo = "## 公司10-K檔案基本資訊\n\n";
            $basicInfo .= "**公司代號**: $ticker\n";
            $basicInfo .= "**公司名稱**: {$summaries[0]['company_name']}\n";
            $basicInfo .= "**可用檔案數量**: " . count($summaries) . " 份\n\n";

            $basicInfo .= "### 檔案列表\n";
            foreach ($summaries as $summary) {
                $basicInfo .= "- **{$summary['original_file_name']}** (報告期間: {$summary['report_date']})\n";
            }
            $basicInfo .= "\n---\n\n";

            $allContent = $basicInfo;
            foreach ($summaries as $summary) {
                $allContent .= "\n\n=== 檔案：{$summary['original_file_name']} (報告日期：{$summary['report_date']}) ===\n\n";

                // 組合所有摘要內容
                $itemSummaries = [
                    'Item 1 - Business' => $summary['item_1_summary'],
                    'Item 1A - Risk Factors' => $summary['item_1a_summary'],
                    'Item 1B - Unresolved Staff Comments' => $summary['item_1b_summary'],
                    'Item 2 - Properties' => $summary['item_2_summary'],
                    'Item 3 - Legal Proceedings' => $summary['item_3_summary'],
                    'Item 4 - Mine Safety' => $summary['item_4_summary'],
                    'Item 5 - Market for Common Equity' => $summary['item_5_summary'],
                    'Item 6 - Selected Financial Data' => $summary['item_6_summary'],
                    'Item 7 - MD&A' => $summary['item_7_summary'],
                    'Item 7A - Market Risk' => $summary['item_7a_summary'],
                    'Item 8 - Financial Statements' => $summary['item_8_summary'],
                    'Item 9 - Accountant Changes' => $summary['item_9_summary'],
                    'Item 9A - Controls and Procedures' => $summary['item_9a_summary'],
                    'Item 9B - Other Information' => $summary['item_9b_summary'],
                    'Item 10 - Directors and Governance' => $summary['item_10_summary'],
                    'Item 11 - Executive Compensation' => $summary['item_11_summary'],
                    'Item 12 - Security Ownership' => $summary['item_12_summary'],
                    'Item 13 - Related Transactions' => $summary['item_13_summary'],
                    'Item 14 - Accountant Fees' => $summary['item_14_summary'],
                    'Item 15 - Exhibits' => $summary['item_15_summary'],
                    'Item 16 - Form 10-K Summary' => $summary['item_16_summary']
                ];

                foreach ($itemSummaries as $itemName => $itemContent) {
                    if (!empty($itemContent)) {
                        $allContent .= "\n## $itemName\n\n$itemContent\n\n";
                    }
                }
            }

            return $allContent ?: null;
        } else {
            // 獲取特定檔案的摘要內容 - 改善查詢邏輯
            $stmt = $pdo->prepare("
                SELECT 
                    s.*,
                    f.file_name as original_file_name,
                    f.company_name,
                    f.report_date
                FROM ten_k_filings_summary s
                INNER JOIN ten_k_filings f ON s.original_filing_id = f.id
                WHERE f.file_name = ? 
                LIMIT 1
            ");
            $stmt->execute([$filename]);
            $summary = $stmt->fetch(PDO::FETCH_ASSOC);

            // 如果沒找到，嘗試模糊匹配
            if (!$summary) {
                $stmt = $pdo->prepare("
                    SELECT 
                        s.*,
                        f.file_name as original_file_name,
                        f.company_name,
                        f.report_date
                    FROM ten_k_filings_summary s
                    INNER JOIN ten_k_filings f ON s.original_filing_id = f.id
                    WHERE f.file_name LIKE ? AND (f.company_name LIKE ? OR f.company_name = ?)
                    LIMIT 1
                ");
                $stmt->execute(["%$filename%", "%$ticker%", $ticker]);
                $summary = $stmt->fetch(PDO::FETCH_ASSOC);
            }

            if (!$summary) {
                error_log("找不到檔案 $filename 的摘要資料，ticker: $ticker");
                return null;
            }

            // 生成基本資訊
            $basicInfo = "## 10-K檔案基本資訊\n\n";
            $basicInfo .= "**檔案名稱**: {$summary['original_file_name']}\n";
            $basicInfo .= "**公司名稱**: {$summary['company_name']}\n";
            $basicInfo .= "**公司代號**: $ticker\n";
            $basicInfo .= "**報告期間結束日期**: {$summary['report_date']}\n";
            $basicInfo .= "**摘要處理狀態**: {$summary['processing_status']}\n";
            $basicInfo .= "**已處理項目**: {$summary['items_processed_count']}/{$summary['total_items_count']}\n\n";
            $basicInfo .= "---\n\n";

            $content = $basicInfo;
            $content .= "=== 檔案內容摘要：{$summary['original_file_name']} ===\n\n";

            // 組合所有摘要內容
            $itemSummaries = [
                'Item 1 - Business' => $summary['item_1_summary'],
                'Item 1A - Risk Factors' => $summary['item_1a_summary'],
                'Item 1B - Unresolved Staff Comments' => $summary['item_1b_summary'],
                'Item 2 - Properties' => $summary['item_2_summary'],
                'Item 3 - Legal Proceedings' => $summary['item_3_summary'],
                'Item 4 - Mine Safety' => $summary['item_4_summary'],
                'Item 5 - Market for Common Equity' => $summary['item_5_summary'],
                'Item 6 - Selected Financial Data' => $summary['item_6_summary'],
                'Item 7 - MD&A' => $summary['item_7_summary'],
                'Item 7A - Market Risk' => $summary['item_7a_summary'],
                'Item 8 - Financial Statements' => $summary['item_8_summary'],
                'Item 9 - Accountant Changes' => $summary['item_9_summary'],
                'Item 9A - Controls and Procedures' => $summary['item_9a_summary'],
                'Item 9B - Other Information' => $summary['item_9b_summary'],
                'Item 10 - Directors and Governance' => $summary['item_10_summary'],
                'Item 11 - Executive Compensation' => $summary['item_11_summary'],
                'Item 12 - Security Ownership' => $summary['item_12_summary'],
                'Item 13 - Related Transactions' => $summary['item_13_summary'],
                'Item 14 - Accountant Fees' => $summary['item_14_summary'],
                'Item 15 - Exhibits' => $summary['item_15_summary'],
                'Item 16 - Form 10-K Summary' => $summary['item_16_summary']
            ];

            foreach ($itemSummaries as $itemName => $itemContent) {
                if (!empty($itemContent)) {
                    $content .= "\n## $itemName\n\n$itemContent\n\n";
                }
            }

            return $content ?: null;
        }
    } catch (Exception $e) {
        error_log("讀取10-K摘要資料錯誤: " . $e->getMessage());
        return null;
    }
}

/**
 * 生成10-K的GPT回答
 */
function generate10KGPTAnswer($question, $tenKContent, $ticker, $filename)
{
    try {
        $openaiApiKey = defined('OPENAI_API_KEY') ? OPENAI_API_KEY : null;

        if (empty($openaiApiKey)) {
            error_log("OpenAI API key 未設定");
            return null;
        }

        // 清理和限制內容長度
        $tenKContent = trim($tenKContent);
        $question = trim($question);

        // 確保UTF-8編碼正確
        $tenKContent = mb_convert_encoding($tenKContent, 'UTF-8', 'UTF-8');
        $question = mb_convert_encoding($question, 'UTF-8', 'UTF-8');

        // 移除可能導致JSON問題的特殊字符
        $tenKContent = preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/u', '', $tenKContent);
        $question = preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/u', '', $question);

        // 限制內容長度以避免超過API限制
        $contentLimit = 12000; // 減少到12k字符以確保安全
        if (mb_strlen($tenKContent, 'UTF-8') > $contentLimit) {
            $tenKContent = mb_substr($tenKContent, 0, $contentLimit, 'UTF-8') . "\n\n[內容因長度限制而截斷]";
        }

        $fileDescription = $filename === 'ALL' ? "所有10-K檔案的GPT摘要" : "10-K檔案的GPT摘要：$filename";

        $systemPrompt = "你是一個專業的財務分析師，專門分析SEC 10-K檔案摘要。你必須嚴格基於提供的摘要內容回答問題，並明確引用相關的Item章節。";

        $userPrompt = "請分析以下 {$ticker} 公司的 {$fileDescription}，並回答問題：\n\n{$question}\n\n摘要內容：\n\n{$tenKContent}";


        // 調用 OpenAI API
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, 'https://api.openai.com/v1/chat/completions');
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_HTTPHEADER, [
            'Content-Type: application/json',
            'Authorization: Bearer ' . $openaiApiKey
        ]);

        $data = [
            'model' => 'gpt-4-turbo',
            'messages' => [
                [
                    'role' => 'system',
                    'content' => $systemPrompt
                ],
                [
                    'role' => 'user',
                    'content' => $userPrompt
                ]
            ],
            'max_tokens' => 2000,
            'temperature' => 0.1
        ];

        // 確保JSON編碼正確
        $jsonData = json_encode($data, JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_IGNORE);
        if ($jsonData === false) {
            error_log("JSON編碼失敗: " . json_last_error_msg());
            curl_close($ch);
            return null;
        }

        curl_setopt($ch, CURLOPT_POSTFIELDS, $jsonData);

        $response = curl_exec($ch);
        if ($response === false) {
            error_log("CURL錯誤: " . curl_error($ch));
            curl_close($ch);
            return null;
        }

        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        if ($httpCode !== 200) {
            error_log("OpenAI API 錯誤: HTTP $httpCode - $response");
            return null;
        }

        $result = json_decode($response, true);
        if (json_last_error() !== JSON_ERROR_NONE) {
            error_log("JSON解碼失敗: " . json_last_error_msg());
            return null;
        }

        if (!$result || !isset($result['choices'][0]['message']['content'])) {
            error_log("OpenAI API 回應格式錯誤: " . $response);
            return null;
        }

        $answer = trim($result['choices'][0]['message']['content']);
        // 再次確保回答的UTF-8編碼正確
        return mb_convert_encoding($answer, 'UTF-8', 'UTF-8');
    } catch (Exception $e) {
        error_log("生成10-K GPT答案錯誤: " . $e->getMessage());
        return null;
    }
}

/**
 * 獲取或創建10-K對話
 */
function getOrCreate10KConversation($pdo, $userId, $title)
{
    // 查找現有對話
    $stmt = $pdo->prepare("
        SELECT id FROM conversations 
        WHERE user_id = ? AND title = ?
        ORDER BY updated_at DESC 
        LIMIT 1
    ");
    $stmt->execute([$userId, $title]);
    $existing = $stmt->fetch(PDO::FETCH_ASSOC);

    if ($existing) {
        // 更新最後活動時間
        $stmt = $pdo->prepare("UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?");
        $stmt->execute([$existing['id']]);
        return $existing['id'];
    }

    // 創建新對話
    $stmt = $pdo->prepare("
        INSERT INTO conversations (user_id, title, created_at, updated_at) 
        VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    ");
    $stmt->execute([$userId, $title]);
    return $pdo->lastInsertId();
}

/**
 * 獲取對話歷史
 */
function getConversationHistory($pdo)
{
    try {
        $stmt = $pdo->prepare("
            SELECT 
                c.id as conversation_id,
                c.title,
                c.created_at,
                c.updated_at,
                COUNT(q.id) as question_count,
                MAX(q.created_at) as last_question_time
            FROM conversations c 
            LEFT JOIN questions q ON c.id = q.conversation_id
            WHERE c.user_id = ?
            GROUP BY c.id, c.title, c.created_at, c.updated_at
            ORDER BY c.updated_at DESC
            LIMIT 20
        ");
        $stmt->execute([$_SESSION['user_id']]);
        $conversations = $stmt->fetchAll(PDO::FETCH_ASSOC);

        echo json_encode([
            'success' => true,
            'conversations' => $conversations
        ]);
    } catch (Exception $e) {
        error_log("獲取對話歷史錯誤: " . $e->getMessage());
        echo json_encode(['success' => false, 'error' => '獲取對話歷史失敗']);
    }
}

/**
 * 獲取對話訊息
 */
function getConversationMessages($pdo)
{
    $conversationId = trim($_POST['conversation_id'] ?? '');

    if (empty($conversationId)) {
        echo json_encode(['success' => false, 'error' => '對話ID不能為空']);
        return;
    }

    try {
        // 驗證對話是否屬於當前用戶
        $stmt = $pdo->prepare("
            SELECT id FROM conversations 
            WHERE id = ? AND user_id = ?
        ");
        $stmt->execute([$conversationId, $_SESSION['user_id']]);

        if (!$stmt->fetch()) {
            echo json_encode(['success' => false, 'error' => '對話不存在或無權限訪問']);
            return;
        }

        // 獲取對話中的所有問答記錄
        $stmt = $pdo->prepare("
            SELECT 
                question,
                answer,
                created_at
            FROM questions 
            WHERE conversation_id = ?
            ORDER BY created_at ASC
        ");
        $stmt->execute([$conversationId]);
        $messages = $stmt->fetchAll(PDO::FETCH_ASSOC);

        echo json_encode([
            'success' => true,
            'messages' => $messages
        ]);
    } catch (Exception $e) {
        error_log("獲取對話訊息錯誤: " . $e->getMessage());
        echo json_encode(['success' => false, 'error' => '獲取對話訊息失敗']);
    }
}

/**
 * 更新對話標題
 */
function updateConversationTitle($pdo, $conversationId, $newTitle, $userId)
{
    try {
        // 驗證對話是否屬於該用戶
        $stmt = $pdo->prepare("SELECT id FROM conversations WHERE id = ? AND user_id = ?");
        $stmt->execute([$conversationId, $userId]);

        if (!$stmt->fetch()) {
            return ['success' => false, 'error' => '無權限修改此對話'];
        }

        // 更新標題
        $stmt = $pdo->prepare("UPDATE conversations SET title = ?, updated_at = NOW() WHERE id = ? AND user_id = ?");
        $stmt->execute([$newTitle, $conversationId, $userId]);

        return ['success' => true, 'message' => '對話標題已更新'];
    } catch (Exception $e) {
        error_log("更新對話標題錯誤: " . $e->getMessage());
        return ['success' => false, 'error' => '更新失敗'];
    }
}
