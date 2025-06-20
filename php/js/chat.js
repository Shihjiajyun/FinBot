// 聊天相關函數
let currentConversationId = null;

// 初始化 Markdown 渲染器
const md = window.markdownit({
    html: true,
    linkify: true,
    typographer: true
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
function initQuestionForm() {
    document.getElementById('question-form').addEventListener('submit', function(e) {
        e.preventDefault();

        const input = document.getElementById('question-input');
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

                    // 準備回答內容
                    let botResponse = data.answer;

                    // 如果是歷史記錄，顯示特殊標識
                    if (data.from_history) {
                        console.log('回答來自歷史記錄');
                    }

                    // 如果有自動下載處理，顯示額外信息
                    if (data.missing_data_processed) {
                        botResponse = "📥 **系統已自動為您獲取最新財報數據**\n\n" + botResponse;
                        console.log('自動下載並處理了缺失的財報數據');
                    }

                    addMessage(botResponse, 'bot');

                    // 記錄調試信息
                    if (data.gpt_logs && data.gpt_logs.download_process) {
                        console.log('下載處理過程:', data.gpt_logs.download_process);
                    }

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
}

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
        '正在分析問題類型和所需財報...',
        '正在檢查財報數據完整性...',
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

    // 隱藏股票查詢界面
    document.getElementById('stock-query-container').style.display = 'none';

    // 顯示聊天界面和輸入區域
    document.getElementById('chat-container').style.display = 'flex';
    document.getElementById('input-area').style.display = 'block';

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

    // 隱藏股票查詢界面，顯示聊天界面
    document.getElementById('stock-query-container').style.display = 'none';
    document.getElementById('chat-container').style.display = 'flex';
    document.getElementById('input-area').style.display = 'block';

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

// UI相關函數
function toggleSidebar() {
    document.querySelector('.sidebar').classList.toggle('show');
}

// 自動調整輸入框高度
function initInputArea() {
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

    // Enter 鍵發送（Shift+Enter 換行）
    input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            document.getElementById('question-form').dispatchEvent(new Event('submit'));
        }
    });
}

// 初始化聊天功能
function initChat() {
    loadConversations();
    initQuestionForm();
    initInputArea();
} 