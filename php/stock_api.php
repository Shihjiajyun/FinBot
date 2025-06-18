<?php
require_once 'config.php';

header('Content-Type: application/json');

// 檢查登入狀態
if (!isset($_SESSION['user_id'])) {
    echo json_encode(['success' => false, 'error' => '請先登入']);
    exit;
}

// 處理股票資訊查詢
if ($_POST['action'] ?? '' === 'get_stock_info') {
    $ticker = strtoupper(trim($_POST['ticker'] ?? ''));

    if (empty($ticker)) {
        echo json_encode(['success' => false, 'error' => '股票代號不能為空']);
        exit;
    }

    // 驗證股票代號格式（只允許字母和數字）
    if (!preg_match('/^[A-Z0-9]{1,10}$/', $ticker)) {
        echo json_encode(['success' => false, 'error' => '股票代號格式錯誤']);
        exit;
    }

    try {
        // 獲取Python腳本的路徑
        $python_script = dirname(__DIR__) . '/stock_info.py';

        // 檢查Python腳本是否存在
        if (!file_exists($python_script)) {
            echo json_encode(['success' => false, 'error' => 'Python腳本未找到']);
            exit;
        }

        // 執行Python腳本獲取股票資訊
        $python_cmd = PYTHON_COMMAND;
        $command = "\"$python_cmd\" \"$python_script\" \"$ticker\" 2>&1";
        $output = shell_exec($command);

        if ($output === null || empty(trim($output))) {
            // 記錄詳細錯誤信息用於調試
            error_log("Python執行失敗 - 命令: $command");
            error_log("Python路徑: $python_cmd");
            error_log("腳本路徑: $python_script");

            echo json_encode([
                'success' => false,
                'error' => '無法執行Python腳本',
                'debug_info' => "使用的Python命令: $python_cmd"
            ]);
            exit;
        }

        // 解析Python腳本的輸出
        $result = json_decode($output, true);

        if (json_last_error() !== JSON_ERROR_NONE) {
            // 如果JSON解析失敗，記錄原始輸出用於調試
            error_log("Python輸出: " . $output);
            echo json_encode(['success' => false, 'error' => 'Python腳本輸出格式錯誤']);
            exit;
        }

        if (!$result['success']) {
            echo json_encode(['success' => false, 'error' => $result['error']]);
            exit;
        }

        echo json_encode([
            'success' => true,
            'stock_info' => $result['data']
        ]);
    } catch (Exception $e) {
        error_log("股票查詢錯誤: " . $e->getMessage());
        echo json_encode(['success' => false, 'error' => '系統錯誤，請稍後再試']);
    }

    exit;
}

// 獲取股票查詢歷史
if ($_GET['action'] ?? '' === 'get_stock_history') {
    try {
        $db = new Database();
        $pdo = $db->getConnection();

        $stmt = $pdo->prepare("
            SELECT ticker, query_time, result_data 
            FROM stock_queries 
            WHERE user_id = ? 
            ORDER BY query_time DESC 
            LIMIT 20
        ");
        $stmt->execute([$_SESSION['user_id']]);
        $history = $stmt->fetchAll();

        echo json_encode([
            'success' => true,
            'history' => $history
        ]);
    } catch (Exception $e) {
        error_log("獲取股票歷史錯誤: " . $e->getMessage());
        echo json_encode(['success' => false, 'error' => '獲取歷史記錄失敗']);
    }

    exit;
}

// 獲取熱門股票列表
if ($_GET['action'] ?? '' === 'get_popular_stocks') {
    try {
        $popular_stocks = [
            ['symbol' => 'AAPL', 'name' => 'Apple Inc.', 'category' => '科技'],
            ['symbol' => 'MSFT', 'name' => 'Microsoft Corporation', 'category' => '科技'],
            ['symbol' => 'GOOGL', 'name' => 'Alphabet Inc.', 'category' => '科技'],
            ['symbol' => 'AMZN', 'name' => 'Amazon.com Inc.', 'category' => '科技'],
            ['symbol' => 'TSLA', 'name' => 'Tesla Inc.', 'category' => '科技'],
            ['symbol' => 'META', 'name' => 'Meta Platforms Inc.', 'category' => '科技'],
            ['symbol' => 'NVDA', 'name' => 'NVIDIA Corporation', 'category' => '科技'],
            ['symbol' => 'NFLX', 'name' => 'Netflix Inc.', 'category' => '科技'],
            ['symbol' => 'JPM', 'name' => 'JPMorgan Chase & Co.', 'category' => '金融'],
            ['symbol' => 'V', 'name' => 'Visa Inc.', 'category' => '金融'],
            ['symbol' => 'JNJ', 'name' => 'Johnson & Johnson', 'category' => '醫療'],
            ['symbol' => 'KO', 'name' => 'Coca-Cola Company', 'category' => '消費'],
        ];

        echo json_encode([
            'success' => true,
            'stocks' => $popular_stocks
        ]);
    } catch (Exception $e) {
        echo json_encode(['success' => false, 'error' => '獲取熱門股票失敗']);
    }

    exit;
}

echo json_encode(['success' => false, 'error' => '未知的操作']);
