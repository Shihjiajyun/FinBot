<?php
require_once 'config.php';

try {
    $db = new Database();
    $pdo = $db->getConnection();

    $sql = "CREATE TABLE IF NOT EXISTS tenk_qa_cache (
        id INT AUTO_INCREMENT PRIMARY KEY,
        cache_key VARCHAR(255) UNIQUE,
        answer LONGTEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )";

    $pdo->exec($sql);
    echo "Table tenk_qa_cache created successfully!";
} catch (Exception $e) {
    echo "Error creating table: " . $e->getMessage();
}
