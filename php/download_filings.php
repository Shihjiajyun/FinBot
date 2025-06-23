<?php
// 增加執行時間限制，因為下載財報檔案可能需要較長時間
set_time_limit(1800); // 30分鐘
ini_set('max_execution_time', 1800);

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
                // 從檔案名提取年份 (例如: 0001326801-21-000014.txt -> 2021)
                if (preg_match('/(\d{2})-\d{6}\.txt$/', $filename, $matches)) {
                    $shortYear = intval($matches[1]);
                    $fullYear = $shortYear >= 90 ? 1900 + $shortYear : 2000 + $shortYear;
                    $existingFiles[$fullYear] = $filename;
                } else if (preg_match('/(\d{4})/', $filename, $matches)) {
                    // 備用邏輯：尋找四位數年份
                    $year = $matches[1];
                    $existingFiles[$year] = $filename;
                }
            }
        }

        // 啟動 Python 下載腳本
        $pythonScript = __DIR__ . '/../download_single_stock.py';
        $pythonCommand = PYTHON_COMMAND;  // 使用配置的 Python 命令
        $workingDir = dirname(__DIR__);  // 設定工作目錄為 FinBot/ 而不是 FinBot/php/

        // 設定環境變數避免 Unicode 錯誤
        $env_vars = '';
        if (PHP_OS_FAMILY === 'Windows') {
            $env_vars = 'set PYTHONIOENCODING=utf-8 && ';
        }

        // 改變到正確的工作目錄後執行Python腳本
        $command = $env_vars . "cd \"{$workingDir}\" && \"{$pythonCommand}\" \"{$pythonScript}\" {$ticker} 2>&1";

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
                // 從檔案名提取年份 (例如: 0001326801-21-000014.txt -> 2021)
                if (preg_match('/(\d{2})-\d{6}\.txt$/', $filename, $matches)) {
                    $shortYear = intval($matches[1]);
                    $fullYear = $shortYear >= 90 ? 1900 + $shortYear : 2000 + $shortYear;
                    $newFiles[$fullYear] = $filename;
                } else if (preg_match('/(\d{4})/', $filename, $matches)) {
                    // 備用邏輯：尋找四位數年份
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

        // 添加調試信息
        $debugInfo = [
            'ticker' => $ticker,
            'current_dir' => __DIR__,
            'downloads_path' => $downloadPath,
            'downloads_path_exists' => is_dir($downloadPath),
            'parent_dir' => dirname(__DIR__),
            'downloads_base' => dirname(__DIR__) . '/downloads',
            'downloads_base_exists' => is_dir(dirname(__DIR__) . '/downloads'),
            'ticker_dir' => dirname(__DIR__) . '/downloads/' . $ticker,
            'ticker_dir_exists' => is_dir(dirname(__DIR__) . '/downloads/' . $ticker)
        ];

        if (is_dir($downloadPath)) {
            $fileList = glob($downloadPath . "/*.txt");
            $debugInfo['glob_pattern'] = $downloadPath . "/*.txt";
            $debugInfo['glob_result'] = $fileList;

            foreach ($fileList as $file) {
                $filename = basename($file);
                $size = filesize($file);
                $modified = filemtime($file);

                // 從檔案名提取年份 (例如: 0001326801-21-000014.txt -> 2021)
                if (preg_match('/(\d{2})-\d{6}\.txt$/', $filename, $matches)) {
                    $shortYear = intval($matches[1]);
                    $fullYear = $shortYear >= 90 ? 1900 + $shortYear : 2000 + $shortYear;
                    $files[$fullYear] = [
                        'filename' => $filename,
                        'size' => $size,
                        'modified' => date('Y-m-d H:i:s', $modified),
                        'year' => $fullYear
                    ];
                } else if (preg_match('/(\d{4})/', $filename, $matches)) {
                    // 備用邏輯：尋找四位數年份
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
            'total_files' => count($files),
            'debug_info' => $debugInfo
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
