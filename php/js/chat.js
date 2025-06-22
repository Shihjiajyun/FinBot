// 聊天相關函數
let currentConversationId = null;

// 初始化 Markdown 渲染器
const md = window.markdownit({
    html: true,
    linkify: true,
    typographer: true
});

// 載入股票查詢歷史（替代對話歷史）
function loadConversations() {
    // 直接載入股票歷史，不再載入對話歷史
    if (typeof loadStockHistory === 'function') {
        loadStockHistory();
    } else {
        // 如果loadStockHistory函數還沒載入，顯示提示
        const historyContainer = document.getElementById('chat-history');
        if (historyContainer) {
            historyContainer.innerHTML = `
                <div class="text-center" style="color: #8e8ea0; padding: 20px; font-size: 14px;">
                    暫無股票查詢記錄<br>
                    <small style="font-size: 12px;">點擊「股票查詢」開始查詢</small>
                </div>
            `;
        }
    }
}

// 快速跳轉到輸入區域
function scrollToInput() {
    const inputArea = document.getElementById('input-area');
    if (inputArea) {
        inputArea.scrollIntoView({ behavior: 'smooth', block: 'end' });
        
        // 聚焦到輸入框
        setTimeout(() => {
            const questionInput = document.getElementById('question-input');
            if (questionInput) {
                questionInput.focus();
            }
        }, 500);
    }
}

// 監控聊天容器滾動，控制快速跳轉按鈕顯示
function initScrollMonitoring() {
    const chatContainer = document.getElementById('chat-container');
    const quickJumpBtn = document.getElementById('quick-jump-btn');
    
    if (chatContainer && quickJumpBtn) {
        chatContainer.addEventListener('scroll', function() {
            const scrollTop = this.scrollTop;
            const scrollHeight = this.scrollHeight;
            const clientHeight = this.clientHeight;
            
            // 如果滾動超過一定距離，顯示快速跳轉按鈕
            if (scrollHeight - scrollTop - clientHeight > 200) {
                quickJumpBtn.classList.add('show');
            } else {
                quickJumpBtn.classList.remove('show');
            }
        });
    }
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

// 開始新對話 - 重新設計為開始新的聊天會話
function startNewChat() {
    currentConversationId = null;
    
    // 清空聊天容器
    const chatContainer = document.getElementById('chat-container');
    if (chatContainer) {
        chatContainer.innerHTML = `
            <!-- 快速跳轉按鈕 -->
            <button class="quick-jump-btn" id="quick-jump-btn" onclick="scrollToInput()">
                <i class="bi bi-arrow-down"></i>
                快速提問
            </button>
            
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
        `;
    }
    
    // 顯示聊天界面
    document.getElementById('chat-container').style.display = 'flex';
    document.getElementById('input-area').style.display = 'block';
    document.getElementById('preset-questions').style.display = 'flex';
    
    // 隱藏股票查詢界面
    document.getElementById('stock-query-container').style.display = 'none';
    
    // 移除歷史記錄的活躍狀態
    document.querySelectorAll('.history-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // 重新初始化滾動監控
    initScrollMonitoring();
}

// 載入對話
function loadConversation(conversationId) {
    currentConversationId = conversationId;

    fetch('api_improved.php', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `action=get_conversation&conversation_id=${conversationId}`
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // 顯示聊天界面
                document.getElementById('chat-container').style.display = 'flex';
                document.getElementById('input-area').style.display = 'block';
                document.getElementById('preset-questions').style.display = 'none';
                
                // 隱藏股票查詢界面和歡迎訊息
                document.getElementById('stock-query-container').style.display = 'none';
                document.getElementById('welcome-message').style.display = 'none';

                // 清空並重新填充聊天容器
                const chatContainer = document.getElementById('chat-container');
                chatContainer.innerHTML = `
                    <button class="quick-jump-btn" id="quick-jump-btn" onclick="scrollToInput()">
                        <i class="bi bi-arrow-down"></i>
                        快速提問
                    </button>
                `;

                // 載入對話內容
                data.messages.forEach(message => {
                    addMessage(message.content, message.role);
                });
                
                // 重新初始化滾動監控
                initScrollMonitoring();
            }
        })
        .catch(error => {
            console.error('載入對話錯誤:', error);
        });
}

function askExample(question) {
    const input = document.getElementById('question-input');
    input.value = question;
    document.getElementById('question-form').dispatchEvent(new Event('submit'));
}

function editConversationTitle(conversationId, currentTitle) {
    const newTitle = prompt('修改對話標題:', currentTitle);
    if (newTitle && newTitle !== currentTitle) {
        fetch('api_improved.php', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `action=update_conversation_title&conversation_id=${conversationId}&title=${encodeURIComponent(newTitle)}`
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    loadConversations();
                }
            })
            .catch(error => {
                console.error('更新標題錯誤:', error);
            });
    }
}

function toggleSidebar() {
    document.querySelector('.sidebar').classList.toggle('show');
}

function initInputArea() {
    const textarea = document.getElementById('question-input');
    if (textarea) {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = this.scrollHeight + 'px';
        });

        textarea.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                document.getElementById('question-form').dispatchEvent(new Event('submit'));
            }
        });
    }
}

// 修正時間顯示 - 加8小時
function formatTimeWithOffset(timestamp) {
    const date = new Date(timestamp);
    date.setHours(date.getHours() + 8); // 加8小時修正時區
    
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return '剛剛';
    if (diffMins < 60) return `${diffMins} 分鐘前`;
    if (diffHours < 24) return `${diffHours} 小時前`;
    if (diffDays < 7) return `${diffDays} 天前`;
    
    return date.toLocaleDateString('zh-TW');
}

function initChat() {
    loadConversations();
    initQuestionForm();
    initInputArea();
    initScrollMonitoring();
} 