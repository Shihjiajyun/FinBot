<?php
require_once 'config.php';

// 檢查登入狀態
if (!isset($_SESSION['user_id'])) {
    header('Location: index.php');
    exit;
}

$ticker = strtoupper(trim($_GET['ticker'] ?? ''));
$filename = trim($_GET['filename'] ?? '');
$filing_ids_str = trim($_GET['filing_ids'] ?? '');
$mode = trim($_GET['mode'] ?? '');

// 支援新的filing_ids模式或舊的filename模式
if (!empty($filing_ids_str) && $mode === 'summary') {
    // 新模式：多檔案摘要對話
    $filing_ids = array_filter(array_map('intval', explode(',', $filing_ids_str)));
    if (empty($ticker) || empty($filing_ids)) {
        header('Location: index.php');
        exit;
    }
    $usingSummaryMode = true;
    $filename = ''; // 摘要模式下設定空字串避免未定義警告
} else {
    // 舊模式：單檔案對話
    if (empty($ticker) || empty($filename)) {
        header('Location: index.php');
        exit;
    }

    // 驗證檔案參數安全性
    if ($filename !== 'ALL' && (strpos($filename, '..') !== false || strpos($filename, '/') !== false || strpos($filename, '\\') !== false)) {
        header('Location: index.php');
        exit;
    }
    $usingSummaryMode = false;
    $filing_ids = []; // 舊模式下設定空陣列避免未定義警告
}

// 處理對話記錄 - 移到這裡以便在生成頁面標題時可以使用資料庫連接
$db = new Database();
$pdo = $db->getConnection();
$conversationId = $_GET['conversation_id'] ?? null;
$existingConversation = null;

// 如果有 conversation_id，載入現有對話
if ($conversationId) {
    try {
        $stmt = $pdo->prepare("
            SELECT c.*, COUNT(q.id) as question_count 
            FROM conversations c 
            LEFT JOIN questions q ON c.id = q.conversation_id 
            WHERE c.id = ? AND c.user_id = ?
            GROUP BY c.id
        ");
        $stmt->execute([$conversationId, $_SESSION['user_id']]);
        $existingConversation = $stmt->fetch(PDO::FETCH_ASSOC);

        if (!$existingConversation) {
            // 對話不存在或不屬於當前用戶，重定向
            header('Location: index.php');
            exit;
        }
    } catch (Exception $e) {
        error_log("載入對話錯誤: " . $e->getMessage());
        header('Location: index.php');
        exit;
    }
}

// 從檔案名稱中提取年份的函數
function extractYearFromFilename($filename)
{
    // 支持多種檔案名稱格式
    // 例如: AAPL_10-K_2023.txt, MSFT-10K-2022.pdf, TSLA_2021_10-K.txt 等
    if (preg_match('/20\d{2}/', $filename, $matches)) {
        return $matches[0];
    }
    return $filename;
}

// 生成頁面標題
if ($usingSummaryMode) {
    // 摘要模式：多檔案分析
    $fileCount = count($filing_ids);

    // 從資料庫獲取財報年份信息
    try {
        $filing_ids_placeholder = implode(',', array_fill(0, count($filing_ids), '?'));
        $stmt = $pdo->prepare("
            SELECT DISTINCT YEAR(report_date) as year 
            FROM ten_k_filings 
            WHERE id IN ($filing_ids_placeholder)
            ORDER BY year DESC
        ");
        $stmt->execute($filing_ids);
        $years = $stmt->fetchAll(PDO::FETCH_COLUMN);

        if (!empty($years)) {
            if (count($years) == 1) {
                $yearText = $years[0] . " 年";
                $pageTitle = "$ticker - {$years[0]} 年 10-K 摘要對話";
            } else {
                $yearText = implode(', ', $years) . " 年";
                $pageTitle = "$ticker - {$fileCount}份 10-K 摘要對話 (" . implode(', ', $years) . ")";
            }
        } else {
            $yearText = "{$fileCount}份";
            $pageTitle = "$ticker - {$fileCount}份 10-K 摘要對話";
        }

        $displayText = $yearText . " 10-K 財報";
    } catch (Exception $e) {
        error_log("獲取財報年份失敗: " . $e->getMessage());
        $pageTitle = "$ticker - {$fileCount}份 10-K 摘要對話";
        $displayText = "{$fileCount}份 10-K 財報";
    }

    $isAllFiles = false; // 摘要模式不是全部檔案模式
} else {
    // 舊模式：單檔案對話
    $isAllFiles = $filename === 'ALL';
    if ($isAllFiles) {
        $pageTitle = "$ticker - 所有 10-K 檔案對話";
        $displayText = "所有年份";
    } else {
        $year = extractYearFromFilename($filename);
        $pageTitle = "$ticker - $year 年 10-K 對話";
        $displayText = $year . " 年";
    }
}
?>

<!DOCTYPE html>
<html lang="zh-TW">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?= htmlspecialchars($pageTitle) ?> - FinBot</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/markdown-it@13.0.1/dist/markdown-it.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
    <link rel="stylesheet" href="css/index.css">
    <style>
    .tenk-page-container {
        min-height: 100vh;
        background: var(--dark-bg);
        display: flex;
        flex-direction: column;
    }

    .tenk-page-header {
        background: linear-gradient(135deg, #2c5aa0 0%, #1a4480 100%);
        color: white;
        padding: 20px;
        border-bottom: 1px solid var(--dark-border);
    }

    .tenk-page-header h1 {
        margin: 0;
        font-size: 24px;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 15px;
    }

    .tenk-page-header .back-btn {
        background: rgba(255, 255, 255, 0.1);
        border: none;
        color: white;
        padding: 8px 12px;
        border-radius: 6px;
        cursor: pointer;
        transition: background 0.2s;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }

    .tenk-page-header .back-btn:hover {
        background: rgba(255, 255, 255, 0.2);
        color: white;
        text-decoration: none;
    }

    .tenk-chat-main {
        flex: 1;
        display: flex;
        flex-direction: column;
        max-height: calc(100vh - 80px);
    }

    .tenk-messages-container {
        flex: 1;
        padding: 25px;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        gap: 20px;
    }

    .tenk-messages-container::-webkit-scrollbar {
        width: 8px;
    }

    .tenk-messages-container::-webkit-scrollbar-track {
        background: var(--dark-sidebar);
    }

    .tenk-messages-container::-webkit-scrollbar-thumb {
        background: #444;
        border-radius: 4px;
    }

    .tenk-page-input {
        padding: 20px 25px;
        border-top: 1px solid var(--dark-border);
        background: var(--dark-sidebar);
    }

    .tenk-page-input .input-container {
        display: flex;
        gap: 12px;
        align-items: flex-end;
        max-width: 1000px;
        margin: 0 auto;
    }

    .tenk-page-input textarea {
        flex: 1;
        background: var(--dark-bg);
        border: 1px solid var(--dark-border);
        border-radius: 10px;
        padding: 12px 16px;
        color: white;
        font-size: 14px;
        resize: none;
        max-height: 120px;
        min-height: 45px;
        line-height: 1.4;
    }

    .tenk-page-input textarea:focus {
        outline: none;
        border-color: #2c5aa0;
        box-shadow: 0 0 0 2px rgba(44, 90, 160, 0.2);
    }

    .tenk-page-input textarea::placeholder {
        color: var(--text-muted);
    }

    .tenk-page-input button {
        background: #2c5aa0;
        border: none;
        color: white;
        width: 45px;
        height: 45px;
        border-radius: 10px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: background 0.2s;
        font-size: 16px;
        flex-shrink: 0;
    }

    .tenk-page-input button:hover:not(:disabled) {
        background: #1a4480;
    }

    .tenk-page-input button:disabled {
        background: #555;
        cursor: not-allowed;
    }

    .welcome-message {
        max-width: 800px;
        margin: 0 auto;
    }

    .chat-message {
        max-width: 800px;
        margin: 0 auto;
        width: 100%;
    }

    .chat-message .message-content {
        max-width: 75%;
    }

    /* 全屏loading樣式 */
    .fullscreen-loading-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100vh;
        background: linear-gradient(135deg,
                rgba(28, 30, 60, 0.98) 0%,
                rgba(44, 90, 160, 0.95) 50%,
                rgba(32, 201, 151, 0.92) 100%);
        backdrop-filter: blur(10px);
        z-index: 9999;
        display: flex;
        align-items: center;
        justify-content: center;
        opacity: 0;
        visibility: hidden;
        transition: all 0.3s ease;
        overflow-y: auto;
        padding: 20px;
        box-sizing: border-box;
    }

    .fullscreen-loading-overlay.show {
        opacity: 1;
        visibility: visible;
    }

    .fullscreen-loading-content {
        text-align: center;
        color: white;
        max-width: 500px;
        width: 100%;
        padding: 30px;
        margin: auto;
        min-height: fit-content;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    .loading-animation {
        margin-bottom: 30px;
        position: relative;
    }

    .loading-spinner {
        width: 80px;
        height: 80px;
        border: 4px solid rgba(255, 255, 255, 0.3);
        border-top: 4px solid #ffffff;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin: 0 auto 20px;
    }

    @keyframes spin {
        0% {
            transform: rotate(0deg);
        }

        100% {
            transform: rotate(360deg);
        }
    }

    .loading-dots {
        display: flex;
        justify-content: center;
        gap: 8px;
    }

    .loading-dots span {
        width: 12px;
        height: 12px;
        background: rgba(255, 255, 255, 0.8);
        border-radius: 50%;
        animation: bounce 1.4s ease-in-out both infinite;
    }

    .loading-dots span:nth-child(1) {
        animation-delay: -0.32s;
    }

    .loading-dots span:nth-child(2) {
        animation-delay: -0.16s;
    }

    .loading-dots span:nth-child(3) {
        animation-delay: 0s;
    }

    @keyframes bounce {

        0%,
        80%,
        100% {
            transform: scale(0.8);
            opacity: 0.5;
        }

        40% {
            transform: scale(1.2);
            opacity: 1;
        }
    }

    .loading-title {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 15px;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
    }

    .loading-subtitle {
        font-size: 1.1rem;
        opacity: 0.9;
        margin-bottom: 40px;
        line-height: 1.5;
    }

    .loading-steps {
        display: flex;
        justify-content: center;
        gap: 30px;
        margin-bottom: 40px;
        flex-wrap: wrap;
    }

    .loading-steps .step {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 10px;
        opacity: 0.4;
        transition: all 0.3s ease;
        min-width: 120px;
    }

    .loading-steps .step.active {
        opacity: 1;
        transform: scale(1.1);
    }

    .loading-steps .step.processing {
        opacity: 0.8;
        animation: pulse 2s ease-in-out infinite;
    }

    @keyframes pulse {

        0%,
        100% {
            opacity: 0.8;
        }

        50% {
            opacity: 1;
            transform: scale(1.05);
        }
    }

    .loading-steps .step i {
        font-size: 1.5rem;
        margin-bottom: 5px;
    }

    .loading-steps .step span {
        font-size: 0.9rem;
        text-align: center;
    }

    .loading-progress {
        width: 100%;
        max-width: 400px;
        margin: 0 auto;
    }

    .progress-bar {
        width: 100%;
        height: 6px;
        background: rgba(255, 255, 255, 0.2);
        border-radius: 3px;
        overflow: hidden;
        margin-bottom: 15px;
    }

    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #20c997, #28a745);
        width: 0%;
        animation: progress 3s ease-in-out infinite;
    }

    @keyframes progress {
        0% {
            width: 0%;
        }

        50% {
            width: 70%;
        }

        100% {
            width: 100%;
        }
    }

    .progress-text {
        text-align: center;
        font-size: 0.9rem;
        opacity: 0.8;
        margin: 0;
    }

    /* 響應式設計 */
    @media (max-width: 768px) {
        .tenk-page-header {
            padding: 15px;
        }

        .tenk-page-header h1 {
            font-size: 18px;
        }

        .tenk-messages-container {
            padding: 15px;
        }

        .tenk-page-input {
            padding: 15px;
        }

        .chat-message .message-content {
            max-width: 85%;
        }

        .fullscreen-loading-content {
            padding: 20px;
            max-width: 90%;
        }

        .loading-title {
            font-size: 2rem;
        }

        .loading-subtitle {
            font-size: 1rem;
        }

        .loading-steps {
            gap: 20px;
            margin-bottom: 30px;
        }

        .loading-steps .step {
            min-width: 100px;
        }

        .loading-steps .step span {
            font-size: 0.8rem;
        }

        .loading-spinner {
            width: 60px;
            height: 60px;
        }
    }

    @media (max-width: 480px) {
        .fullscreen-loading-content {
            padding: 15px;
        }

        .loading-title {
            font-size: 1.8rem;
            margin-bottom: 10px;
        }

        .loading-subtitle {
            font-size: 0.9rem;
            margin-bottom: 30px;
        }

        .loading-steps {
            gap: 15px;
            margin-bottom: 25px;
        }

        .loading-steps .step {
            min-width: 80px;
        }

        .loading-steps .step i {
            font-size: 1.2rem;
        }

        .loading-steps .step span {
            font-size: 0.75rem;
        }

        .loading-spinner {
            width: 50px;
            height: 50px;
            margin-bottom: 15px;
        }

        .progress-text {
            font-size: 0.8rem;
        }
    }

    /* 確保在極小螢幕上也能正常顯示 */
    @media (max-height: 600px) {
        .fullscreen-loading-content {
            justify-content: flex-start;
            padding-top: 50px;
        }

        .loading-title {
            font-size: 1.5rem;
            margin-bottom: 8px;
        }

        .loading-subtitle {
            font-size: 0.85rem;
            margin-bottom: 20px;
        }

        .loading-steps {
            margin-bottom: 20px;
        }

        .loading-animation {
            margin-bottom: 20px;
        }

        .loading-spinner {
            width: 40px;
            height: 40px;
            margin-bottom: 10px;
        }
    }
    </style>
    <script>
    // 初始化 markdown-it
    window.md = markdownit({
        html: true,
        linkify: true,
        typographer: true,
        breaks: true
    });
    </script>
</head>

<body>
    <div class="tenk-page-container">
        <div class="tenk-page-header">
            <div class="d-flex justify-content-between align-items-center">
                <h1>
                    <i class="bi bi-<?= $isAllFiles ? 'collection' : 'calendar3' ?>"></i>
                    <?= htmlspecialchars($pageTitle) ?>
                </h1>
                <a href="index.php" class="back-btn">
                    <i class="bi bi-arrow-left"></i>
                    返回股票查詢
                </a>
            </div>
        </div>

        <div class="tenk-chat-main">
            <div class="tenk-messages-container" id="messages-container">
                <div class="welcome-message">
                    <div class="bot-avatar">
                        <i class="bi bi-robot"></i>
                    </div>
                    <div class="message-content">
                        <h5>歡迎使用 FinBot 10-K 分析</h5>
                        <p>我可以幫您分析 <?= htmlspecialchars($ticker) ?>
                            的<?= $isAllFiles ? '所有年份' : htmlspecialchars($displayText) ?> 10-K 財報檔案。請提出您的問題：
                        </p>
                        <div class="suggested-questions">
                            <button class="suggested-btn" onclick="askSuggestedQuestion('公司的主要業務和產品線有哪些？')">
                                主要業務
                            </button>
                            <button class="suggested-btn" onclick="askSuggestedQuestion('最主要的風險因素是什麼？')">
                                風險因素
                            </button>
                            <button class="suggested-btn" onclick="askSuggestedQuestion('請用圖表顯示公司近年來的財務表現')">
                                財務圖表
                            </button>
                            <button class="suggested-btn" onclick="askSuggestedQuestion('未來的發展策略和計劃是什麼？')">
                                未來計劃
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <div class="tenk-page-input">
                <div class="input-container">
                    <textarea id="question-input"
                        placeholder="請針對<?= $isAllFiles ? '所有年份' : htmlspecialchars($displayText) ?> 10-K 檔案提出您的問題..."
                        rows="2"></textarea>
                    <button id="send-button" onclick="sendQuestion()">
                        <i class="bi bi-send"></i>
                    </button>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="js/financial-tables.js"></script>

    <script>
    const ticker = <?= json_encode($ticker) ?>;
    const filename = <?= json_encode($filename) ?>;
    const displayText = <?= json_encode($displayText) ?>;
    const isAllFiles = <?= json_encode($isAllFiles) ?>;
    const conversationId = <?= $conversationId ? $conversationId : 'null' ?>;
    const existingConversation = <?= $existingConversation ? json_encode($existingConversation) : 'null' ?>;

    // 載入現有對話（如果有的話）
    function loadExistingConversation() {
        if (conversationId && existingConversation) {
            console.log('載入現有對話:', existingConversation);

            // 載入對話中的問答記錄
            loadConversationMessages(conversationId);
        }
    }

    // 載入對話訊息
    function loadConversationMessages(convId) {
        const formData = new FormData();
        formData.append('action', 'get_conversation_messages');
        formData.append('conversation_id', convId);

        fetch('stock_qa_api.php', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.messages) {
                    const messagesContainer = document.getElementById('messages-container');

                    // 清除歡迎訊息
                    const welcomeMessage = messagesContainer.querySelector('.welcome-message');
                    if (welcomeMessage) {
                        welcomeMessage.remove();
                    }

                    // 添加歷史訊息
                    data.messages.forEach(msg => {
                        addMessage(messagesContainer, msg.question, 'user');
                        addMessage(messagesContainer, msg.answer, 'bot');
                    });
                }
            })
            .catch(error => {
                console.error('載入對話訊息錯誤:', error);
            });
    }

    // 頁面載入時檢查是否需要載入現有對話
    document.addEventListener('DOMContentLoaded', function() {
        loadExistingConversation();
    });

    // 發送問題到新的摘要API
    function sendQuestion() {
        const inputElement = document.getElementById('question-input');
        const sendButton = document.getElementById('send-button');
        const messagesContainer = document.getElementById('messages-container');

        const question = inputElement.value.trim();
        if (!question) {
            alert('請輸入問題');
            return;
        }

        // 禁用輸入
        inputElement.disabled = true;
        sendButton.disabled = true;
        sendButton.innerHTML = '<i class="bi bi-hourglass-split"></i>';

        // 添加用戶問題
        addMessage(messagesContainer, question, 'user');

        // 清空輸入框
        inputElement.value = '';

        // 顯示機器人思考狀態
        addMessage(messagesContainer, '', 'bot', true);

        // 準備請求數據
        const formData = new FormData();
        let apiUrl;

        <?php if ($usingSummaryMode): ?>
        // 使用新的摘要模式API
        formData.append('action', 'ask_summary_question');
        formData.append('ticker', ticker);
        formData.append('filing_ids', JSON.stringify(<?= json_encode($filing_ids ?? []) ?>));
        formData.append('question', question);
        apiUrl = 'tenk_summary_chat_api.php';
        <?php else: ?>
        // 使用舊的單檔案模式API
        formData.append('action', 'ask_10k_question');
        formData.append('ticker', ticker);
        formData.append('filename', filename);
        formData.append('question', question);
        apiUrl = 'stock_qa_api.php';
        <?php endif; ?>

        fetch(apiUrl, {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                // 移除思考狀態
                const thinkingMessage = messagesContainer.querySelector('.thinking-message');
                if (thinkingMessage) {
                    thinkingMessage.remove();
                }

                if (data.success) {
                    // 添加機器人回答
                    addMessage(messagesContainer, data.answer, 'bot');
                } else {
                    addMessage(messagesContainer, '抱歉，我無法回答這個問題：' + (data.error || '未知錯誤'), 'bot', false, true);
                }
            })
            .catch(error => {
                console.error('發送問題錯誤:', error);

                // 移除思考狀態
                const thinkingMessage = messagesContainer.querySelector('.thinking-message');
                if (thinkingMessage) {
                    thinkingMessage.remove();
                }

                addMessage(messagesContainer, '網路錯誤，請稍後再試', 'bot', false, true);
            })
            .finally(() => {
                // 恢復輸入狀態
                inputElement.disabled = false;
                sendButton.disabled = false;
                sendButton.innerHTML = '<i class="bi bi-send"></i>';
                inputElement.focus();
            });
    }

    // 添加消息
    function addMessage(messagesContainer, content, sender, isThinking = false, isError = false) {
        const messageDiv = document.createElement('div');

        if (isThinking) {
            messageDiv.className = 'chat-message bot thinking-message';
            messageDiv.innerHTML = `
                    <div class="bot-avatar">
                        <i class="bi bi-robot"></i>
                    </div>
                    <div class="message-content">
                        <div class="thinking-animation">
                            <span></span><span></span><span></span>
                        </div>
                        <small>FinBot 正在分析 ${isAllFiles ? '所有年份' : displayText} 10-K 檔案...</small>
                    </div>
                `;
        } else {
            messageDiv.className = `chat-message ${sender}${isError ? ' error' : ''}`;

            if (sender === 'user') {
                messageDiv.innerHTML = `
                        <div class="message-content">
                            ${escapeHtml(content)}
                        </div>
                        <div class="user-avatar">
                            <i class="bi bi-person"></i>
                        </div>
                    `;
            } else {
                messageDiv.innerHTML = `
                        <div class="bot-avatar">
                            <i class="bi bi-robot"></i>
                        </div>
                        <div class="message-content">
                            ${isError ? escapeHtml(content) : formatAnswer(content)}
                        </div>
                    `;
            }
        }

        messagesContainer.appendChild(messageDiv);
        messageDiv.scrollIntoView({
            behavior: 'smooth'
        });
    }

    // 建議問題
    function askSuggestedQuestion(question) {
        const inputElement = document.getElementById('question-input');
        inputElement.value = question;
        sendQuestion();
    }

    // HTML轉義
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // 格式化回答（使用markdown）
    function formatAnswer(answer) {
        // 檢查是否包含圖表數據
        const chartRegex = /```chart\s*([\s\S]*?)\s*```/g;
        const charts = [];
        let match;

        // 提取所有圖表數據
        while ((match = chartRegex.exec(answer)) !== null) {
            try {
                const chartData = JSON.parse(match[1]);
                charts.push(chartData);
            } catch (e) {
                console.error('圖表數據解析錯誤:', e);
                console.log('原始圖表數據:', match[1]);
            }
        }

        // 移除圖表數據標記，保留純文字內容
        let cleanAnswer = answer.replace(chartRegex, '');

        // 使用markdown-it渲染
        let formattedAnswer;
        try {
            formattedAnswer = window.md.render(cleanAnswer);
        } catch (e) {
            console.error('Markdown渲染錯誤:', e);
            formattedAnswer = escapeHtml(cleanAnswer).replace(/\n/g, '<br>');
        }

        // 如果有圖表，添加圖表容器
        if (charts.length > 0) {
            charts.forEach((chartData, index) => {
                const chartId = `chart-${Date.now()}-${index}`;
                formattedAnswer +=
                    `<div class="chart-container" style="margin: 20px 0; background: var(--dark-sidebar); border-radius: 8px; padding: 15px;"><canvas id="${chartId}" style="max-height: 400px;"></canvas></div>`;

                // 延遲渲染圖表
                setTimeout(() => {
                    renderChart(chartId, chartData);
                }, 100);
            });
        }

        return formattedAnswer;
    }

    // 渲染圖表
    function renderChart(canvasId, chartData) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.error('找不到canvas元素:', canvasId);
            return;
        }

        try {
            console.log('正在渲染圖表:', canvasId, chartData);

            // 設置深色主題的預設樣式
            const defaultOptions = {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#ffffff'
                        }
                    },
                    title: {
                        color: '#ffffff'
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: '#ffffff'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    y: {
                        ticks: {
                            color: '#ffffff'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                }
            };

            // 合併預設選項和自定義選項
            if (chartData.options) {
                chartData.options = Object.assign({}, defaultOptions, chartData.options);
            } else {
                chartData.options = defaultOptions;
            }

            new Chart(canvas, chartData);
            console.log('圖表渲染成功:', canvasId);
        } catch (error) {
            console.error('圖表渲染錯誤:', error);
            console.log('錯誤的圖表數據:', chartData);
            canvas.parentElement.innerHTML = '<p style="color: #ff6b6b; text-align: center; padding: 20px;">圖表渲染失敗：' +
                error.message + '</p>';
        }
    }

    // Enter鍵發送
    document.getElementById('question-input').addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendQuestion();
        }
    });

    // 檢查並處理摘要
    async function checkAndProcessSummaries() {
        const ticker = '<?= $ticker ?>';
        const filingIds = <?= json_encode($filing_ids ?? []) ?>;

        try {
            // 檢查摘要狀態
            const formData = new FormData();
            formData.append('action', 'check_summary_status');
            formData.append('ticker', ticker);
            formData.append('filing_ids', JSON.stringify(filingIds));

            const response = await fetch('summarize_filings.php', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                // 檢查哪些檔案需要摘要
                const needsSummary = filingIds.filter(id => {
                    const status = data.summary_statuses[id];
                    return !status.has_summary || status.status !== 'completed';
                });

                if (needsSummary.length > 0) {
                    // 顯示loading並開始摘要
                    showSummaryProgress(ticker, needsSummary.length);
                    await processSummaries(ticker, needsSummary);
                } else {
                    // 所有檔案都已摘要，可以開始對話
                    console.log('所有檔案已完成摘要，可以開始對話');
                }
            } else {
                console.error('檢查摘要狀態失敗:', data.error);
            }
        } catch (error) {
            console.error('檢查摘要時發生錯誤:', error);
        }
    }

    // 顯示摘要進度 - 全屏loading
    function showSummaryProgress(ticker, fileCount) {
        // 創建全屏loading overlay
        const loadingOverlay = document.createElement('div');
        loadingOverlay.id = 'fullscreen-loading-overlay';
        loadingOverlay.className = 'fullscreen-loading-overlay';
        loadingOverlay.innerHTML = `
            <div class="fullscreen-loading-content">
                <div class="loading-animation">
                    <div class="loading-spinner"></div>
                    <div class="loading-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
                <h1 class="loading-title">🤖 閱讀財報中</h1>
                <p class="loading-subtitle">正在分析 ${ticker} 的 ${fileCount} 份 10-K 財報</p>
                <div class="loading-steps">
                    <div class="step active">
                        <i class="bi bi-file-text"></i> 
                        <span>準備財報數據</span>
                    </div>
                    <div class="step processing">
                        <i class="bi bi-cpu"></i> 
                        <span>智能分析中</span>
                    </div>
                    <div class="step">
                        <i class="bi bi-chat-dots"></i> 
                        <span>準備對話界面</span>
                    </div>
                </div>
                <div class="loading-progress">
                    <div class="progress-bar">
                        <div class="progress-fill"></div>
                    </div>
                    <p class="progress-text">這可能需要 1-2 分鐘，請耐心等候...</p>
                </div>
            </div>
        `;

        // 添加到body最頂層
        document.body.appendChild(loadingOverlay);

        // 添加動畫效果
        setTimeout(() => {
            loadingOverlay.classList.add('show');
        }, 100);

        // 禁用頁面滾動
        document.body.style.overflow = 'hidden';
    }

    // 處理摘要
    async function processSummaries(ticker, filingIds) {
        try {
            const formData = new FormData();
            formData.append('action', 'summarize_filings');
            formData.append('ticker', ticker);
            formData.append('filing_ids', JSON.stringify(filingIds));

            const response = await fetch('summarize_filings.php', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                // 摘要完成，隱藏loading並啟用輸入
                hideSummaryProgress();
                showSummaryComplete(ticker, filingIds.length);
            } else {
                console.error('摘要失敗:', data.error);
                hideSummaryProgress();
                showSummaryError(data.error);
            }
        } catch (error) {
            console.error('摘要過程中發生錯誤:', error);
            hideSummaryProgress();
            showSummaryError('網路錯誤');
        }
    }

    // 隱藏摘要進度
    function hideSummaryProgress() {
        const loadingOverlay = document.getElementById('fullscreen-loading-overlay');
        if (loadingOverlay) {
            // 添加淡出動畫
            loadingOverlay.classList.remove('show');

            // 延遲移除元素，讓動畫完成
            setTimeout(() => {
                if (loadingOverlay.parentNode) {
                    loadingOverlay.parentNode.removeChild(loadingOverlay);
                }
            }, 300);
        }

        // 恢復頁面滾動
        document.body.style.overflow = '';

        // 恢復輸入聚焦
        setTimeout(() => {
            const inputElement = document.getElementById('question-input');
            if (inputElement) {
                inputElement.focus();
            }
        }, 300);
    }

    // 顯示摘要完成訊息
    function showSummaryComplete(ticker, fileCount) {
        const messagesContainer = document.querySelector('.tenk-messages-container');

        const completeDiv = document.createElement('div');
        completeDiv.className = 'chat-message bot';
        completeDiv.innerHTML = `
                <div class="bot-avatar">
                    <i class="bi bi-robot"></i>
                </div>
                <div class="message-content">
                    <h5>🎉 財報分析完成！</h5>
                    <p>我已經成功分析了 <strong>${ticker}</strong> 的 <strong>${fileCount}</strong> 份 10-K 財報。</p>
                    <p>您現在可以問我關於：</p>
                    <ul>
                        <li>📊 財務表現與趨勢</li>
                        <li>🎯 業務策略與營運重點</li>
                        <li>⚠️ 風險因素與挑戰</li>
                        <li>💰 收入結構與獲利能力</li>
                        <li>🔮 未來展望與計劃</li>
                    </ul>
                    <p>請告訴我您想了解什麼？</p>
                </div>
            `;

        messagesContainer.appendChild(completeDiv);
        completeDiv.scrollIntoView({
            behavior: 'smooth'
        });
    }

    // 顯示摘要錯誤
    function showSummaryError(error) {
        const messagesContainer = document.querySelector('.tenk-messages-container');

        const errorDiv = document.createElement('div');
        errorDiv.className = 'chat-message bot error';
        errorDiv.innerHTML = `
                <div class="bot-avatar">
                    <i class="bi bi-robot"></i>
                </div>
                <div class="message-content">
                    <h5>❌ 財報分析失敗</h5>
                    <p>很抱歉，財報分析過程中發生錯誤：${error}</p>
                    <p>請嘗試重新載入頁面或聯繫管理員。</p>
                </div>
            `;

        messagesContainer.appendChild(errorDiv);
        errorDiv.scrollIntoView({
            behavior: 'smooth'
        });
    }

    // 自動聚焦輸入框
    document.getElementById('question-input').focus();

    <?php if ($usingSummaryMode): ?>
    // 摘要模式：檢查是否需要進行摘要
    checkAndProcessSummaries();
    <?php endif; ?>
    </script>
</body>

</html>