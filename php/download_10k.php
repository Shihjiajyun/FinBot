<?php
require_once 'config.php';

// 檢查登入狀態
if (!isset($_SESSION['user_id'])) {
    http_response_code(403);
    die('未授權訪問');
}

$ticker = strtoupper(trim($_GET['ticker'] ?? ''));
$filename = trim($_GET['file'] ?? '');

if (empty($ticker) || empty($filename)) {
    http_response_code(400);
    die('缺少必要參數');
}

// 驗證檔案路徑安全性
if (strpos($filename, '..') !== false || strpos($filename, '/') !== false || strpos($filename, '\\') !== false) {
    http_response_code(400);
    die('無效的檔案名稱');
}

$file_path = dirname(__DIR__) . DIRECTORY_SEPARATOR . 'downloads' . DIRECTORY_SEPARATOR . $ticker . DIRECTORY_SEPARATOR . '10-K' . DIRECTORY_SEPARATOR . $filename;

if (!file_exists($file_path)) {
    http_response_code(404);
    die('檔案不存在');
}

// 設定下載標頭
header('Content-Type: text/plain');
header('Content-Disposition: attachment; filename="' . $filename . '"');
header('Content-Length: ' . filesize($file_path));

// 輸出檔案內容
readfile($file_path);
exit;
