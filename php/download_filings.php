<?php
require_once 'config.php';

header('Content-Type: application/json');

// 檢查登入狀態
if (!isset($_SESSION['user_id'])) {
    echo json_encode(['success' => false, 'error' => '未登入']);
    exit;
}

$action = $_POST['action'] ?? '';

if ($action === 'download_10k_filings') {
    $ticker = strtoupper(trim($_POST['ticker'] ?? ''));

    if (empty($ticker)) {
        echo json_encode(['success' => false, 'error' => '股票代號不能為空']);
        exit;
    }

    try {
        // 檢查是否已有下載的檔案
        $downloadPath = __DIR__ . "/../downloads/{$ticker}/10-K";
        $existingFiles = [];

        if (is_dir($downloadPath)) {
            $files = glob($downloadPath . "/*.txt");
            foreach ($files as $file) {
                $filename = basename($file);
                // 從檔案名提取年份
                if (preg_match('/(\d{4})/', $filename, $matches)) {
                    $year = $matches[1];
                    $existingFiles[$year] = $filename;
                }
            }
        }

        // 啟動 Python 下載腳本
        $pythonScript = __DIR__ . '/../download_single_stock.py';
        $pythonCommand = PYTHON_COMMAND;  // 使用配置的 Python 命令

        // 設定環境變數避免 Unicode 錯誤
        $env_vars = '';
        if (PHP_OS_FAMILY === 'Windows') {
            $env_vars = 'set PYTHONIOENCODING=utf-8 && ';
        }

        $command = $env_vars . "\"{$pythonCommand}\" \"{$pythonScript}\" {$ticker} 2>&1";

        $output = [];
        $returnCode = 0;
        exec($command, $output, $returnCode);

        if ($returnCode !== 0) {
            error_log("Python下載腳本執行失敗，返回碼: $returnCode");
            error_log("輸出內容: " . implode('\n', $output));
            echo json_encode([
                'success' => false,
                'error' => '下載失敗，詳細錯誤: ' . implode('\n', $output)
            ]);
            exit;
        }

        // 重新檢查下載後的檔案
        $newFiles = [];
        if (is_dir($downloadPath)) {
            $files = glob($downloadPath . "/*.txt");
            foreach ($files as $file) {
                $filename = basename($file);
                if (preg_match('/(\d{4})/', $filename, $matches)) {
                    $year = $matches[1];
                    $newFiles[$year] = $filename;
                }
            }
        }

        echo json_encode([
            'success' => true,
            'message' => '下載完成',
            'existing_files' => $existingFiles,
            'new_files' => $newFiles,
            'download_output' => implode('\n', $output)
        ]);
    } catch (Exception $e) {
        echo json_encode([
            'success' => false,
            'error' => '下載過程中發生錯誤: ' . $e->getMessage()
        ]);
    }
} else if ($action === 'check_download_status') {
    $ticker = strtoupper(trim($_POST['ticker'] ?? ''));

    if (empty($ticker)) {
        echo json_encode(['success' => false, 'error' => '股票代號不能為空']);
        exit;
    }

    try {
        $downloadPath = __DIR__ . "/../downloads/{$ticker}/10-K";
        $files = [];

        if (is_dir($downloadPath)) {
            $fileList = glob($downloadPath . "/*.txt");
            foreach ($fileList as $file) {
                $filename = basename($file);
                $size = filesize($file);
                $modified = filemtime($file);

                // 從檔案名提取年份
                if (preg_match('/(\d{4})/', $filename, $matches)) {
                    $year = $matches[1];
                    $files[$year] = [
                        'filename' => $filename,
                        'size' => $size,
                        'modified' => date('Y-m-d H:i:s', $modified),
                        'year' => $year
                    ];
                }
            }
        }

        echo json_encode([
            'success' => true,
            'files' => $files,
            'total_files' => count($files)
        ]);
    } catch (Exception $e) {
        echo json_encode([
            'success' => false,
            'error' => '檢查檔案狀態時發生錯誤: ' . $e->getMessage()
        ]);
    }
} else {
    echo json_encode(['success' => false, 'error' => '無效的操作']);
}
