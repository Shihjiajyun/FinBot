<?php
require_once 'config.php';

header('Content-Type: application/json');

// 檢查登入狀態
if (!isset($_SESSION['user_id'])) {
    echo json_encode(['success' => false, 'error' => '未登入']);
    exit;
}

$action = $_POST['action'] ?? '';

if ($action === 'summarize_filings') {
    $ticker = strtoupper(trim($_POST['ticker'] ?? ''));
    $filing_ids = $_POST['filing_ids'] ?? [];

    if (empty($ticker)) {
        echo json_encode(['success' => false, 'error' => '股票代號不能為空']);
        exit;
    }

    if (empty($filing_ids) || !is_array($filing_ids)) {
        echo json_encode(['success' => false, 'error' => '請選擇要摘要的財報']);
        exit;
    }

    try {
        // 檢查選中的財報是否存在
        $db = new Database();
        $pdo = $db->getConnection();

        $placeholders = str_repeat('?,', count($filing_ids) - 1) . '?';
        $stmt = $pdo->prepare("
            SELECT id, file_name, report_date, company_name
            FROM ten_k_filings 
            WHERE id IN ($placeholders) AND company_name = ?
        ");
        $stmt->execute(array_merge($filing_ids, [$ticker]));
        $filings = $stmt->fetchAll();

        if (count($filings) !== count($filing_ids)) {
            echo json_encode(['success' => false, 'error' => '部分財報不存在或不屬於該股票']);
            exit;
        }

        // 檢查是否已有摘要
        $existing_summaries = [];
        foreach ($filing_ids as $filing_id) {
            $summaryStmt = $pdo->prepare("
                SELECT id, processing_status, items_processed_count
                FROM ten_k_filings_summary 
                WHERE original_filing_id = ?
            ");
            $summaryStmt->execute([$filing_id]);
            $summary = $summaryStmt->fetch();

            if ($summary) {
                $existing_summaries[$filing_id] = $summary;
            }
        }

        // 創建專用的 Python 摘要腳本
        $summaryScript = __DIR__ . "/../summarize_single_stock.py";
        $filing_ids_str = implode(',', $filing_ids);
        $command = "python \"{$summaryScript}\" {$ticker} {$filing_ids_str} 2>&1";

        // 啟動背景進程進行摘要
        $output = [];
        $returnCode = 0;
        exec($command, $output, $returnCode);

        if ($returnCode !== 0) {
            echo json_encode([
                'success' => false,
                'error' => '摘要過程失敗: ' . implode('\n', $output)
            ]);
            exit;
        }

        // 檢查摘要結果
        $completed_summaries = [];
        foreach ($filing_ids as $filing_id) {
            $summaryStmt = $pdo->prepare("
                SELECT id, processing_status, items_processed_count, summary_completed_at
                FROM ten_k_filings_summary 
                WHERE original_filing_id = ?
            ");
            $summaryStmt->execute([$filing_id]);
            $summary = $summaryStmt->fetch();

            if ($summary) {
                $completed_summaries[$filing_id] = $summary;
            }
        }

        echo json_encode([
            'success' => true,
            'message' => '摘要完成',
            'existing_summaries' => $existing_summaries,
            'completed_summaries' => $completed_summaries,
            'summary_output' => implode('\n', $output)
        ]);
    } catch (Exception $e) {
        echo json_encode([
            'success' => false,
            'error' => '摘要過程中發生錯誤: ' . $e->getMessage()
        ]);
    }
} else if ($action === 'check_summary_status') {
    $ticker = strtoupper(trim($_POST['ticker'] ?? ''));
    $filing_ids = $_POST['filing_ids'] ?? [];

    if (empty($ticker) || empty($filing_ids)) {
        echo json_encode(['success' => false, 'error' => '參數不完整']);
        exit;
    }

    try {
        $db = new Database();
        $pdo = $db->getConnection();

        $summary_statuses = [];
        foreach ($filing_ids as $filing_id) {
            $stmt = $pdo->prepare("
                SELECT f.file_name, f.report_date, f.company_name,
                       s.id as summary_id, s.processing_status, s.items_processed_count,
                       s.total_items_count, s.summary_completed_at
                FROM ten_k_filings f
                LEFT JOIN ten_k_filings_summary s ON f.id = s.original_filing_id
                WHERE f.id = ? AND f.company_name = ?
            ");
            $stmt->execute([$filing_id, $ticker]);
            $result = $stmt->fetch();

            if ($result) {
                $year = $result['report_date'] ? date('Y', strtotime($result['report_date'])) : 'Unknown';

                $summary_statuses[$filing_id] = [
                    'file_name' => $result['file_name'],
                    'year' => $year,
                    'has_summary' => $result['summary_id'] !== null,
                    'status' => $result['processing_status'] ?? 'not_started',
                    'items_processed' => $result['items_processed_count'] ?? 0,
                    'total_items' => $result['total_items_count'] ?? 16,
                    'completed_at' => $result['summary_completed_at']
                ];
            }
        }

        echo json_encode([
            'success' => true,
            'summary_statuses' => $summary_statuses
        ]);
    } catch (Exception $e) {
        echo json_encode([
            'success' => false,
            'error' => '檢查摘要狀態時發生錯誤: ' . $e->getMessage()
        ]);
    }
} else {
    echo json_encode(['success' => false, 'error' => '無效的操作']);
}
