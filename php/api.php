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

        case 'ask':
            $question = sanitize_input($_POST['question'] ?? '');
            $conversation_id = intval($_POST['conversation_id'] ?? 0);

            if (empty($question)) {
                json_response(['success' => false, 'error' => '問題不能為空']);
            }

            // 驗證問題格式和內容
            $validation = validateQuestion($question);
            if (!$validation['valid']) {
                json_response(['success' => false, 'error' => $validation['error']]);
            }

            // 如果沒有指定對話室，創建新的
            if ($conversation_id === 0) {
                $conversation_id = createNewConversation($user_id, $pdo);
            }

            $result = processQuestion($question, $user_id, $conversation_id, $pdo);
            json_response(['success' => true, 'answer' => $result['answer'], 'conversation_id' => $conversation_id]);
            break;

        case 'get_conversations':
            // 獲取用戶的對話室列表
            $stmt = $pdo->prepare("
                SELECT c.id, c.title, c.created_at, c.updated_at,
                       (SELECT q.question FROM questions q WHERE q.conversation_id = c.id ORDER BY q.created_at DESC LIMIT 1) as last_question
                FROM conversations c 
                WHERE c.user_id = ?
                ORDER BY c.updated_at DESC 
                LIMIT 20
            ");
            $stmt->execute([$user_id]);
            $conversations = $stmt->fetchAll();

            json_response(['success' => true, 'conversations' => $conversations]);
            break;

        case 'get_conversation':
            $conversation_id = intval($_GET['id'] ?? 0);

            // 驗證對話室屬於當前用戶
            $stmt = $pdo->prepare("SELECT id FROM conversations WHERE id = ? AND user_id = ?");
            $stmt->execute([$conversation_id, $user_id]);
            if (!$stmt->fetch()) {
                json_response(['success' => false, 'error' => '對話不存在']);
            }

            // 獲取對話內容
            $stmt = $pdo->prepare("
                SELECT q.question, q.answer, q.created_at
                FROM questions q
                WHERE q.conversation_id = ?
                ORDER BY q.created_at ASC
            ");
            $stmt->execute([$conversation_id]);
            $messages = $stmt->fetchAll();

            json_response([
                'success' => true,
                'messages' => $messages,
                'conversation_id' => $conversation_id
            ]);
            break;

        case 'new_conversation':
            // 創建新對話室
            $title = sanitize_input($_POST['title'] ?? '新對話');
            $conversation_id = createNewConversation($user_id, $pdo, $title);

            json_response(['success' => true, 'conversation_id' => $conversation_id]);
            break;

        case 'rename_conversation':
            // 重命名對話室
            $conversation_id = intval($_POST['conversation_id'] ?? 0);
            $title = sanitize_input($_POST['title'] ?? '');

            if (empty($title)) {
                json_response(['success' => false, 'error' => '標題不能為空']);
            }

            $stmt = $pdo->prepare("UPDATE conversations SET title = ? WHERE id = ? AND user_id = ?");
            $result = $stmt->execute([$title, $conversation_id, $user_id]);

            json_response(['success' => $result]);
            break;

        default:
            json_response(['success' => false, 'error' => '無效的操作'], 400);
    }
} catch (Exception $e) {
    error_log("API Error: " . $e->getMessage());
    json_response(['success' => false, 'error' => '系統錯誤，請稍後再試'], 500);
}

function validateQuestion($question)
{
    // 1. 檢查是否包含股票代碼格式 [TICKER]
    if (!preg_match('/\[([A-Z]{1,5})\]/', $question, $matches)) {
        return [
            'valid' => false,
            'error' => '請使用正確格式：[股票代碼] 您的問題，例如：[AAPL] 2023年營收表現如何？'
        ];
    }

    $ticker = $matches[1];

    // 2. 驗證股票代碼（基本驗證）
    if (strlen($ticker) < 1 || strlen($ticker) > 5) {
        return [
            'valid' => false,
            'error' => '股票代碼格式錯誤，請使用1-5個英文字母，例如：[AAPL]'
        ];
    }

    return ['valid' => true];
}

function createNewConversation($user_id, $pdo, $title = '新對話')
{
    $stmt = $pdo->prepare("INSERT INTO conversations (user_id, title) VALUES (?, ?)");
    $stmt->execute([$user_id, $title]);
    return $pdo->lastInsertId();
}

function processQuestion($question, $user_id, $conversation_id, $pdo)
{
    // 1. 搜尋現有答案
    $existingAnswer = searchExistingAnswers($question, $pdo);
    if ($existingAnswer) {
        // 將現有答案複製到當前對話室
        $questionId = saveQuestionAnswer($question, $existingAnswer['answer'], [], $user_id, $conversation_id, $pdo);
        recordUserQuestion($user_id, $questionId, $conversation_id, $pdo);
        updateConversationTitle($conversation_id, $question, $pdo);
        return ['answer' => $existingAnswer['answer'], 'question_id' => $questionId];
    }

    // 2. 尋找相關財報資料
    $filingData = findRelevantFilings($question, $pdo);

    if (empty($filingData)) {
        // 3. 如果沒有相關資料，嘗試下載
        $companies = extractCompaniesFromQuestion($question);
        if (!empty($companies)) {
            // 檢查是否已有該公司的任何財報
            $hasAnyFilings = checkCompanyFilings($companies, $pdo);

            if (!$hasAnyFilings) {
                // 開始下載並提供即時回饋
                $downloadResult = downloadFilingsForCompanies($companies);
                if (!$downloadResult) {
                    $questionId = saveQuestionAnswer(
                        $question,
                        "抱歉，系統中沒有找到 " . implode(', ', $companies) . " 的財報資料，且自動下載失敗。請稍後再試或聯繫管理員。",
                        [],
                        $user_id,
                        $conversation_id,
                        $pdo
                    );
                    recordUserQuestion($user_id, $questionId, $conversation_id, $pdo);
                    updateConversationTitle($conversation_id, $question, $pdo);
                    return ['answer' => "抱歉，系統中沒有找到 " . implode(', ', $companies) . " 的財報資料，且自動下載失敗。請稍後再試或聯繫管理員。", 'question_id' => $questionId];
                }
            }

            // 重新搜尋
            $filingData = findRelevantFilings($question, $pdo);
        } else {
            // 無法識別公司
            $questionId = saveQuestionAnswer(
                $question,
                "抱歉，我無法識別您想詢問的公司。請使用格式 [股票代碼] 您的問題，例如：[AAPL] 2023年營收如何？",
                [],
                $user_id,
                $conversation_id,
                $pdo
            );
            recordUserQuestion($user_id, $questionId, $conversation_id, $pdo);
            updateConversationTitle($conversation_id, $question, $pdo);
            return ['answer' => "抱歉，我無法識別您想詢問的公司。請使用格式 [股票代碼] 您的問題，例如：[AAPL] 2023年營收如何？", 'question_id' => $questionId];
        }
    }

    // 4. 使用 GPT 分析
    $answer = analyzeWithGPT($question, $filingData);

    // 5. 保存問題和答案
    $questionId = saveQuestionAnswer($question, $answer, $filingData, $user_id, $conversation_id, $pdo);
    recordUserQuestion($user_id, $questionId, $conversation_id, $pdo);
    updateConversationTitle($conversation_id, $question, $pdo);

    return ['answer' => $answer, 'question_id' => $questionId];
}

function updateConversationTitle($conversation_id, $question, $pdo)
{
    // 如果對話室標題是默認的，使用問題的前30個字符作為標題
    $stmt = $pdo->prepare("SELECT title FROM conversations WHERE id = ?");
    $stmt->execute([$conversation_id]);
    $conversation = $stmt->fetch();

    if ($conversation && ($conversation['title'] === '新對話' || $conversation['title'] === '預設對話')) {
        $newTitle = mb_substr($question, 0, 30) . (mb_strlen($question) > 30 ? '...' : '');
        $stmt = $pdo->prepare("UPDATE conversations SET title = ? WHERE id = ?");
        $stmt->execute([$newTitle, $conversation_id]);
    }
}

function searchExistingAnswers($question, $pdo)
{
    // 首先進行精確匹配
    $stmt = $pdo->prepare("
        SELECT id, question, answer
        FROM questions 
        WHERE question = ?
        LIMIT 1
    ");
    $stmt->execute([$question]);
    $result = $stmt->fetch();

    if ($result) {
        return ['question_id' => $result['id'], 'answer' => $result['answer']];
    }

    // 如果沒有找到完全相同的問題，進行相似性搜尋（備用）
    $stmt = $pdo->prepare("
        SELECT id, question, answer, 
               MATCH(question) AGAINST(? IN NATURAL LANGUAGE MODE) as relevance
        FROM questions 
        WHERE MATCH(question) AGAINST(? IN NATURAL LANGUAGE MODE)
        HAVING relevance > 0.8
        ORDER BY relevance DESC 
        LIMIT 1
    ");
    $stmt->execute([$question, $question]);
    $result = $stmt->fetch();

    if ($result) {
        return ['question_id' => $result['id'], 'answer' => $result['answer']];
    }

    return null;
}

function findRelevantFilings($question, $pdo)
{
    // 從問題中提取公司關鍵字
    $companies = extractCompaniesFromQuestion($question);
    $filings = [];

    // 股票代碼到公司名稱的映射
    $tickerToCompanyMap = [
        'AAPL' => 'Apple',
        'MSFT' => 'Microsoft',
        'GOOGL' => 'Alphabet',
        'GOOG' => 'Alphabet',
        'AMZN' => 'Amazon',
        'TSLA' => 'Tesla',
        'META' => 'Meta',
        'NVDA' => 'NVIDIA',
        'JPM' => 'JPMorgan',
        'V' => 'Visa',
        'MA' => 'Mastercard',
        'BRK.B' => 'Berkshire',
        'UNH' => 'UnitedHealth',
    ];

    foreach ($companies as $company) {
        // 如果是股票代碼，轉換為公司名稱
        $searchTerms = [$company];
        if (isset($tickerToCompanyMap[$company])) {
            $searchTerms[] = $tickerToCompanyMap[$company];
        }

        $conditions = [];
        $params = [];

        foreach ($searchTerms as $term) {
            $conditions[] = "f.company_name LIKE ?";
            $conditions[] = "f.cik LIKE ?";
            $params[] = "%{$term}%";
            $params[] = "%{$term}%";
        }

        $whereClause = "(" . implode(" OR ", $conditions) . ")";

        $stmt = $pdo->prepare("
            SELECT f.*, 
                   COALESCE(f.item_7_content, '') as item_7,
                   COALESCE(f.item_8_content, '') as item_8
            FROM filings f 
            WHERE {$whereClause}
            AND (f.item_7_content IS NOT NULL OR f.item_8_content IS NOT NULL)
            ORDER BY f.report_date DESC 
            LIMIT 3
        ");

        $stmt->execute($params);

        while ($filing = $stmt->fetch()) {
            $filings[] = $filing;
        }
    }

    return $filings;
}

function extractCompaniesFromQuestion($question)
{
    $foundCompanies = [];

    // 優先檢查新格式：[股票代碼]
    if (preg_match_all('/\[([A-Z]{1,5})\]/', $question, $matches)) {
        $foundCompanies = array_merge($foundCompanies, $matches[1]);
    }

    // 如果沒有使用新格式，回退到舊方式
    if (empty($foundCompanies)) {
        // 常見公司名稱和股票代碼對應表
        $companyMap = [
            'AAPL' => ['Apple', 'Apple Inc', '蘋果'],
            'MSFT' => ['Microsoft', 'Microsoft Corp', '微軟'],
            'GOOGL' => ['Google', 'Alphabet', 'Alphabet Inc', '谷歌'],
            'AMZN' => ['Amazon', 'Amazon.com', '亞馬遜'],
            'TSLA' => ['Tesla', 'Tesla Inc', '特斯拉'],
            'META' => ['Meta', 'Facebook', 'Meta Platforms'],
            'NVDA' => ['NVIDIA', 'Nvidia Corp', '輝達'],
            'JPM' => ['JPMorgan', 'JP Morgan', 'JPMorgan Chase'],
            'V' => ['Visa', 'Visa Inc'],
            'MA' => ['Mastercard', 'MasterCard Inc'],
            'BRK.B' => ['Berkshire Hathaway', 'Berkshire'],
            'UNH' => ['UnitedHealth', 'UnitedHealth Group'],
        ];

        $upperQuestion = strtoupper($question);

        foreach ($companyMap as $ticker => $names) {
            // 檢查股票代碼
            if (strpos($upperQuestion, $ticker) !== false) {
                $foundCompanies[] = $ticker;
                continue;
            }

            // 檢查公司名稱
            foreach ($names as $name) {
                if (stripos($question, $name) !== false) {
                    $foundCompanies[] = $ticker;
                    break;
                }
            }
        }
    }

    return array_unique($foundCompanies);
}

function checkCompanyFilings($companies, $pdo)
{
    if (empty($companies)) {
        return false;
    }

    $placeholders = str_repeat('?,', count($companies) - 1) . '?';
    $searchTerms = array_map(function ($company) {
        return "%{$company}%";
    }, $companies);

    $stmt = $pdo->prepare(
        "
        SELECT COUNT(*) as count 
        FROM filings 
        WHERE " . implode(' OR ', array_fill(0, count($companies), 'company_name LIKE ?'))
    );
    $stmt->execute($searchTerms);

    $result = $stmt->fetch();
    return $result['count'] > 0;
}

function downloadFilingsForCompanies($companies)
{
    try {
        // 調用 Python 腳本下載財報
        $companiesStr = implode(',', $companies);
        $cmd = sprintf(
            'cd %s && python filing_processor.py download %s "10-K,10-Q" 2023-01-01 2024-12-31 2>&1',
            escapeshellarg(PYTHON_SCRIPT_PATH),
            escapeshellarg($companiesStr)
        );

        // 非同步執行，避免用戶等待太久
        if (strtoupper(substr(PHP_OS, 0, 3)) === 'WIN') {
            pclose(popen("start /B " . $cmd, "r"));
        } else {
            exec($cmd . " > /dev/null 2>&1 &");
        }

        // 由於是非同步執行，我們假設命令啟動成功
        return true;
    } catch (Exception $e) {
        error_log("下載財報失敗: " . $e->getMessage());
        return false;
    }
}

function analyzeWithGPT($question, $filingData)
{
    $gpt = new GPTClient();

    // 檢查資料品質
    $hasUsefulData = false;
    if (!empty($filingData)) {
        foreach ($filingData as $filing) {
            $item7 = $filing['item_7'] ?? '';
            $item8 = $filing['item_8'] ?? '';

            // 檢查是否包含實際的財務內容（而非只是HTML導航）
            if ((strlen($item7) > 500 && (strpos(strtolower($item7), 'revenue') !== false ||
                    strpos(strtolower($item7), 'income') !== false ||
                    strpos(strtolower($item7), 'cash') !== false)) ||
                (strlen($item8) > 500 && (strpos(strtolower($item8), 'revenue') !== false ||
                    strpos(strtolower($item8), 'income') !== false ||
                    strpos(strtolower($item8), 'cash') !== false))
            ) {
                $hasUsefulData = true;
                break;
            }
        }
    }

    // 根據資料品質調整系統提示
    if ($hasUsefulData) {
        $systemPrompt = "你是一位專業的財務分析師。請基於提供的財報資料回答用戶的問題，提供具體的數據分析和見解。如果資料不足以回答特定問題，請說明並提供你所能分析的部分。";
    } else {
        $systemPrompt = "你是一位專業的商業和財務助手。由於目前沒有可用的詳細財報數據，請基於你的知識庫回答關於該公司的問題。對於具體的財務數字，請說明需要最新的財報資料才能提供準確答案，但可以提供一般性的公司資訊、業務分析或歷史背景。";
    }

    // 構建用戶訊息
    if ($hasUsefulData) {
        $filingContent = "\n【財報資料】:\n";
        foreach ($filingData as $filing) {
            $filingContent .= sprintf(
                "公司: %s (%s)\n財報類型: %s\n報告日期: %s\n\n",
                $filing['company_name'],
                $filing['cik'],
                $filing['filing_type'],
                $filing['report_date']
            );

            // 添加 Item 7 內容（管理層討論與分析）
            if (!empty($filing['item_7'])) {
                $item7 = substr($filing['item_7'], 0, 8000);
                $filingContent .= "管理層討論與分析 (Item 7):\n" . $item7 . "\n\n";
            }

            // 添加 Item 8 內容（財務報表）
            if (!empty($filing['item_8'])) {
                $item8 = substr($filing['item_8'], 0, 5000);
                $filingContent .= "財務報表 (Item 8):\n" . $item8 . "\n\n";
            }
        }
        $userMessage = $filingContent . "\n【用戶問題】:\n" . $question;
    } else {
        $userMessage = "【用戶問題】:\n" . $question . "\n\n注意：目前沒有可用的詳細財報數據，請基於你的知識庫回答。";
    }

    try {
        return $gpt->askQuestion($systemPrompt, $userMessage);
    } catch (Exception $e) {
        error_log("GPT API Error: " . $e->getMessage());
        return "抱歉，AI分析服務暫時無法使用，請稍後再試。";
    }
}

function saveQuestionAnswer($question, $answer, $filingData, $user_id, $conversation_id, $pdo)
{
    $filing_id = !empty($filingData) ? $filingData[0]['id'] : null;

    $stmt = $pdo->prepare("
        INSERT INTO questions (conversation_id, question, answer, filing_id, created_by) 
        VALUES (?, ?, ?, ?, ?)
    ");
    $stmt->execute([$conversation_id, $question, $answer, $filing_id, $user_id]);

    return $pdo->lastInsertId();
}

function recordUserQuestion($user_id, $question_id, $conversation_id, $pdo)
{
    $stmt = $pdo->prepare("
        INSERT INTO user_questions (user_id, question_id, conversation_id) 
        VALUES (?, ?, ?)
    ");
    $stmt->execute([$user_id, $question_id, $conversation_id]);
}
