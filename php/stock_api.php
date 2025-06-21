<?php
require_once 'config.php';

// 格式化檔案大小的輔助函數
function formatFileSize($bytes)
{
    if ($bytes >= 1073741824) {
        return number_format($bytes / 1073741824, 2) . ' GB';
    } elseif ($bytes >= 1048576) {
        return number_format($bytes / 1048576, 2) . ' MB';
    } elseif ($bytes >= 1024) {
        return number_format($bytes / 1024, 2) . ' KB';
    } else {
        return $bytes . ' B';
    }
}

header('Content-Type: application/json');

// 檢查登入狀態
if (!isset($_SESSION['user_id'])) {
    echo json_encode(['success' => false, 'error' => '請先登入']);
    exit;
}

// 首先處理所有 POST 請求
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action = $_POST['action'] ?? '';

    // 獲取10-K檔案列表 - 移到最前面優先處理
    if ($action === 'get_10k_files') {
        // 添加調試日志
        error_log(" 收到 get_10k_files 請求，POST 數據: " . print_r($_POST, true));

        $ticker = strtoupper(trim($_POST['ticker'] ?? ''));

        if (empty($ticker)) {
            error_log(" 股票代號為空");
            echo json_encode(['success' => false, 'error' => '股票代號不能為空']);
            exit;
        }

        error_log(" 處理 10-K 檔案請求，股票代號: $ticker");

        try {
            // 使用相對路徑
            $downloadsPath = __DIR__ . '/../downloads/' . $ticker . '/10-K/';

            // 添加調試信息
            $debugInfo = [
                'ticker' => $ticker,
                'current_dir' => __DIR__,
                'downloads_path' => $downloadsPath,
                'downloads_path_exists' => is_dir($downloadsPath),
                'parent_dir' => dirname(__DIR__),
                'downloads_base' => dirname(__DIR__) . '/downloads',
                'downloads_base_exists' => is_dir(dirname(__DIR__) . '/downloads'),
                'ticker_dir' => dirname(__DIR__) . '/downloads/' . $ticker,
                'ticker_dir_exists' => is_dir(dirname(__DIR__) . '/downloads/' . $ticker)
            ];

            if (!is_dir($downloadsPath)) {
                echo json_encode([
                    'success' => false,
                    'error' => '找不到該股票的10-K檔案目錄',
                    'debug_info' => $debugInfo
                ]);
                exit;
            }

            $files = [];
            $allFiles = [];
            $iterator = new DirectoryIterator($downloadsPath);

            foreach ($iterator as $fileInfo) {
                if ($fileInfo->isDot() || $fileInfo->isDir()) {
                    continue;
                }

                $filename = $fileInfo->getFilename();
                $extension = pathinfo($filename, PATHINFO_EXTENSION);

                // 記錄所有檔案用於調試
                $allFiles[] = [
                    'filename' => $filename,
                    'extension' => $extension,
                    'size' => $fileInfo->getSize()
                ];

                if ($extension === 'txt') {
                    $files[] = [
                        'filename' => $filename,
                        'size' => formatFileSize($fileInfo->getSize()),
                        'date' => date('Y-m-d H:i', $fileInfo->getMTime()),
                        'path' => $fileInfo->getPathname()
                    ];
                }
            }

            // 按修改時間排序，最新的在前
            usort($files, function ($a, $b) {
                return strcmp($b['date'], $a['date']);
            });

            echo json_encode([
                'success' => true,
                'files' => $files,
                'total_files' => count($files),
                'all_files_in_directory' => $allFiles,
                'debug_info' => $debugInfo
            ]);
        } catch (Exception $e) {
            echo json_encode([
                'success' => false,
                'error' => '讀取檔案列表時發生錯誤: ' . $e->getMessage(),
                'debug_info' => $debugInfo ?? null
            ]);
        }

        exit;
    }

    // 處理股票資訊查詢
    if ($action === 'get_stock_info') {
        $ticker = strtoupper(trim($_POST['ticker'] ?? ''));

        if (empty($ticker)) {
            echo json_encode(['success' => false, 'error' => '股票代號不能為空']);
            exit;
        }

        // 驗證股票代號格式（只允許字母和數字）
        if (!preg_match('/^[A-Z0-9]{1,10}$/', $ticker)) {
            echo json_encode(['success' => false, 'error' => '股票代號格式錯誤']);
            exit;
        }

        try {
            // 首先檢查資料庫是否有該股票的財務數據
            $financial_data = getFinancialData($ticker);

            // 改進的檢查邏輯：檢查是否有基本的財務數據
            $has_financial_data = $financial_data['total_years'] > 0 &&
                (!empty($financial_data['growth_rates']) ||
                    !empty($financial_data['absolute_metrics']) ||
                    !empty($financial_data['balance_sheet_data']));

            // 如果沒有財務數據，返回分析狀態讓前端處理
            if (!$has_financial_data) {
                error_log(" 股票 $ticker 沒有財務數據，返回分析狀態 (total_years: {$financial_data['total_years']})");

                echo json_encode([
                    'success' => true,
                    'status' => 'analyzing',
                    'message' => '正在分析並獲取該股票的財務數據，請稍候...',
                    'ticker' => $ticker,
                    'needs_analysis' => true
                ]);
                exit;
            }

            // 添加調試日誌
            error_log(" 股票 $ticker 找到財務數據：{$financial_data['total_years']} 年數據");

            // 獲取Python腳本的路徑
            $python_script = dirname(__DIR__) . '/stock_info.py';

            // 檢查Python腳本是否存在
            if (!file_exists($python_script)) {
                echo json_encode(['success' => false, 'error' => 'Python腳本未找到']);
                exit;
            }

            // 執行Python腳本獲取股票資訊
            $python_cmd = PYTHON_COMMAND;
            $command = "\"$python_cmd\" \"$python_script\" \"$ticker\" 2>&1";
            $output = shell_exec($command);

            if ($output === null || empty(trim($output))) {
                // 記錄詳細錯誤信息用於調試
                error_log("Python執行失敗 - 命令: $command");
                error_log("Python路徑: $python_cmd");
                error_log("腳本路徑: $python_script");

                echo json_encode([
                    'success' => false,
                    'error' => '無法執行Python腳本',
                    'debug_info' => "使用的Python命令: $python_cmd"
                ]);
                exit;
            }

            // 解析Python腳本的輸出
            $result = json_decode($output, true);

            if (json_last_error() !== JSON_ERROR_NONE) {
                // 如果JSON解析失敗，記錄原始輸出用於調試
                error_log("Python輸出: " . $output);
                echo json_encode(['success' => false, 'error' => 'Python腳本輸出格式錯誤']);
                exit;
            }

            if (!$result['success']) {
                echo json_encode(['success' => false, 'error' => $result['error']]);
                exit;
            }

            echo json_encode([
                'success' => true,
                'stock_info' => $result['data'],
                'financial_data' => $financial_data,
                'data_freshly_analyzed' => !$has_financial_data
            ]);
        } catch (Exception $e) {
            error_log("股票查詢錯誤: " . $e->getMessage());
            echo json_encode(['success' => false, 'error' => '系統錯誤，請稍後再試']);
        }

        exit;
    }

    // 新增：專門處理財務數據分析的 API 端點
    if ($action === 'analyze_financial_data') {
        $ticker = strtoupper(trim($_POST['ticker'] ?? ''));

        if (empty($ticker)) {
            echo json_encode(['success' => false, 'error' => '股票代號不能為空']);
            exit;
        }

        // 驗證股票代號格式
        if (!preg_match('/^[A-Z0-9]{1,10}$/', $ticker)) {
            echo json_encode(['success' => false, 'error' => '股票代號格式錯誤']);
            exit;
        }

        try {
            error_log("🔍 開始分析股票 $ticker 的財務數據");

            // 設置響應頭確保 JSON 輸出完整
            header('Content-Type: application/json; charset=utf-8');

            // 禁用輸出緩衝
            if (ob_get_level()) {
                ob_end_clean();
            }

            // 執行 dual_source_analyzer.py
            $analysis_result = executeDualSourceAnalyzer($ticker);

            if ($analysis_result['success']) {
                // 分析成功後，重新獲取財務數據
                $financial_data = getFinancialData($ticker);

                $response = [
                    'success' => true,
                    'message' => '財務數據分析完成',
                    'financial_data' => $financial_data,
                    'analysis_log' => substr($analysis_result['log'], -1000) // 只保留最後1000字符的日誌
                ];

                echo json_encode($response, JSON_UNESCAPED_UNICODE);
            } else {
                $response = [
                    'success' => false,
                    'error' => $analysis_result['error'],
                    'analysis_log' => isset($analysis_result['log']) ? substr($analysis_result['log'], -1000) : null
                ];

                echo json_encode($response, JSON_UNESCAPED_UNICODE);
            }
        } catch (Exception $e) {
            error_log("財務數據分析錯誤: " . $e->getMessage());
            echo json_encode(['success' => false, 'error' => '分析過程中發生錯誤'], JSON_UNESCAPED_UNICODE);
        }

        exit;
    }
}

// 處理 GET 請求
if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    $action = $_GET['action'] ?? '';

    // 獲取股票查詢歷史
    if ($action === 'get_stock_history') {
        try {
            $db = new Database();
            $pdo = $db->getConnection();

            $stmt = $pdo->prepare("
                SELECT ticker, query_time, result_data 
                FROM stock_queries 
                WHERE user_id = ? 
                ORDER BY query_time DESC 
                LIMIT 20
            ");
            $stmt->execute([$_SESSION['user_id']]);
            $history = $stmt->fetchAll();

            echo json_encode([
                'success' => true,
                'history' => $history
            ]);
        } catch (Exception $e) {
            error_log("獲取股票歷史錯誤: " . $e->getMessage());
            echo json_encode(['success' => false, 'error' => '獲取歷史記錄失敗']);
        }

        exit;
    }

    // 獲取熱門股票列表
    if ($action === 'get_popular_stocks') {
        try {
            $popular_stocks = [
                ['symbol' => 'AAPL', 'name' => 'Apple Inc.', 'category' => '科技'],
                ['symbol' => 'MSFT', 'name' => 'Microsoft Corporation', 'category' => '科技'],
                ['symbol' => 'GOOGL', 'name' => 'Alphabet Inc.', 'category' => '科技'],
                ['symbol' => 'AMZN', 'name' => 'Amazon.com Inc.', 'category' => '科技'],
                ['symbol' => 'TSLA', 'name' => 'Tesla Inc.', 'category' => '科技'],
                ['symbol' => 'META', 'name' => 'Meta Platforms Inc.', 'category' => '科技'],
                ['symbol' => 'NVDA', 'name' => 'NVIDIA Corporation', 'category' => '科技'],
                ['symbol' => 'NFLX', 'name' => 'Netflix Inc.', 'category' => '科技'],
                ['symbol' => 'JPM', 'name' => 'JPMorgan Chase & Co.', 'category' => '金融'],
                ['symbol' => 'V', 'name' => 'Visa Inc.', 'category' => '金融'],
                ['symbol' => 'JNJ', 'name' => 'Johnson & Johnson', 'category' => '醫療'],
                ['symbol' => 'KO', 'name' => 'Coca-Cola Company', 'category' => '消費'],
            ];

            echo json_encode([
                'success' => true,
                'stocks' => $popular_stocks
            ]);
        } catch (Exception $e) {
            echo json_encode(['success' => false, 'error' => '獲取熱門股票失敗']);
        }

        exit;
    }
}

// 執行 dual_source_analyzer.py 腳本
function executeDualSourceAnalyzer($ticker)
{
    try {
        error_log(" 準備執行 dual_source_analyzer.py 分析股票: $ticker");

        // dual_source_analyzer.py 的路徑
        $python_script = dirname(__DIR__) . '/dual_source_analyzer.py';

        // 檢查 Python 腳本是否存在
        if (!file_exists($python_script)) {
            error_log(" dual_source_analyzer.py 腳本未找到: $python_script");
            return [
                'success' => false,
                'error' => 'dual_source_analyzer.py 腳本未找到'
            ];
        }

        // 支持任何股票代號 - 不再限制特定股票列表
        $company_name = $ticker; // Python 腳本會自動從 Yahoo Finance 獲取公司名稱

        // 使用 Python 命令
        $python_cmd = PYTHON_COMMAND;

        // 設置更長的執行時間限制
        set_time_limit(300); // 5分鐘

        // 增加記憶體限制
        ini_set('memory_limit', '512M');

        // 構建命令 - 使用命令行參數（非互動模式）
        $command = "\"$python_cmd\" \"$python_script\" 2 $ticker 2>&1";

        error_log("📝 執行命令: $command");

        // 執行命令並獲取輸出
        $output = shell_exec($command);
        $exit_code = 0; // shell_exec不直接返回退出代碼，我們將基於輸出判斷

        error_log("✅ Python 腳本執行完成");
        error_log("📊 輸出長度: " . strlen($output) . " 字符");

        // 只記錄輸出的最後部分，避免日誌過長
        if (strlen($output) > 2000) {
            error_log("📋 輸出摘要: " . substr($output, -2000));
        } else {
            error_log("📋 完整輸出: " . $output);
        }

        // 檢查是否成功 - 更新成功指標
        $success_indicators = ['🎉 股票', '財務數據分析成功完成', 'Successfully stored', 'SUCCESS'];
        $has_success = false;

        foreach ($success_indicators as $indicator) {
            if (strpos($output, $indicator) !== false) {
                $has_success = true;
                break;
            }
        }

        // 檢查錯誤指標 - 但忽略 404 錯誤（因為 Macrotrends 沒有某些頁面）
        $error_indicators = ['ERROR: Analysis failed', 'CRITICAL ERROR', 'Database connection failed'];
        $has_error = false;

        foreach ($error_indicators as $indicator) {
            if (strpos($output, $indicator) !== false) {
                $has_error = true;
                break;
            }
        }

        if ($has_success && !$has_error) {
            error_log("🎉 股票 $ticker 財務數據分析成功完成");
            return [
                'success' => true,
                'message' => '財務數據分析並存入資料庫成功',
                'log' => $output
            ];
        } else {
            error_log(" 股票 $ticker 分析可能失敗");
            return [
                'success' => false,
                'error' => '分析過程中可能發生錯誤',
                'log' => $output
            ];
        }
    } catch (Exception $e) {
        error_log(" executeDualSourceAnalyzer 發生異常: " . $e->getMessage());
        return [
            'success' => false,
            'error' => '執行分析時發生異常: ' . $e->getMessage()
        ];
    }
}

// 獲取財務數據和計算增長率
function getFinancialData($ticker)
{
    try {
        $db = new Database();
        $pdo = $db->getConnection();

        // 查詢該股票的財務數據，按年份排序（增加查詢筆數）
        $stmt = $pdo->prepare("
            SELECT 
                filing_year,
                revenue,
                operating_cash_flow,
                net_income,
                shareholders_equity,
                company_name,
                cogs,
                gross_profit,
                operating_income,
                operating_expenses,
                income_before_tax,
                eps_basic,
                outstanding_shares,
                current_assets,
                total_assets,
                current_liabilities,
                total_liabilities,
                long_term_debt,
                retained_earnings_balance,
                current_ratio,
                free_cash_flow,
                cash_flow_investing,
                cash_flow_financing,
                cash_and_cash_equivalents
            FROM filings 
            WHERE ticker = ? 
            AND filing_type = 'ANNUAL_FINANCIAL'
            ORDER BY filing_year DESC
            LIMIT 10
        ");

        $stmt->execute([$ticker]);
        $raw_data = $stmt->fetchAll(PDO::FETCH_ASSOC);

        if (empty($raw_data)) {
            return [
                'years' => [],
                'growth_rates' => [],
                'absolute_metrics' => [],
                'balance_sheet_data' => [],
                'cash_flow_data' => [],
                'message' => '目前沒有該股票的財務數據',
                'company_name' => null,
                'total_years' => 0
            ];
        }

        $years = [];
        $growth_rates = [];
        $absolute_metrics = [];
        $balance_sheet_data = [];
        $cash_flow_data = [];
        $company_name = $raw_data[0]['company_name'];
        $total_years = count($raw_data);

        // 反轉數據以便從舊到新計算增長率
        $raw_data = array_reverse($raw_data);

        foreach ($raw_data as $index => $data) {
            $year = $data['filing_year'];
            $years[] = $year;

            // 計算增長率
            $growth_rate = [
                'year' => $year,
                'equity_growth' => null,
                'net_income_growth' => null,
                'cash_flow_growth' => null,
                'revenue_growth' => null
            ];

            // 如果不是第一年，計算相對於前一年的增長率
            if ($index > 0) {
                $prev_data = $raw_data[$index - 1];

                // 股東權益成長率
                if ($prev_data['shareholders_equity'] > 0) {
                    $growth_rate['equity_growth'] = (($data['shareholders_equity'] - $prev_data['shareholders_equity']) / $prev_data['shareholders_equity']) * 100;
                }

                // 淨利成長率
                if ($prev_data['net_income'] > 0) {
                    $growth_rate['net_income_growth'] = (($data['net_income'] - $prev_data['net_income']) / $prev_data['net_income']) * 100;
                }

                // 現金流成長率
                if ($prev_data['operating_cash_flow'] > 0) {
                    $growth_rate['cash_flow_growth'] = (($data['operating_cash_flow'] - $prev_data['operating_cash_flow']) / $prev_data['operating_cash_flow']) * 100;
                }

                // 營收成長率
                if ($prev_data['revenue'] > 0) {
                    $growth_rate['revenue_growth'] = (($data['revenue'] - $prev_data['revenue']) / $prev_data['revenue']) * 100;
                }
            }

            $growth_rates[] = $growth_rate;

            // 計算絕對數值指標和比率
            $absolute_metric = [
                'year' => $year,
                'revenue' => $data['revenue'],
                'cogs' => $data['cogs'],
                'gross_profit' => $data['gross_profit'],
                'operating_income' => $data['operating_income'],
                'operating_expenses' => $data['operating_expenses'],
                'income_before_tax' => $data['income_before_tax'],
                'net_income' => $data['net_income'],
                'eps_basic' => $data['eps_basic'],
                'outstanding_shares' => $data['outstanding_shares'],
                'net_income_margin' => $data['revenue'] > 0 ? ($data['net_income'] / $data['revenue'] * 100) : null,
                'gross_margin' => $data['revenue'] > 0 ? ($data['gross_profit'] / $data['revenue'] * 100) : null,
                'operating_margin' => $data['revenue'] > 0 ? ($data['operating_income'] / $data['revenue'] * 100) : null
            ];

            $absolute_metrics[] = $absolute_metric;

            // 計算資產負債表指標
            $balance_sheet_metric = [
                'year' => $year,
                'current_assets' => $data['current_assets'],
                'total_assets' => $data['total_assets'],
                'current_liabilities' => $data['current_liabilities'],
                'total_liabilities' => $data['total_liabilities'],
                'long_term_debt' => $data['long_term_debt'],
                'retained_earnings' => $data['retained_earnings_balance'],
                'shareholders_equity' => $data['shareholders_equity'],
                'current_ratio' => $data['current_ratio'],
                // 計算比率指標
                'book_value_per_share' => ($data['shareholders_equity'] > 0 && $data['outstanding_shares'] > 0)
                    ? ($data['shareholders_equity'] / $data['outstanding_shares']) : null,
                'roa' => ($data['net_income'] > 0 && $data['total_assets'] > 0)
                    ? ($data['net_income'] / $data['total_assets'] * 100) : null,
                'roe' => ($data['net_income'] > 0 && $data['shareholders_equity'] > 0)
                    ? ($data['net_income'] / $data['shareholders_equity'] * 100) : null,
                'roic' => ($data['operating_income'] > 0 && $data['total_assets'] > 0 && $data['current_liabilities'] > 0)
                    ? ($data['operating_income'] / ($data['total_assets'] - $data['current_liabilities']) * 100) : null,
                'debt_equity_ratio' => ($data['total_liabilities'] > 0 && $data['shareholders_equity'] > 0)
                    ? ($data['total_liabilities'] / $data['shareholders_equity']) : null,
                'debt_payoff_years' => ($data['total_liabilities'] > 0 && $data['operating_cash_flow'] > 0)
                    ? ($data['total_liabilities'] / $data['operating_cash_flow']) : null
            ];

            $balance_sheet_data[] = $balance_sheet_metric;

            // 計算現金流指標
            $cash_flow_metric = [
                'year' => $year,
                'net_income' => $data['net_income'],
                'operating_cash_flow' => $data['operating_cash_flow'],
                'free_cash_flow' => $data['free_cash_flow'],
                'cash_flow_investing' => $data['cash_flow_investing'],
                'cash_flow_financing' => $data['cash_flow_financing'],
                'cash_and_cash_equivalents' => $data['cash_and_cash_equivalents']
            ];

            $cash_flow_data[] = $cash_flow_metric;
        }

        // 反轉結果數組以便從新到舊顯示
        $growth_rates = array_reverse($growth_rates);
        $absolute_metrics = array_reverse($absolute_metrics);
        $balance_sheet_data = array_reverse($balance_sheet_data);
        $cash_flow_data = array_reverse($cash_flow_data);

        return [
            'years' => array_reverse($years),
            'growth_rates' => $growth_rates,
            'absolute_metrics' => $absolute_metrics,
            'balance_sheet_data' => $balance_sheet_data,
            'cash_flow_data' => $cash_flow_data,
            'company_name' => $company_name,
            'total_years' => $total_years
        ];
    } catch (Exception $e) {
        error_log("獲取財務數據錯誤: " . $e->getMessage());
        return [
            'years' => [],
            'growth_rates' => [],
            'absolute_metrics' => [],
            'balance_sheet_data' => [],
            'cash_flow_data' => [],
            'message' => '獲取財務數據時發生錯誤',
            'company_name' => null,
            'total_years' => 0
        ];
    }
}

// 調試：記錄所有未匹配的請求
error_log(" 未知操作，請求方法: " . $_SERVER['REQUEST_METHOD'] . ", POST action: " . ($_POST['action'] ?? 'undefined') . ", GET action: " . ($_GET['action'] ?? 'undefined'));
echo json_encode(['success' => false, 'error' => '未知的操作']);
