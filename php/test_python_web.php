<?php
// 測試Python在Web環境下的執行
header('Content-Type: text/html; charset=utf-8');
?>
<!DOCTYPE html>
<html>

<head>
    <title>Python Web Environment Test</title>
    <style>
        body {
            font-family: monospace;
            background: #000;
            color: #0f0;
            padding: 20px;
        }

        .success {
            color: #0f0;
        }

        .error {
            color: #f00;
        }

        .info {
            color: #ff0;
        }

        pre {
            background: #111;
            padding: 10px;
            border: 1px solid #333;
        }
    </style>
</head>

<body>
    <h1>🐍 Python Web Environment Test</h1>

    <?php
    echo "<div class='info'>當前工作目錄: " . getcwd() . "</div><br>";
    echo "<div class='info'>FinBot目錄: " . dirname(__DIR__) . "</div><br>";

    // Python路徑列表
    $python_paths = [
        'C:\\Users\\shihj\\anaconda3\\python.exe',
        'python',
        'python3',
        'C:\\Python39\\python.exe',
        'C:\\Python38\\python.exe',
        'C:\\Python37\\python.exe'
    ];

    $current_dir = dirname(__DIR__);
    $script_path = $current_dir . DIRECTORY_SEPARATOR . 'test_basic.py';

    echo "<div class='info'>測試腳本路徑: {$script_path}</div><br>";
    echo "<div class='info'>腳本是否存在: " . (file_exists($script_path) ? '✅ 是' : '❌ 否') . "</div><br>";

    foreach ($python_paths as $i => $python_path) {
        echo "<h3>測試 " . ($i + 1) . ": {$python_path}</h3>";

        $command = "\"{$python_path}\" \"{$script_path}\"";
        echo "<div class='info'>命令: {$command}</div>";

        // 切換工作目錄
        $old_cwd = getcwd();
        chdir($current_dir);

        $output = [];
        $return_code = 0;

        $start_time = microtime(true);
        exec($command . ' 2>&1', $output, $return_code);
        $end_time = microtime(true);
        $duration = round(($end_time - $start_time) * 1000, 2);

        // 恢復工作目錄
        chdir($old_cwd);

        echo "<div>執行時間: {$duration}ms</div>";
        echo "<div>返回碼: {$return_code}</div>";

        if ($return_code === 0) {
            echo "<div class='success'>✅ 成功!</div>";
            echo "<pre>" . htmlspecialchars(implode("\n", $output)) . "</pre>";
            echo "<div class='success'>🎉 找到可用的Python: {$python_path}</div>";
            break;
        } else {
            echo "<div class='error'>❌ 失敗 (返回碼: {$return_code})</div>";
            if (!empty($output)) {
                echo "<pre>" . htmlspecialchars(implode("\n", $output)) . "</pre>";
            }
        }
        echo "<hr>";
    }

    // 測試PATH環境變量
    echo "<h3>PATH環境變量:</h3>";
    $path = getenv('PATH');
    if ($path) {
        $path_dirs = explode(PATH_SEPARATOR, $path);
        echo "<ul>";
        foreach ($path_dirs as $dir) {
            echo "<li>" . htmlspecialchars($dir) . "</li>";
        }
        echo "</ul>";
    } else {
        echo "<div class='error'>無法獲取PATH環境變量</div>";
    }
    ?>

    <hr>
    <div class='info'>💡 如果測試失敗，請檢查:</div>
    <ul>
        <li>Python是否正確安裝</li>
        <li>PATH環境變量是否包含Python路徑</li>
        <li>Apache/PHP是否有執行權限</li>
        <li>腳本路徑是否正確</li>
    </ul>
</body>

</html>