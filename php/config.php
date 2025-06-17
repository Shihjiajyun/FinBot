<?php
// FinBot 系統配置文件
date_default_timezone_set('Asia/Taipei');

// 資料庫配置
define('DB_HOST', '43.207.210.147');
define('DB_NAME', 'finbot_db');
define('DB_USER', 'myuser');
define('DB_PASS', '123456789');
define('DB_CHARSET', 'utf8mb4');

// GPT API 配置
define('OPENAI_API_KEY', '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'); // 請替換成你的API Key
define('OPENAI_API_URL', 'https://api.openai.com/v1/chat/completions');
define('OPENAI_MODEL', 'gpt-4o');

// 系統設定
define('SESSION_TIMEOUT', 7200); // 2小時
define('MAX_UPLOAD_SIZE', 50 * 1024 * 1024); // 50MB
define('DOWNLOADS_PATH', '../downloads/');
define('PYTHON_SCRIPT_PATH', '../');

// 資料庫連接類
class Database
{
    private $pdo;

    public function __construct()
    {
        try {
            $dsn = "mysql:host=" . DB_HOST . ";dbname=" . DB_NAME . ";charset=" . DB_CHARSET;
            $options = [
                PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                PDO::ATTR_EMULATE_PREPARES => false,
            ];
            $this->pdo = new PDO($dsn, DB_USER, DB_PASS, $options);
        } catch (PDOException $e) {
            die("資料庫連接失敗: " . $e->getMessage());
        }
    }

    public function getConnection()
    {
        return $this->pdo;
    }
}

// GPT API 調用類
class GPTClient
{
    private $api_key;
    private $api_url;
    private $model;

    public function __construct()
    {
        $this->api_key = OPENAI_API_KEY;
        $this->api_url = OPENAI_API_URL;
        $this->model = OPENAI_MODEL;
    }

    public function askQuestion($system_prompt, $user_message)
    {
        $data = [
            'model' => $this->model,
            'messages' => [
                [
                    'role' => 'system',
                    'content' => $system_prompt
                ],
                [
                    'role' => 'user',
                    'content' => $user_message
                ]
            ],
            'max_tokens' => 2000,
            'temperature' => 0.7
        ];

        $headers = [
            'Content-Type: application/json',
            'Authorization: Bearer ' . $this->api_key
        ];

        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $this->api_url);
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
        curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 60);

        $response = curl_exec($ch);
        $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        if ($http_code !== 200) {
            throw new Exception("GPT API 調用失敗: HTTP " . $http_code);
        }

        $result = json_decode($response, true);
        if (json_last_error() !== JSON_ERROR_NONE) {
            throw new Exception("GPT API 回應解析失敗");
        }

        return $result['choices'][0]['message']['content'] ?? '';
    }
}

// 工具函數
function sanitize_input($data)
{
    return htmlspecialchars(strip_tags(trim($data)), ENT_QUOTES, 'UTF-8');
}

function json_response($data, $status_code = 200)
{
    http_response_code($status_code);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
    exit;
}

function redirect($url)
{
    header("Location: " . $url);
    exit;
}

// 自動加載類
spl_autoload_register(function ($class) {
    $file = __DIR__ . '/' . str_replace('\\', '/', $class) . '.php';
    if (file_exists($file)) {
        require_once $file;
    }
});

// 開始 Session
if (session_status() === PHP_SESSION_NONE) {
    session_start();
}
