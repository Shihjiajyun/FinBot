<?php
require_once 'config.php';

// 檢查登入狀態
if (!isset($_SESSION['user_id'])) {
    redirect('index.php');
}

$user_id = $_SESSION['user_id'];

// 獲取用戶問答歷史
$db = new Database();
$pdo = $db->getConnection();

$page = max(1, intval($_GET['page'] ?? 1));
$limit = 10;
$offset = ($page - 1) * $limit;

// 獲取總數
$countStmt = $pdo->prepare("
    SELECT COUNT(*) as total 
    FROM user_questions uq 
    JOIN questions q ON uq.question_id = q.id 
    WHERE uq.user_id = ?
");
$countStmt->execute([$user_id]);
$totalQuestions = $countStmt->fetch()['total'];
$totalPages = ceil($totalQuestions / $limit);

// 獲取問答記錄
$stmt = $pdo->prepare("
    SELECT q.question, q.answer, q.created_at, 
           f.company_name, f.filing_type, f.report_date,
           uq.asked_at
    FROM user_questions uq 
    JOIN questions q ON uq.question_id = q.id 
    LEFT JOIN filings f ON q.filing_id = f.id
    WHERE uq.user_id = ?
    ORDER BY uq.asked_at DESC 
    LIMIT ? OFFSET ?
");
$stmt->execute([$user_id, $limit, $offset]);
$questions = $stmt->fetchAll();
?>

<!DOCTYPE html>
<html lang="zh-TW">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>歷史記錄 - FinBot</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        :root {
            --primary-color: #2c5aa0;
            --secondary-color: #f8f9fa;
        }

        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }

        .main-container {
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            margin: 20px 0;
            overflow: hidden;
        }

        .header {
            background: var(--primary-color);
            color: white;
            padding: 20px;
        }

        .question-card {
            border: none;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
            overflow: hidden;
        }

        .question-header {
            background: var(--secondary-color);
            padding: 15px 20px;
            border-bottom: 1px solid #dee2e6;
        }

        .question-body {
            padding: 20px;
        }

        .question-text {
            background: var(--primary-color);
            color: white;
            padding: 12px 18px;
            border-radius: 18px;
            display: inline-block;
            margin-bottom: 15px;
            max-width: 80%;
        }

        .answer-text {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
            border-left: 4px solid var(--primary-color);
        }

        .meta-info {
            font-size: 0.85em;
            color: #6c757d;
            margin-top: 10px;
        }

        .filing-info {
            background: #e3f2fd;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.85em;
            display: inline-block;
            margin-top: 5px;
        }
    </style>
</head>

<body>
    <div class="container">
        <div class="main-container">
            <div class="header">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h3><i class="bi bi-clock-history me-2"></i>問答歷史記錄</h3>
                        <p class="mb-0">共 <?= $totalQuestions ?> 個問題</p>
                    </div>
                    <div>
                        <a href="index.php" class="btn btn-light">
                            <i class="bi bi-arrow-left"></i> 返回主頁
                        </a>
                    </div>
                </div>
            </div>

            <div class="p-4">
                <?php if (empty($questions)): ?>
                    <div class="text-center py-5">
                        <i class="bi bi-question-circle" style="font-size: 4rem; color: #ccc;"></i>
                        <h4 class="mt-3 text-muted">還沒有問答記錄</h4>
                        <p class="text-muted">開始提問來建立您的第一個記錄吧！</p>
                        <a href="index.php" class="btn btn-primary">
                            <i class="bi bi-chat-dots"></i> 開始提問
                        </a>
                    </div>
                <?php else: ?>
                    <?php foreach ($questions as $qa): ?>
                        <div class="question-card">
                            <div class="question-header">
                                <div class="d-flex justify-content-between align-items-center">
                                    <strong>
                                        <i class="bi bi-calendar3"></i>
                                        <?= date('Y-m-d H:i', strtotime($qa['asked_at'])) ?>
                                    </strong>
                                    <?php if ($qa['company_name']): ?>
                                        <div class="filing-info">
                                            <i class="bi bi-building"></i>
                                            <?= htmlspecialchars($qa['company_name']) ?>
                                            - <?= htmlspecialchars($qa['filing_type']) ?>
                                            <?php if ($qa['report_date']): ?>
                                                (<?= date('Y-m-d', strtotime($qa['report_date'])) ?>)
                                            <?php endif; ?>
                                        </div>
                                    <?php endif; ?>
                                </div>
                            </div>

                            <div class="question-body">
                                <div class="mb-3">
                                    <div class="question-text">
                                        <i class="bi bi-person-fill me-2"></i>
                                        <?= nl2br(htmlspecialchars($qa['question'])) ?>
                                    </div>
                                </div>

                                <div class="answer-text">
                                    <div class="mb-2">
                                        <i class="bi bi-robot me-2"></i>
                                        <strong>FinBot 回答:</strong>
                                    </div>
                                    <?= nl2br(htmlspecialchars($qa['answer'])) ?>
                                </div>
                            </div>
                        </div>
                    <?php endforeach; ?>

                    <?php if ($totalPages > 1): ?>
                        <nav aria-label="問答記錄分頁">
                            <ul class="pagination justify-content-center">
                                <?php if ($page > 1): ?>
                                    <li class="page-item">
                                        <a class="page-link" href="?page=<?= $page - 1 ?>">
                                            <i class="bi bi-chevron-left"></i> 上一頁
                                        </a>
                                    </li>
                                <?php endif; ?>

                                <?php for ($i = max(1, $page - 2); $i <= min($totalPages, $page + 2); $i++): ?>
                                    <li class="page-item <?= $i == $page ? 'active' : '' ?>">
                                        <a class="page-link" href="?page=<?= $i ?>"><?= $i ?></a>
                                    </li>
                                <?php endfor; ?>

                                <?php if ($page < $totalPages): ?>
                                    <li class="page-item">
                                        <a class="page-link" href="?page=<?= $page + 1 ?>">
                                            下一頁 <i class="bi bi-chevron-right"></i>
                                        </a>
                                    </li>
                                <?php endif; ?>
                            </ul>
                        </nav>
                    <?php endif; ?>
                <?php endif; ?>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>

</html>