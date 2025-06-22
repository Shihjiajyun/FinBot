<?php
require_once 'config.php';

// 檢查登入狀態
if (!isset($_SESSION['user_id'])) {
    header('Location: index.php');
    exit;
}

$ticker = strtoupper(trim($_GET['ticker'] ?? ''));
$filename = trim($_GET['filename'] ?? '');

if (empty($ticker) || empty($filename)) {
    header('Location: index.php');
    exit;
}

// 驗證檔案參數安全性
if ($filename !== 'ALL' && (strpos($filename, '..') !== false || strpos($filename, '/') !== false || strpos($filename, '\\') !== false)) {
    header('Location: index.php');
    exit;
}

$isAllFiles = $filename === 'ALL';
$pageTitle = $isAllFiles ?
    "$ticker - 所有 10-K 檔案對話" :
    "$ticker - $filename 對話";

// 處理對話記錄
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
                    <i class="bi bi-<?= $isAllFiles ? 'collection' : 'file-earmark-text' ?>"></i>
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
                        <p>我可以幫您分析 <?= htmlspecialchars($ticker) ?> 的<?= $isAllFiles ? '所有' : '指定' ?> 10-K 財報檔案。請提出您的問題：
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
                    <textarea id="question-input" placeholder="請針對<?= $isAllFiles ? '所有' : '此份' ?> 10-K 檔案提出您的問題..."
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

    // 發送問題
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

        // 發送請求
        const formData = new FormData();
        formData.append('action', 'ask_10k_question');
        formData.append('ticker', ticker);
        formData.append('filename', filename);
        formData.append('question', question);

        fetch('stock_qa_api.php', {
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
                    // 添加回答
                    addMessage(messagesContainer, data.answer, 'bot');

                    // 通知父頁面更新對話歷史（如果是在iframe或有父頁面的情況）
                    try {
                        if (window.opener && window.opener.loadConversationHistory) {
                            window.opener.loadConversationHistory();
                        }
                    } catch (e) {
                        // 忽略跨域錯誤
                    }
                } else {
                    // 添加錯誤消息
                    addMessage(messagesContainer, `抱歉，處理您的問題時發生錯誤：${data.error}`, 'bot', false, true);
                }
            })
            .catch(error => {
                console.error('發送10-K問題失敗:', error);

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
                        <small>FinBot 正在分析 10-K 檔案...</small>
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

    // 自動聚焦輸入框
    document.getElementById('question-input').focus();
    </script>
</body>

</html>