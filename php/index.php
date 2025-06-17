<?php
require_once 'config.php';

// 檢查登入狀態
function check_login()
{
    return isset($_SESSION['user_id']) && !empty($_SESSION['user_id']);
}

// 處理登入
if ($_POST['action'] ?? '' === 'login') {
    $username = sanitize_input($_POST['username'] ?? '');
    $password = $_POST['password'] ?? '';

    if ($username && $password) {
        $db = new Database();
        $pdo = $db->getConnection();

        $stmt = $pdo->prepare("SELECT id, username, password_hash, nickname FROM users WHERE username = ?");
        $stmt->execute([$username]);
        $user = $stmt->fetch();

        if ($user && password_verify($password, $user['password_hash'])) {
            $_SESSION['user_id'] = $user['id'];
            $_SESSION['username'] = $user['username'];
            $_SESSION['nickname'] = $user['nickname'];
            redirect('index.php');
        } else {
            $login_error = "帳號或密碼錯誤";
        }
    }
}

// 處理登出
if ($_GET['action'] ?? '' === 'logout') {
    session_destroy();
    redirect('index.php');
}

$is_logged_in = check_login();

// 現在對話歷史由JavaScript動態載入
?>

<!DOCTYPE html>
<html lang="zh-TW">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FinBot - 財務報表分析機器人</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/markdown-it@13.0.1/dist/markdown-it.min.js"></script>
    <link rel="stylesheet" href="css/index.css">
</head>

<body>
    <?php if (!$is_logged_in): ?>
    <!-- 登入頁面 -->
    <div class="login-container">
        <div class="login-card">
            <div class="login-header">
                <i class="bi bi-robot" style="font-size: 3rem; color: var(--primary-color);"></i>
                <h2 class="mt-3">FinBot</h2>
                <p class="text-muted">財務報表分析機器人</p>
            </div>

            <?php if (isset($login_error)): ?>
            <div class="alert alert-danger"><?= $login_error ?></div>
            <?php endif; ?>

            <form method="POST" class="login-form">
                <input type="hidden" name="action" value="login">
                <input type="text" class="form-control" name="username" placeholder="帳號" required>
                <input type="password" class="form-control" name="password" placeholder="密碼" required>
                <button type="submit" class="login-btn">登入</button>
            </form>

            <div class="mt-3 text-center">
                <small class="text-muted">
                    測試帳號: admin / password<br>
                    或 demo / password
                </small>
            </div>
        </div>
    </div>
    <?php else: ?>
    <!-- 主應用界面 -->
    <div class="sidebar">
        <div class="sidebar-header">
            <button class="new-chat-btn" onclick="startNewChat()">
                <i class="bi bi-plus"></i>
                新對話
            </button>
        </div>

        <div class="chat-history" id="chat-history">
            <!-- 對話歷史將由JavaScript載入 -->
        </div>

        <div class="sidebar-footer">
            <div class="user-info">
                <i class="bi bi-person-circle"></i>
                <span><?= htmlspecialchars($_SESSION['nickname'] ?? $_SESSION['username']) ?></span>
            </div>
            <a href="?action=logout" class="logout-btn">
                <i class="bi bi-box-arrow-right"></i> 登出
            </a>
        </div>
    </div>

    <div class="main-content">
        <div class="mobile-header d-md-none">
            <button class="menu-toggle" onclick="toggleSidebar()">
                <i class="bi bi-list"></i>
            </button>
            <span class="ms-2">FinBot</span>
            <button class="history-toggle" onclick="toggleSidebar()">
                <i class="bi bi-clock-history"></i>
            </button>
        </div>

        <div class="chat-container" id="chat-container">
            <div class="welcome-message" id="welcome-message">
                <i class="bi bi-robot" style="font-size: 4rem; color: var(--primary-color); margin-bottom: 20px;"></i>
                <h2>歡迎使用 FinBot</h2>
                <p style="color: #8e8ea0; margin: 20px 0;">
                    我是您的財務報表分析助手，可以幫您分析任何上市公司的財務狀況。
                    <br>試著問我一些問題吧！
                </p>
                <div class="example-grid">
                    <div class="example-question" onclick="askExample('[AAPL] 2023年的營收表現如何？')">
                        <i class="bi bi-graph-up"></i>
                        <div style="margin-top: 8px; font-size: 14px;">[AAPL] 2023年的營收表現如何？</div>
                    </div>
                    <div class="example-question" onclick="askExample('[TSLA] 最新季度的毛利率是多少？')">
                        <i class="bi bi-percent"></i>
                        <div style="margin-top: 8px; font-size: 14px;">[TSLA] 最新季度的毛利率是多少？</div>
                    </div>
                    <div class="example-question" onclick="askExample('[MSFT] 債務狀況如何？')">
                        <i class="bi bi-bank"></i>
                        <div style="margin-top: 8px; font-size: 14px;">[MSFT] 債務狀況如何？</div>
                    </div>
                    <div class="example-question" onclick="askExample('[AMZN] 現金流狀況怎麼樣？')">
                        <i class="bi bi-cash-stack"></i>
                        <div style="margin-top: 8px; font-size: 14px;">[AMZN] 現金流狀況怎麼樣？</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="input-area">
            <!-- 全屏Loading覆蓋層 -->
            <div class="fullscreen-loading" id="fullscreen-loading">
                <div class="loading-overlay">
                    <div class="loading-content">
                        <div class="spinner-large"></div>
                        <h3>🤖 FinBot 正在分析中...</h3>
                        <p id="loading-text">正在分析您的問題並搜尋相關財報數據</p>
                        <div class="loading-steps">
                            <div class="step" id="step1">📋 分析問題類型</div>
                            <div class="step" id="step2">🔍 搜尋財報數據</div>
                            <div class="step" id="step3">🧠 AI 智能分析</div>
                            <div class="step" id="step4">📊 生成專業回答</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 預設問題按鈕 -->
            <div class="preset-questions" id="preset-questions">
                <button class="preset-btn" onclick="askExample('[AAPL] 2023年營收表現如何？')">[AAPL] 2023年營收如何？</button>
                <button class="preset-btn" onclick="askExample('[TSLA] 最新季度毛利率多少？')">[TSLA] 毛利率多少？</button>
                <button class="preset-btn" onclick="askExample('[MSFT] 債務狀況如何？')">[MSFT] 債務狀況？</button>
                <button class="preset-btn" onclick="askExample('[AMZN] 現金流狀況怎麼樣？')">[AMZN] 現金流？</button>
                <button class="preset-btn" onclick="askExample('[META] 成長率如何？')">[META] 成長率？</button>
            </div>

            <div class="input-container">
                <form id="question-form">
                    <textarea class="message-input" id="question-input"
                        placeholder="請使用格式：[股票代碼] 您的問題&#10;例如：[AAPL] 2023年營收表現如何？" rows="1" required></textarea>
                    <button type="submit" class="send-button" id="send-button">
                        <i class="bi bi-send"></i>
                    </button>
                </form>
            </div>
        </div>
    </div>
    <?php endif; ?>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
    <?php if ($is_logged_in): ?>
    let currentConversationId = null;

    // 初始化 Markdown 渲染器
    const md = window.markdownit({
        html: true,
        linkify: true,
        typographer: true
    });

    // 自動調整輸入框高度
    const input = document.getElementById('question-input');
    input.addEventListener('input', function() {
        this.style.height = '60px';
        this.style.height = Math.min(this.scrollHeight, 150) + 'px';

        // 如果內容超出最大高度，顯示滾動條
        if (this.scrollHeight > 150) {
            this.style.overflowY = 'auto';
        } else {
            this.style.overflowY = 'hidden';
        }
    });

    // 載入對話歷史
    function loadConversations() {
        fetch('api_improved.php?action=get_conversations')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const historyContainer = document.getElementById('chat-history');
                    if (data.conversations.length === 0) {
                        historyContainer.innerHTML = `
                                    <div class="text-center" style="color: #8e8ea0; padding: 20px; font-size: 14px;">
                                        暫無對話記錄
                                    </div>
                                `;
                    } else {
                        historyContainer.innerHTML = `
                                    <div class="mb-2" style="color: #8e8ea0; font-size: 12px; padding: 0 12px;">
                                        最近對話
                                    </div>
                                ` + data.conversations.map(conv => `
                                    <div class="history-item" data-conversation-id="${conv.id}">
                                        <div class="history-content" onclick="loadConversation(${conv.id})">
                                            <i class="bi bi-chat-dots"></i>
                                            <div class="question-preview" id="conv-title-${conv.id}">
                                                ${conv.title || (conv.last_question ? conv.last_question.substring(0, 30) + '...' : '新對話')}
                                            </div>
                                        </div>
                                        <div class="history-actions">
                                            <button class="edit-conv-btn" onclick="editConversationTitle(${conv.id}, '${(conv.title || '新對話').replace(/'/g, "\\'")}')">
                                                <i class="bi bi-pencil"></i>
                                            </button>
                                        </div>
                                    </div>
                                `).join('');
                    }
                }
            })
            .catch(err => console.error('載入對話失敗:', err));
    }

    // 發送問題
    document.getElementById('question-form').addEventListener('submit', function(e) {
        e.preventDefault();

        const question = input.value.trim();
        if (!question) return;

        // 隱藏歡迎訊息和預設問題
        const welcomeMessage = document.getElementById('welcome-message');
        const presetQuestions = document.getElementById('preset-questions');
        if (welcomeMessage) {
            welcomeMessage.style.display = 'none';
        }
        if (presetQuestions) {
            presetQuestions.style.display = 'none';
        }

        // 顯示用戶問題
        addMessage(question, 'user');
        input.value = '';
        input.style.height = 'auto';

        // 顯示載入狀態
        showLoading(true);

        // 開始Loading步驟動畫
        startLoadingSteps();

        // 準備請求數據
        const formData = new FormData();
        formData.append('action', 'ask');
        formData.append('question', question);
        if (currentConversationId) {
            formData.append('conversation_id', currentConversationId);
        }

        // 發送到後端
        fetch('api_improved.php', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                showLoading(false);
                if (data.success) {
                    currentConversationId = data.conversation_id;
                    addMessage(data.answer, 'bot');
                    // 重新載入對話歷史
                    loadConversations();
                } else {
                    addMessage('抱歉，處理您的問題時發生錯誤：' + data.error, 'bot');
                }
            })
            .catch(error => {
                showLoading(false);
                addMessage('網路錯誤，請稍後再試。', 'bot');
                console.error('發送錯誤:', error);
            });
    });

    function addMessage(text, sender) {
        const chatContainer = document.getElementById('chat-container');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;

        const avatar = sender === 'user' ?
            '<div class="message-avatar"><i class="bi bi-person"></i></div>' :
            '<div class="message-avatar"><i class="bi bi-robot"></i></div>';

        // 對於機器人回答，使用 Markdown 渲染
        let processedText;
        if (sender === 'bot') {
            processedText = md.render(text);
        } else {
            processedText = text.replace(/\n/g, '<br>');
        }

        messageDiv.innerHTML = `
                <div class="message-content">
                    ${sender === 'bot' ? avatar : ''}
                    <div class="message-text">${processedText}</div>
                    ${sender === 'user' ? avatar : ''}
                </div>
            `;

        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function showLoading(show) {
        const loading = document.getElementById('fullscreen-loading');
        const sendBtn = document.getElementById('send-button');

        if (show) {
            loading.classList.add('show');
            sendBtn.disabled = true;
            // 禁用整個頁面的點擊
            document.body.style.pointerEvents = 'none';
            loading.style.pointerEvents = 'auto';
        } else {
            loading.classList.remove('show');
            sendBtn.disabled = false;
            // 恢復頁面點擊
            document.body.style.pointerEvents = 'auto';
            // 重置所有步驟狀態
            resetLoadingSteps();
        }
    }

    function startLoadingSteps() {
        const steps = ['step1', 'step2', 'step3', 'step4'];
        const texts = [
            '正在分析問題類型...',
            '正在搜尋相關財報數據...',
            '正在進行AI智能分析...',
            '正在生成專業回答...'
        ];

        let currentStep = 0;

        function activateStep() {
            if (currentStep > 0) {
                document.getElementById(steps[currentStep - 1]).classList.remove('active');
                document.getElementById(steps[currentStep - 1]).classList.add('completed');
            }

            if (currentStep < steps.length) {
                document.getElementById(steps[currentStep]).classList.add('active');
                document.getElementById('loading-text').textContent = texts[currentStep];
                currentStep++;

                // 每個步驟間隔1-3秒
                const delay = Math.random() * 2000 + 1000;
                setTimeout(activateStep, delay);
            }
        }

        activateStep();
    }

    function resetLoadingSteps() {
        const steps = ['step1', 'step2', 'step3', 'step4'];
        steps.forEach(stepId => {
            const step = document.getElementById(stepId);
            step.classList.remove('active', 'completed');
        });
        document.getElementById('loading-text').textContent = '正在分析您的問題並搜尋相關財報數據';
    }

    function startNewChat() {
        currentConversationId = null;
        document.getElementById('chat-container').innerHTML = `
                <div class="welcome-message" id="welcome-message">
                    <i class="bi bi-robot" style="font-size: 4rem; color: var(--primary-color); margin-bottom: 20px;"></i>
                    <h2>開始新對話</h2>
                    <p style="color: #8e8ea0;">有什麼財務問題想要了解的嗎？</p>
                </div>
            `;

        // 顯示預設問題
        document.getElementById('preset-questions').style.display = 'flex';

        // 移除活躍狀態
        document.querySelectorAll('.history-item').forEach(item => {
            item.classList.remove('active');
        });
    }

    function loadConversation(conversationId) {
        currentConversationId = conversationId;

        // 標記為活躍
        document.querySelectorAll('.history-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[data-conversation-id="${conversationId}"]`).classList.add('active');

        // 隱藏歡迎訊息和預設問題
        const welcomeMessage = document.getElementById('welcome-message');
        const presetQuestions = document.getElementById('preset-questions');
        if (welcomeMessage) welcomeMessage.style.display = 'none';
        if (presetQuestions) presetQuestions.style.display = 'none';

        // 載入對話內容
        fetch(`api_improved.php?action=get_conversation&id=${conversationId}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const chatContainer = document.getElementById('chat-container');
                    chatContainer.innerHTML = '';

                    // 顯示所有訊息
                    data.messages.forEach(msg => {
                        addMessage(msg.question, 'user');
                        addMessage(msg.answer, 'bot');
                    });
                }
            })
            .catch(err => console.error('載入對話錯誤:', err));
    }

    function askExample(question) {
        document.getElementById('question-input').value = question;
        document.getElementById('question-form').dispatchEvent(new Event('submit'));
    }

    function toggleSidebar() {
        document.querySelector('.sidebar').classList.toggle('show');
    }

    function editConversationTitle(conversationId, currentTitle) {
        // 防止事件冒泡
        event.stopPropagation();

        const newTitle = prompt('請輸入新的對話室名稱:', currentTitle);
        if (newTitle && newTitle !== currentTitle) {
            const formData = new FormData();
            formData.append('action', 'rename_conversation');
            formData.append('conversation_id', conversationId);
            formData.append('title', newTitle);

            fetch('api_improved.php', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // 更新UI中的標題
                        document.getElementById(`conv-title-${conversationId}`).textContent = newTitle;
                        alert('對話室名稱已更新');
                    } else {
                        alert('更新失敗，請稍後再試');
                    }
                })
                .catch(error => {
                    console.error('更新錯誤:', error);
                    alert('更新失敗，請稍後再試');
                });
        }
    }

    // Enter 鍵發送（Shift+Enter 換行）
    input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            document.getElementById('question-form').dispatchEvent(new Event('submit'));
        }
    });
    // 初始載入
    loadConversations();
    <?php endif; ?>
    </script>
</body>

</html>