<?php
session_start();

// 模擬登入狀態
$_SESSION['user_id'] = 1;

// 設置錯誤報告
error_reporting(E_ALL);
ini_set('display_errors', 1);

// 設置日誌文件
ini_set('log_errors', 1);
ini_set('error_log', 'improved_system.log');

echo "<h1>改進後的GPT通信系統測試</h1>";

// 測試問題
$test_questions = [
    '[AMZN] 2024年的營運重點是什麼？',
    '[AMZN] 2023年的業務描述和風險因素有哪些？',
    '[AMZN] 最近的內部人交易情況如何？'
];

foreach ($test_questions as $index => $question) {
    echo "<h2>測試 " . ($index + 1) . ": {$question}</h2>";

    // 模擬POST請求
    $_POST['action'] = 'ask';
    $_POST['question'] = $question;

    echo "<p>開始處理請求...</p>";

    try {
        // 包含API文件
        ob_start();
        require_once 'php/api_improved.php';
        $output = ob_get_clean();

        // 解析JSON回應
        $response = json_decode($output, true);

        if ($response && $response['success']) {
            echo "<div style='background: #2a2a2a; padding: 15px; border-radius: 8px; margin: 10px 0;'>";
            echo "<h3>✅ 測試成功</h3>";
            echo "<p><strong>答案長度:</strong> " . strlen($response['answer']) . " 字符</p>";

            if (isset($response['gpt_logs'])) {
                echo "<h4>GPT通信日誌:</h4>";
                echo "<pre style='background: #1a1a1a; padding: 10px; border-radius: 4px; overflow-x: auto;'>";
                echo json_encode($response['gpt_logs'], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
                echo "</pre>";
            }

            if (isset($response['filing_data_summary'])) {
                echo "<h4>使用的財報數據:</h4>";
                echo "<pre style='background: #1a1a1a; padding: 10px; border-radius: 4px;'>";
                echo json_encode($response['filing_data_summary'], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
                echo "</pre>";
            }
            echo "</div>";
        } else {
            echo "<div style='background: #ff4444; padding: 15px; border-radius: 8px; margin: 10px 0;'>";
            echo "<h3>❌ 測試失敗</h3>";
            echo "<p>錯誤: " . ($response['error'] ?? '未知錯誤') . "</p>";
            echo "</div>";
        }
    } catch (Exception $e) {
        echo "<div style='background: #ff4444; padding: 15px; border-radius: 8px; margin: 10px 0;'>";
        echo "<h3>❌ 系統錯誤</h3>";
        echo "<p>錯誤: " . $e->getMessage() . "</p>";
        echo "</div>";
    }

    echo "<hr>";

    // 清理POST數據
    unset($_POST['question']);
}

echo "<h2>測試完成</h2>";
echo "<p>詳細日誌請查看 improved_system.log 文件</p>";
?>

<style>
    body {
        font-family: Arial, sans-serif;
        background: #1a1a1a;
        color: white;
        padding: 20px;
        line-height: 1.6;
    }

    h1,
    h2,
    h3,
    h4 {
        color: #4a9eff;
    }

    pre {
        font-size: 12px;
        max-height: 400px;
        overflow-y: auto;
    }

    hr {
        border: 1px solid #333;
        margin: 30px 0;
    }
</style>