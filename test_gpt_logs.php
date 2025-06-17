<?php
session_start();

// 模擬登入狀態
$_SESSION['user_id'] = 1;

// 模擬POST請求
$_POST['action'] = 'ask';
$_POST['question'] = '[AMZN] 2024年的營運重點是什麼？';

// 設置錯誤報告
error_reporting(E_ALL);
ini_set('display_errors', 1);

// 設置日誌文件
ini_set('log_errors', 1);
ini_set('error_log', 'gpt_communication.log');

echo "<h1>GPT 通信日誌測試</h1>";
echo "<p>問題: [AMZN] 2024年的營運重點是什麼？</p>";
echo "<p>開始處理請求...</p>";

// 包含API文件
require_once 'php/api_improved.php';
