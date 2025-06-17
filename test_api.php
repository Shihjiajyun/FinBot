<?php
// 測試API功能
require_once 'php/config.php';

echo "🧪 FinBot API 測試\n";
echo "==================\n\n";

try {
    // 測試資料庫連接
    echo "1. 測試資料庫連接...\n";
    $db = new Database();
    $pdo = $db->getConnection();
    echo "✅ 資料庫連接成功\n\n";

    // 測試資料表存在性
    echo "2. 檢查資料表...\n";
    $tables = ['users', 'conversations', 'questions', 'user_questions', 'filings'];
    foreach ($tables as $table) {
        $stmt = $pdo->query("SHOW TABLES LIKE '$table'");
        if ($stmt->rowCount() > 0) {
            echo "✅ 資料表 '$table' 存在\n";
        } else {
            echo "❌ 資料表 '$table' 不存在\n";
        }
    }
    echo "\n";

    // 測試財報數據
    echo "3. 檢查財報數據...\n";
    $stmt = $pdo->query("SELECT COUNT(*) as count FROM filings");
    $filing_count = $stmt->fetch()['count'];
    echo "📊 財報文件總數: $filing_count\n";

    $stmt = $pdo->query("SELECT filing_type, COUNT(*) as count FROM filings GROUP BY filing_type");
    $filing_types = $stmt->fetchAll();
    foreach ($filing_types as $type) {
        echo "   - {$type['filing_type']}: {$type['count']} 個文件\n";
    }
    echo "\n";

    // 測試AMZN數據
    echo "4. 檢查AMZN數據...\n";
    $stmt = $pdo->query("SELECT COUNT(*) as count FROM filings WHERE company_name LIKE '%AMAZON%'");
    $amzn_count = $stmt->fetch()['count'];
    echo "🏢 AMAZON 相關文件: $amzn_count 個\n";

    if ($amzn_count > 0) {
        $stmt = $pdo->query("SELECT filing_type, COUNT(*) as count FROM filings WHERE company_name LIKE '%AMAZON%' GROUP BY filing_type");
        $amzn_types = $stmt->fetchAll();
        foreach ($amzn_types as $type) {
            echo "   - {$type['filing_type']}: {$type['count']} 個文件\n";
        }
    }
    echo "\n";

    // 測試OpenAI API Key
    echo "5. 檢查OpenAI API配置...\n";
    if (defined('OPENAI_API_KEY') && OPENAI_API_KEY !== 'your-openai-api-key-here') {
        echo "✅ OpenAI API Key 已配置\n";
        echo "🔑 API Key: " . substr(OPENAI_API_KEY, 0, 10) . "...\n";
    } else {
        echo "❌ OpenAI API Key 未正確配置\n";
    }
    echo "\n";

    // 測試用戶數據
    echo "6. 檢查用戶數據...\n";
    $stmt = $pdo->query("SELECT COUNT(*) as count FROM users");
    $user_count = $stmt->fetch()['count'];
    echo "👥 用戶總數: $user_count\n";

    if ($user_count > 0) {
        $stmt = $pdo->query("SELECT username FROM users LIMIT 3");
        $users = $stmt->fetchAll();
        echo "   測試用戶: ";
        foreach ($users as $user) {
            echo $user['username'] . " ";
        }
        echo "\n";
    }
    echo "\n";

    echo "🎉 測試完成！\n";
    echo "==================\n";
    echo "系統狀態總結:\n";
    echo "- 資料庫: ✅ 正常\n";
    echo "- 財報數據: ✅ $filing_count 個文件\n";
    echo "- AMZN數據: ✅ $amzn_count 個文件\n";
    echo "- API配置: " . (defined('OPENAI_API_KEY') && OPENAI_API_KEY !== 'your-openai-api-key-here' ? '✅ 正常' : '❌ 需要配置') . "\n";
    echo "- 用戶數據: ✅ $user_count 個用戶\n";
} catch (Exception $e) {
    echo "❌ 測試失敗: " . $e->getMessage() . "\n";
}
