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
                <button class="stock-query-btn" onclick="switchToStockQuery()">
                    <i class="bi bi-graph-up"></i>
                    股票查詢
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

            <!-- 股票查詢界面 -->
            <div class="stock-query-container" id="stock-query-container" style="display: none;">
                <div class="stock-query-header">
                    <h2><i class="bi bi-graph-up"></i> 股票資訊查詢</h2>
                    <p style="color: #8e8ea0;">輸入股票代號，獲取詳細的財務資訊</p>
                </div>

                <div class="stock-search-area">
                    <div class="search-form">
                        <input type="text" id="stock-ticker-input" placeholder="請輸入股票代號 (例如: AAPL, TSLA, MSFT)"
                            class="stock-input">
                        <button id="search-stock-btn" onclick="searchStock()">
                            <i class="bi bi-search"></i> 查詢
                        </button>
                    </div>

                    <div class="popular-stocks">
                        <h5 style="color: #8e8ea0; margin-bottom: 15px;">熱門股票</h5>
                        <div class="stock-tags">
                            <span class="stock-tag" onclick="quickSearch('AAPL')">AAPL</span>
                            <span class="stock-tag" onclick="quickSearch('MSFT')">MSFT</span>
                            <span class="stock-tag" onclick="quickSearch('GOOGL')">GOOGL</span>
                            <span class="stock-tag" onclick="quickSearch('AMZN')">AMZN</span>
                            <span class="stock-tag" onclick="quickSearch('TSLA')">TSLA</span>
                            <span class="stock-tag" onclick="quickSearch('META')">META</span>
                            <span class="stock-tag" onclick="quickSearch('NVDA')">NVDA</span>
                            <span class="stock-tag" onclick="quickSearch('NFLX')">NFLX</span>
                        </div>
                    </div>
                </div>

                <div class="stock-result-area" id="stock-result-area" style="display: none;">
                    <!-- 股票資訊將在這裡顯示 -->
                </div>
            </div>

            <div class="input-area" id="input-area">
                <!-- 全屏Loading覆蓋層 -->
                <div class="fullscreen-loading" id="fullscreen-loading">
                    <div class="loading-overlay">
                        <div class="loading-content">
                            <div class="spinner-large"></div>
                            <h3>🤖 FinBot 正在分析中...</h3>
                            <p id="loading-text">正在分析您的問題並搜尋相關財報數據</p>
                            <div class="loading-steps">
                                <div class="step" id="step1">📋 分析問題類型</div>
                                <div class="step" id="step2">🔍 檢查財報數據</div>
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

    <?php if ($is_logged_in): ?>
        <!-- 引入分離的JavaScript檔案 -->
        <script src="js/financial-tables.js"></script>
        <script src="js/stock-query.js"></script>
        <script src="js/chat.js"></script>

        <script>
            // 頁面載入完成後初始化
            document.addEventListener('DOMContentLoaded', function() {
                initChat();
            });
        </script>
    <?php endif; ?>
</body>

</html>