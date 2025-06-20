<?php
require_once 'config.php';

// 檢查登入狀態
if (!isset($_SESSION['user_id'])) {
    header('Location: index.php');
    exit;
}

$ticker = strtoupper(trim($_GET['ticker'] ?? ''));
$filename = trim($_GET['file'] ?? '');

if (empty($ticker) || empty($filename)) {
    die('缺少必要參數');
}

// 驗證檔案路徑安全性
if (strpos($filename, '..') !== false || strpos($filename, '/') !== false || strpos($filename, '\\') !== false) {
    die('無效的檔案名稱');
}

$file_path = dirname(__DIR__) . DIRECTORY_SEPARATOR . 'downloads' . DIRECTORY_SEPARATOR . $ticker . DIRECTORY_SEPARATOR . '10-K' . DIRECTORY_SEPARATOR . $filename;

if (!file_exists($file_path)) {
    die('檔案不存在');
}

$file_content = file_get_contents($file_path);
$file_size = filesize($file_path);
$file_date = date('Y-m-d H:i:s', filemtime($file_path));

// 簡單的內容處理：移除過多的空行並保持基本格式
$file_content = preg_replace('/\n\s*\n\s*\n/', "\n\n", $file_content);
$file_content = htmlspecialchars($file_content);
?>

<!DOCTYPE html>
<html lang="zh-TW">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?= htmlspecialchars($ticker) ?> - <?= htmlspecialchars($filename) ?></title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        body {
            background-color: #f8f9fa;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }

        .file-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            margin-bottom: 2rem;
        }

        .file-info {
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }

        .file-content {
            background: white;
            border-radius: 8px;
            padding: 2rem;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            max-height: 70vh;
            overflow-y: auto;
        }

        .file-text {
            font-family: 'Courier New', monospace;
            font-size: 14px;
            line-height: 1.6;
            white-space: pre-wrap;
            word-wrap: break-word;
        }

        .toolbar {
            position: sticky;
            top: 0;
            background: white;
            border-bottom: 1px solid #dee2e6;
            padding: 1rem;
            margin: -2rem -2rem 2rem -2rem;
            z-index: 100;
        }

        .search-box {
            max-width: 400px;
        }

        .highlight {
            background-color: yellow;
            padding: 1px 2px;
        }

        .back-button {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1000;
        }
    </style>
</head>

<body>
    <button class="btn btn-primary back-button" onclick="window.close()">
        <i class="bi bi-x-lg"></i> 關閉
    </button>

    <div class="file-header">
        <div class="container-fluid">
            <h1><i class="bi bi-file-earmark-text"></i> <?= htmlspecialchars($ticker) ?> 10-K 財報</h1>
            <p class="mb-0">檔案名稱: <?= htmlspecialchars($filename) ?></p>
        </div>
    </div>

    <div class="container-fluid">
        <div class="file-info">
            <div class="row">
                <div class="col-md-4">
                    <h6>股票代號</h6>
                    <p><?= htmlspecialchars($ticker) ?></p>
                </div>
                <div class="col-md-4">
                    <h6>檔案大小</h6>
                    <p><?= number_format($file_size / 1024, 2) ?> KB</p>
                </div>
                <div class="col-md-4">
                    <h6>修改時間</h6>
                    <p><?= $file_date ?></p>
                </div>
            </div>
        </div>

        <div class="file-content">
            <div class="toolbar">
                <div class="row align-items-center">
                    <div class="col-md-6">
                        <div class="input-group search-box">
                            <input type="text" class="form-control" id="searchInput" placeholder="搜尋文件內容...">
                            <button class="btn btn-outline-secondary" type="button" onclick="searchText()">
                                <i class="bi bi-search"></i>
                            </button>
                            <button class="btn btn-outline-secondary" type="button" onclick="clearSearch()">
                                <i class="bi bi-x"></i>
                            </button>
                        </div>
                    </div>
                    <div class="col-md-6 text-end">
                        <button class="btn btn-sm btn-outline-primary" onclick="downloadFile()">
                            <i class="bi bi-download"></i> 下載檔案
                        </button>
                    </div>
                </div>
            </div>

            <div class="file-text" id="fileContent"><?= $file_content ?></div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        let originalContent = document.getElementById('fileContent').innerHTML;

        function searchText() {
            const searchTerm = document.getElementById('searchInput').value.trim();
            const content = document.getElementById('fileContent');

            if (!searchTerm) {
                content.innerHTML = originalContent;
                return;
            }

            // 清除之前的高亮
            content.innerHTML = originalContent;

            // 創建正則表達式進行搜尋（不區分大小寫）
            const regex = new RegExp(`(${searchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');

            // 高亮搜尋結果
            content.innerHTML = content.innerHTML.replace(regex, '<span class="highlight">$1</span>');

            // 滾動到第一個結果
            const firstHighlight = content.querySelector('.highlight');
            if (firstHighlight) {
                firstHighlight.scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });
            }
        }

        function clearSearch() {
            document.getElementById('searchInput').value = '';
            document.getElementById('fileContent').innerHTML = originalContent;
        }

        function downloadFile() {
            const link = document.createElement('a');
            link.href = 'download_10k.php?ticker=<?= urlencode($ticker) ?>&file=<?= urlencode($filename) ?>';
            link.download = '<?= htmlspecialchars($filename) ?>';
            link.click();
        }

        // Enter鍵搜尋
        document.getElementById('searchInput').addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                searchText();
            }
        });
    </script>
</body>

</html>