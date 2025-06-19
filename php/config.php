<?php
// FinBot 系統配置文件
date_default_timezone_set('Asia/Taipei');

// 環境變數支援 - 優先使用環境變數，再使用預設值
function getEnvVar($key, $default = null)
{
    $value = getenv($key);
    return $value !== false ? $value : $default;
}

// 資料庫配置 - 支援環境變數
define('DB_HOST', getEnvVar('DB_HOST', '43.207.210.147'));
define('DB_NAME', getEnvVar('DB_NAME', 'finbot_db'));
define('DB_USER', getEnvVar('DB_USER', 'myuser'));
define('DB_PASS', getEnvVar('DB_PASS', '123456789'));
define('DB_CHARSET', 'utf8mb4');

// GPT API 配置 - 支援環境變數
define('OPENAI_API_KEY', getEnvVar('OPENAI_API_KEY', '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'));
define('OPENAI_API_URL', 'https://api.openai.com/v1/chat/completions');
define('OPENAI_MODEL', getEnvVar('OPENAI_MODEL', 'gpt-4o'));

// 系統設定
define('SESSION_TIMEOUT', 7200); // 2小時
define('MAX_UPLOAD_SIZE', 50 * 1024 * 1024); // 50MB
define('DOWNLOADS_PATH', '../downloads/');
define('PYTHON_SCRIPT_PATH', '../');

// Python配置 - 跨平台自動偵測
function getPythonCommand()
{
    // 首先檢查環境變數
    $env_python = getEnvVar('PYTHON_PATH');
    if ($env_python && isPythonValid($env_python)) {
        return $env_python;
    }

    // 偵測作業系統
    $os = strtoupper(substr(PHP_OS, 0, 3));

    if ($os === 'WIN') {
        // Windows 路徑
        $python_paths = [
            'C:\\Users\\shihj\\anaconda3\\python.exe', // 保留開發環境路徑
            'C:\\Python312\\python.exe',
            'C:\\Python311\\python.exe',
            'C:\\Python310\\python.exe',
            'C:\\Python39\\python.exe',
            'python.exe',
            'python3.exe',
            'python'
        ];
    } else {
        // Linux/Unix 路徑
        $python_paths = [
            '/opt/bitnami/apache/htdocs/FinBot/finbot_env/bin/python3', // 虛擬環境 Python
            '/usr/bin/python3',
            '/usr/bin/python',
            '/usr/local/bin/python3',
            '/usr/local/bin/python',
            '/opt/python3/bin/python3',
            'python3',
            'python'
        ];
    }

    foreach ($python_paths as $path) {
        if (isPythonValid($path)) {
            return $path;
        }
    }

    // 如果都找不到，返回系統預設
    return ($os === 'WIN') ? 'python' : 'python3';
}

// 檢查Python是否有效
function isPythonValid($python_path)
{
    $test_cmd = "\"$python_path\" --version 2>&1";
    $output = shell_exec($test_cmd);

    return ($output !== null && strpos($output, 'Python') !== false);
}

define('PYTHON_COMMAND', getPythonCommand());

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
            error_log("資料庫連接失敗: " . $e->getMessage());
            die("資料庫連接失敗，請檢查配置");
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
