<!DOCTYPE html>
<html lang="zh-TW">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FinBot API 調試</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
        }

        .test-section {
            margin: 20px 0;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }

        .success {
            color: green;
        }

        .error {
            color: red;
        }

        .info {
            color: blue;
        }

        button {
            padding: 10px 15px;
            margin: 5px;
            cursor: pointer;
        }

        textarea {
            width: 100%;
            height: 100px;
            margin: 10px 0;
        }

        .result {
            background: #f5f5f5;
            padding: 10px;
            margin: 10px 0;
            border-radius: 3px;
        }
    </style>
</head>

<body>
    <h1>🧪 FinBot API 調試工具</h1>

    <div class="test-section">
        <h3>1. 測試登入狀態</h3>
        <button onclick="testLogin()">檢查登入狀態</button>
        <div id="login-result" class="result"></div>
    </div>

    <div class="test-section">
        <h3>2. 測試問答功能</h3>
        <textarea id="test-question" placeholder="輸入測試問題，例如：[AMZN] 最近有哪些內部人交易？">[AMZN] 最近有哪些內部人交易？</textarea>
        <br>
        <button onclick="testAsk()">發送問題</button>
        <div id="ask-result" class="result"></div>
    </div>

    <div class="test-section">
        <h3>3. 測試對話歷史</h3>
        <button onclick="testConversations()">載入對話歷史</button>
        <div id="conversations-result" class="result"></div>
    </div>

    <script>
        function testLogin() {
            const resultDiv = document.getElementById('login-result');
            resultDiv.innerHTML = '檢查中...';

            fetch('php/api_improved.php?action=stats')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        resultDiv.innerHTML = `<span class="success">✅ 登入狀態正常</span><br>
                                             統計資料: ${JSON.stringify(data, null, 2)}`;
                    } else {
                        resultDiv.innerHTML = `<span class="error">❌ ${data.error}</span>`;
                    }
                })
                .catch(error => {
                    resultDiv.innerHTML = `<span class="error">❌ 網路錯誤: ${error}</span>`;
                });
        }

        function testAsk() {
            const question = document.getElementById('test-question').value;
            const resultDiv = document.getElementById('ask-result');

            if (!question.trim()) {
                resultDiv.innerHTML = '<span class="error">❌ 請輸入問題</span>';
                return;
            }

            resultDiv.innerHTML = '處理中...';

            const formData = new FormData();
            formData.append('action', 'ask');
            formData.append('question', question);

            fetch('php/api_improved.php', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        resultDiv.innerHTML = `
                        <span class="success">✅ 問答成功</span><br>
                        <strong>問題:</strong> ${question}<br>
                        <strong>回答:</strong> ${data.answer}<br>
                        <strong>對話ID:</strong> ${data.conversation_id}<br>
                        <strong>數據分析:</strong> <pre>${JSON.stringify(data.data_analysis, null, 2)}</pre>
                        <strong>使用數據:</strong> <pre>${JSON.stringify(data.filing_data_summary, null, 2)}</pre>
                    `;
                    } else {
                        resultDiv.innerHTML = `<span class="error">❌ ${data.error}</span>`;
                    }
                })
                .catch(error => {
                    resultDiv.innerHTML = `<span class="error">❌ 網路錯誤: ${error}</span>`;
                });
        }

        function testConversations() {
            const resultDiv = document.getElementById('conversations-result');
            resultDiv.innerHTML = '載入中...';

            fetch('php/api_improved.php?action=get_conversations')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        resultDiv.innerHTML = `
                            <span class="success">✅ 對話歷史載入成功</span><br>
                            <strong>對話數量:</strong> ${data.conversations.length}<br>
                            <strong>對話列表:</strong> <pre>${JSON.stringify(data.conversations, null, 2)}</pre>
                        `;
                    } else {
                        resultDiv.innerHTML = `<span class="error">❌ ${data.error}</span>`;
                    }
                })
                .catch(error => {
                    resultDiv.innerHTML = `<span class="error">❌ 網路錯誤: ${error}</span>`;
                });
        }

        // 頁面載入時自動測試登入狀態
        window.onload = function() {
            testLogin();
        };
    </script>
</body>

</html>