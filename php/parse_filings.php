<?php
require_once 'config.php';

header('Content-Type: application/json');

// 檢查登入狀態
if (!isset($_SESSION['user_id'])) {
    echo json_encode(['success' => false, 'error' => '未登入']);
    exit;
}

$action = $_POST['action'] ?? '';

if ($action === 'parse_10k_filings') {
    $ticker = strtoupper(trim($_POST['ticker'] ?? ''));

    if (empty($ticker)) {
        echo json_encode(['success' => false, 'error' => '股票代號不能為空']);
        exit;
    }

    try {
        // 檢查下載目錄是否存在檔案
        $downloadPath = __DIR__ . "/../downloads/{$ticker}/10-K";

        if (!is_dir($downloadPath)) {
            echo json_encode([
                'success' => false,
                'error' => '找不到下載的財報檔案，請先下載財報'
            ]);
            exit;
        }

        $files = glob($downloadPath . "/*.txt");
        if (empty($files)) {
            echo json_encode([
                'success' => false,
                'error' => '下載目錄中沒有找到財報檔案'
            ]);
            exit;
        }

        // 創建修改版的解析腳本
        $parseScript = __DIR__ . "/../parse_single_stock.py";
        $command = "python \"{$parseScript}\" {$ticker} 2>&1";

        $output = [];
        $returnCode = 0;
        exec($command, $output, $returnCode);

        if ($returnCode !== 0) {
            echo json_encode([
                'success' => false,
                'error' => '解析失敗: ' . implode('\n', $output)
            ]);
            exit;
        }

        // 檢查數據庫中的解析結果
        $db = new Database();
        $pdo = $db->getConnection();

        $stmt = $pdo->prepare("
            SELECT COUNT(*) as count, 
                   MIN(report_date) as earliest_date,
                   MAX(report_date) as latest_date
            FROM ten_k_filings 
            WHERE company_name = ?
        ");
        $stmt->execute([$ticker]);
        $result = $stmt->fetch();

        echo json_encode([
            'success' => true,
            'message' => '解析完成',
            'parsed_files' => $result['count'],
            'date_range' => [
                'earliest' => $result['earliest_date'],
                'latest' => $result['latest_date']
            ],
            'parse_output' => implode('\n', $output)
        ]);
    } catch (Exception $e) {
        echo json_encode([
            'success' => false,
            'error' => '解析過程中發生錯誤: ' . $e->getMessage()
        ]);
    }
} else if ($action === 'check_parsed_filings') {
    $ticker = strtoupper(trim($_POST['ticker'] ?? ''));

    if (empty($ticker)) {
        echo json_encode(['success' => false, 'error' => '股票代號不能為空']);
        exit;
    }

    try {
        $db = new Database();
        $pdo = $db->getConnection();

        $stmt = $pdo->prepare("
            SELECT id, file_name, report_date, filed_date, created_at
            FROM ten_k_filings 
            WHERE company_name = ?
            ORDER BY report_date DESC
        ");
        $stmt->execute([$ticker]);
        $filings = $stmt->fetchAll();

        // 為每個財報檢查是否已有摘要
        $filingsWithSummary = [];
        foreach ($filings as $filing) {
            $summaryStmt = $pdo->prepare("
                SELECT id, processing_status, items_processed_count, summary_completed_at
                FROM ten_k_filings_summary 
                WHERE original_filing_id = ?
            ");
            $summaryStmt->execute([$filing['id']]);
            $summary = $summaryStmt->fetch();

            $filing['has_summary'] = $summary !== false;
            $filing['summary_status'] = $summary['processing_status'] ?? 'not_started';
            $filing['summary_items_count'] = $summary['items_processed_count'] ?? 0;
            $filing['summary_completed_at'] = $summary['summary_completed_at'] ?? null;

            // 從檔案名或報告日期中提取年份
            if ($filing['report_date']) {
                $filing['year'] = date('Y', strtotime($filing['report_date']));
            } else {
                preg_match('/(\d{4})/', $filing['file_name'], $matches);
                $filing['year'] = $matches[1] ?? 'Unknown';
            }

            $filingsWithSummary[] = $filing;
        }

        echo json_encode([
            'success' => true,
            'filings' => $filingsWithSummary,
            'total_filings' => count($filingsWithSummary)
        ]);
    } catch (Exception $e) {
        echo json_encode([
            'success' => false,
            'error' => '檢查解析狀態時發生錯誤: ' . $e->getMessage()
        ]);
    }
} else {
    echo json_encode(['success' => false, 'error' => '無效的操作']);
}
