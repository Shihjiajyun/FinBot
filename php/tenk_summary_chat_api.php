<?php
require_once 'config.php';

header('Content-Type: application/json');

// 檢查登入狀態
if (!isset($_SESSION['user_id'])) {
    echo json_encode(['success' => false, 'error' => '未登入']);
    exit;
}

$action = $_POST['action'] ?? '';

// 根據不同的操作分發請求
switch ($action) {
    case 'ask_summary_question':
        askSummaryQuestion();
        break;
    case 'get_conversation_messages':
        getConversationMessages();
        break;
    case 'get_conversation_history':
        getConversationHistory();
        break;
    default:
        echo json_encode(['success' => false, 'error' => '無效的操作']);
        break;
}

/**
 * 處理基於摘要的智能問答
 */
function askSummaryQuestion()
{
    $ticker = strtoupper(trim($_POST['ticker'] ?? ''));
    $filingIds = json_decode($_POST['filing_ids'] ?? '[]', true);
    $question = trim($_POST['question'] ?? '');

    if (empty($ticker) || empty($filingIds) || empty($question)) {
        echo json_encode(['success' => false, 'error' => '參數不完整']);
        return;
    }

    try {
        $db = new Database();
        $pdo = $db->getConnection();

        // 1. 檢查快取
        $cacheKey = generateCacheKey($ticker, $filingIds, $question);
        $cachedAnswer = getCachedAnswer($pdo, $cacheKey);

        if ($cachedAnswer) {
            echo json_encode([
                'success' => true,
                'answer' => $cachedAnswer,
                'is_cached' => true,
                'conversation_id' => getOrCreateSummaryConversation($pdo, $ticker, $filingIds)
            ]);
            return;
        }

        // 2. 獲取財報摘要數據
        $summaryData = getFilingsSummaryData($pdo, $filingIds);

        if (!$summaryData) {
            echo json_encode([
                'success' => false,
                'error' => '找不到相關的財報摘要數據'
            ]);
            return;
        }

        // 3. 使用GPT-4O生成智能答案
        $answer = generateGPT4OAnswer($question, $summaryData, $ticker);

        if (!$answer) {
            echo json_encode(['success' => false, 'error' => 'AI分析失敗，請稍後再試']);
            return;
        }

        // 4. 快取答案
        cacheAnswer($pdo, $cacheKey, $answer);

        // 5. 獲取或創建對話
        $conversationId = getOrCreateSummaryConversation($pdo, $ticker, $filingIds);

        // 6. 儲存問答記錄
        $questionId = saveQuestionAnswer($pdo, $conversationId, $question, $answer, $_SESSION['user_id']);

        echo json_encode([
            'success' => true,
            'answer' => $answer,
            'is_cached' => false,
            'question_id' => $questionId,
            'conversation_id' => $conversationId
        ]);
    } catch (Exception $e) {
        error_log("摘要問答錯誤: " . $e->getMessage());
        echo json_encode(['success' => false, 'error' => '處理請求時發生錯誤']);
    }
}

/**
 * 生成快取鍵
 */
function generateCacheKey($ticker, $filingIds, $question)
{
    sort($filingIds); // 確保順序一致
    return $ticker . '_' . implode('_', $filingIds) . '_' . md5($question);
}

/**
 * 獲取財報摘要數據
 */
function getFilingsSummaryData($pdo, $filingIds)
{
    if (empty($filingIds)) {
        return null;
    }

    try {
        // 構建 IN 子句
        $placeholders = str_repeat('?,', count($filingIds) - 1) . '?';

        $stmt = $pdo->prepare("
            SELECT 
                tfs.*,
                tf.file_name,
                tf.report_date,
                tf.company_name
            FROM ten_k_filings_summary tfs
            JOIN ten_k_filings tf ON tfs.original_filing_id = tf.id
            WHERE tfs.original_filing_id IN ($placeholders)
                AND tfs.processing_status = 'completed'
            ORDER BY tf.report_date DESC
        ");

        $stmt->execute($filingIds);
        $summaries = $stmt->fetchAll(PDO::FETCH_ASSOC);

        if (empty($summaries)) {
            return null;
        }

        return $summaries;
    } catch (Exception $e) {
        error_log("獲取摘要數據錯誤: " . $e->getMessage());
        return null;
    }
}

/**
 * 使用GPT-4O生成智能答案
 */
function generateGPT4OAnswer($question, $summaryData, $ticker)
{
    $openaiApiKey = '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';

    try {
        // 構建系統提示詞
        $systemPrompt = "你是一位專業的財務分析師和投資顧問，專門分析美股上市公司的10-K年報。你的任務是：

1. **深度分析**: 基於提供的10-K摘要數據，提供專業、深入的財務和業務分析
2. **數據驅動**: 所有分析都必須基於具體的財務數據和事實
3. **投資視角**: 從投資者角度提供有價值的洞察和建議
4. **風險評估**: 客觀評估公司面臨的風險和機會
5. **趨勢分析**: 分析多年份數據時，重點關注趨勢變化和發展軌跡

回答要求：
- 使用繁體中文回答
- 結構清晰，使用標題和列表
- 包含具體數據支持
- 提供專業但易懂的解釋
- 當有多年份數據時，進行對比分析
- 只回答有明確數據支持的內容";

        // 構建摘要內容
        $summaryContent = buildSummaryContent($summaryData, $ticker);

        // 構建用戶提示詞
        $userPrompt = "基於以下 $ticker 公司的10-K財報摘要數據，請回答用戶問題：

$summaryContent

用戶問題：$question

請提供專業、深入的分析，包含：
1. 直接回答用戶問題
2. 相關的財務數據支持
3. 業務背景和市場環境分析
4. 潛在的投資意義和風險提示
5. 如有多年份數據，請進行趨勢對比

回答格式請使用Markdown，包含適當的標題、列表和強調。";

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
            'model' => 'gpt-4o',  // 使用 GPT-4O 模型
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
            'max_tokens' => 3000,  // 增加token限制以獲得更詳細的回答
            'temperature' => 0.1,   // 低溫度確保準確性
            'presence_penalty' => 0.1,
            'frequency_penalty' => 0.1
        ];

        $jsonData = json_encode($data, JSON_UNESCAPED_UNICODE);
        if ($jsonData === false) {
            error_log("JSON編碼失敗: " . json_last_error_msg());
            curl_close($ch);
            return null;
        }

        curl_setopt($ch, CURLOPT_POSTFIELDS, $jsonData);

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
        error_log("生成GPT-4O答案錯誤: " . $e->getMessage());
        return null;
    }
}

/**
 * 構建摘要內容
 */
function buildSummaryContent($summaryData, $ticker)
{
    $content = "=== $ticker 公司 10-K 財報摘要數據 ===\n\n";
    $content .= "共包含 " . count($summaryData) . " 份財報的摘要內容\n\n";

    foreach ($summaryData as $index => $summary) {
        $reportYear = $summary['report_date'] ? date('Y', strtotime($summary['report_date'])) : '未知年份';
        $content .= "## 📊 第" . ($index + 1) . "份財報 - $reportYear 年\n\n";
        $content .= "**檔案**: {$summary['file_name']}\n";
        $content .= "**報告日期**: {$summary['report_date']}\n\n";

        // 重要的Items內容
        $importantItems = [
            'comprehensive_summary' => '綜合摘要',
            'item_1_summary' => 'Item 1 - 業務概況',
            'item_1a_summary' => 'Item 1A - 風險因素',
            'item_7_summary' => 'Item 7 - 管理層討論與分析',
            'item_8_summary' => 'Item 8 - 財務報表',
            'item_2_summary' => 'Item 2 - 物業',
            'item_3_summary' => 'Item 3 - 法律程序'
        ];

        foreach ($importantItems as $field => $title) {
            if (!empty($summary[$field])) {
                $content .= "### $title\n\n";
                $content .= $summary[$field] . "\n\n";
            }
        }

        $content .= "---\n\n";
    }

    return $content;
}

/**
 * 獲取或創建摘要對話
 */
function getOrCreateSummaryConversation($pdo, $ticker, $filingIds)
{
    // 生成對話標題
    $title = $ticker . '_摘要分析_' . count($filingIds) . '份財報';

    // 查找現有對話
    $stmt = $pdo->prepare("
        SELECT id FROM conversations 
        WHERE user_id = ? AND title = ?
        ORDER BY updated_at DESC 
        LIMIT 1
    ");
    $stmt->execute([$_SESSION['user_id'], $title]);
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
    $stmt->execute([$_SESSION['user_id'], $title]);
    return $pdo->lastInsertId();
}

/**
 * 快取答案
 */
function cacheAnswer($pdo, $cacheKey, $answer)
{
    try {
        $stmt = $pdo->prepare("
            INSERT INTO qa_cache (cache_key, answer, created_at, expires_at) 
            VALUES (?, ?, NOW(), DATE_ADD(NOW(), INTERVAL 7 DAY))
            ON DUPLICATE KEY UPDATE 
                answer = VALUES(answer), 
                created_at = NOW(), 
                expires_at = DATE_ADD(NOW(), INTERVAL 7 DAY)
        ");
        $stmt->execute([$cacheKey, $answer]);
    } catch (Exception $e) {
        error_log("快取答案錯誤: " . $e->getMessage());
    }
}

/**
 * 獲取快取答案
 */
function getCachedAnswer($pdo, $cacheKey)
{
    try {
        $stmt = $pdo->prepare("
            SELECT answer FROM qa_cache 
            WHERE cache_key = ? AND expires_at > NOW()
        ");
        $stmt->execute([$cacheKey]);
        $result = $stmt->fetch(PDO::FETCH_ASSOC);

        return $result ? $result['answer'] : null;
    } catch (Exception $e) {
        error_log("獲取快取答案錯誤: " . $e->getMessage());
        return null;
    }
}

/**
 * 儲存問答記錄
 */
function saveQuestionAnswer($pdo, $conversationId, $question, $answer, $userId)
{
    try {
        $stmt = $pdo->prepare("
            INSERT INTO questions (conversation_id, question, answer, user_id, created_at) 
            VALUES (?, ?, ?, ?, NOW())
        ");
        $stmt->execute([$conversationId, $question, $answer, $userId]);
        return $pdo->lastInsertId();
    } catch (Exception $e) {
        error_log("儲存問答記錄錯誤: " . $e->getMessage());
        return null;
    }
}

/**
 * 獲取對話訊息
 */
function getConversationMessages()
{
    $conversationId = trim($_POST['conversation_id'] ?? '');

    if (empty($conversationId)) {
        echo json_encode(['success' => false, 'error' => '對話ID不能為空']);
        return;
    }

    try {
        $db = new Database();
        $pdo = $db->getConnection();

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
 * 獲取對話歷史
 */
function getConversationHistory()
{
    try {
        $db = new Database();
        $pdo = $db->getConnection();

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