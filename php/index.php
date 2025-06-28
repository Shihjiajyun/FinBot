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
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
    <link rel="stylesheet" href="css/index.css">
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
                <button class="stock-query-btn" onclick="switchToStockQuery()">
                    <i class="bi bi-graph-up"></i>
                    股票查詢
                </button>
            </div>

            <div class="chat-history" id="chat-history">
                <!-- 股票查詢歷史將由JavaScript載入 -->
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

            <!-- 股票查詢界面 -->
            <div class="stock-query-container" id="stock-query-container">
                <!-- 股票查詢頁面的快速跳轉按鈕 -->
                <button class="stock-quick-jump-btn" id="stock-quick-jump-btn" onclick="scrollToCurrentStockQA()">
                    <i class="bi bi-arrow-down"></i>
                    快速提問
                </button>

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
        </div>
    <?php endif; ?>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>

    <?php if ($is_logged_in): ?>
        <!-- 引入分離的JavaScript檔案 -->
        <!-- 表格處理 -->
        <script src="js/financial-tables.js"></script>

        <!-- 股票查詢 -->
        <script src="js/stock-query.js"></script>

        <!-- 對話功能 -->
        <script src="js/chat.js"></script>

        <script>
            // 頁面載入完成後初始化
            document.addEventListener('DOMContentLoaded', function() {
                // 直接切換到股票查詢
                switchToStockQuery();
                // 載入對話歷史（而不是股票查詢歷史）
                setTimeout(function() {
                    if (typeof loadConversationHistory === 'function') {
                        loadConversationHistory();
                    } else {
                        console.error('loadConversationHistory 函數未定義');
                        // 備用方案：載入舊的股票歷史
                        if (typeof loadStockHistory === 'function') {
                            loadStockHistory();
                        }
                    }
                }, 100);
            });

            // 監聽頁面可見性變化，當用戶從其他頁面返回時重新載入對話歷史
            document.addEventListener('visibilitychange', function() {
                if (!document.hidden && typeof loadConversationHistory === 'function') {
                    // 延遲一點再載入，確保頁面完全激活
                    setTimeout(function() {
                        loadConversationHistory();
                    }, 500);
                }
            });

            // 監聽窗口焦點變化
            window.addEventListener('focus', function() {
                if (typeof loadConversationHistory === 'function') {
                    setTimeout(function() {
                        loadConversationHistory();
                    }, 300);
                }
            });
        </script>
    <?php endif; ?>
</body>

</html>