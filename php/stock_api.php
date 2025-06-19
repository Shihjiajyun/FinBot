<?php
require_once 'config.php';

header('Content-Type: application/json');

// 檢查登入狀態
if (!isset($_SESSION['user_id'])) {
    echo json_encode(['success' => false, 'error' => '請先登入']);
    exit;
}

// 處理股票資訊查詢
if ($_POST['action'] ?? '' === 'get_stock_info') {
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

        // 獲取財務數據
        $financial_data = getFinancialData($ticker);

        echo json_encode([
            'success' => true,
            'stock_info' => $result['data'],
            'financial_data' => $financial_data
        ]);
    } catch (Exception $e) {
        error_log("股票查詢錯誤: " . $e->getMessage());
        echo json_encode(['success' => false, 'error' => '系統錯誤，請稍後再試']);
    }

    exit;
}

// 獲取股票查詢歷史
if ($_GET['action'] ?? '' === 'get_stock_history') {
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
if ($_GET['action'] ?? '' === 'get_popular_stocks') {
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

echo json_encode(['success' => false, 'error' => '未知的操作']);
