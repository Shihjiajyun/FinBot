import requests
import json
from datetime import datetime
from typing import Dict, List, Any

API_KEY = "f1dtgv3q9ZlPAwMNWfxTnhsozQB26lKe"
BASE_URL = "https://financialmodelingprep.com/api/v3"

def get_financial_data(ticker: str) -> Dict[str, Any]:
    """獲取公司的所有財務數據"""
    
    # 獲取公司基本信息
    company_profile = requests.get(
        f"{BASE_URL}/profile/{ticker}?apikey={API_KEY}"
    ).json()
    
    # 獲取年度財務報表
    income_statement = requests.get(
        f"{BASE_URL}/income-statement/{ticker}?limit=10&apikey={API_KEY}"
    ).json()
    
    balance_sheet = requests.get(
        f"{BASE_URL}/balance-sheet-statement/{ticker}?limit=10&apikey={API_KEY}"
    ).json()
    
    cash_flow = requests.get(
        f"{BASE_URL}/cash-flow-statement/{ticker}?limit=10&apikey={API_KEY}"
    ).json()
    
    # 獲取關鍵指標
    key_metrics = requests.get(
        f"{BASE_URL}/key-metrics/{ticker}?limit=10&apikey={API_KEY}"
    ).json()
    
    # 整理數據
    financial_data = []
    
    # 使用收入報表作為基準年份
    for year_data in income_statement:
        filing_year = datetime.strptime(year_data['date'], '%Y-%m-%d').year
        
        # 找到對應年份的資產負債表數據
        bs_data = next(
            (item for item in balance_sheet if datetime.strptime(item['date'], '%Y-%m-%d').year == filing_year),
            {}
        )
        
        # 找到對應年份的現金流量表數據
        cf_data = next(
            (item for item in cash_flow if datetime.strptime(item['date'], '%Y-%m-%d').year == filing_year),
            {}
        )
        
        # 找到對應年份的關鍵指標數據
        metrics_data = next(
            (item for item in key_metrics if datetime.strptime(item['date'], '%Y-%m-%d').year == filing_year),
            {}
        )
        
        # 構建符合資料表結構的數據
        filing_data = {
            'ticker': ticker,
            'company_name': company_profile[0]['companyName'] if company_profile else '',
            'filing_type': 'ANNUAL_FINANCIAL',
            'filing_year': filing_year,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data_source': 'fmp',
            'data_quality_score': 95.0,  # 可以根據數據完整性計算
            'data_quality_flag': 'excellent',
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            
            # 收入報表數據
            'revenue': year_data.get('revenue'),
            'gross_profit': year_data.get('grossProfit'),
            'operating_expenses': year_data.get('operatingExpenses'),
            'operating_income': year_data.get('operatingIncome'),
            'income_before_tax': year_data.get('incomeBeforeTax'),
            'eps_basic': year_data.get('eps'),
            'outstanding_shares': metrics_data.get('sharesMilli'),
            'cogs': year_data.get('costOfRevenue'),
            'net_income': year_data.get('netIncome'),
            
            # 現金流量表數據
            'operating_cash_flow': cf_data.get('operatingCashFlow'),
            'free_cash_flow': cf_data.get('freeCashFlow'),
            'cash_flow_investing': cf_data.get('investingCashFlow'),
            'cash_flow_financing': cf_data.get('financingCashFlow'),
            'cash_and_cash_equivalents': cf_data.get('cashAtEndOfPeriod'),
            
            # 資產負債表數據
            'shareholders_equity': bs_data.get('totalStockholdersEquity'),
            'total_assets': bs_data.get('totalAssets'),
            'total_liabilities': bs_data.get('totalLiabilities'),
            'long_term_debt': bs_data.get('longTermDebt'),
            'retained_earnings_balance': bs_data.get('retainedEarnings'),
            'current_assets': bs_data.get('totalCurrentAssets'),
            'current_liabilities': bs_data.get('totalCurrentLiabilities'),
            'current_ratio': metrics_data.get('currentRatio'),
        }
        
        financial_data.append(filing_data)
    
    return financial_data

def main():
    # 測試幾個不同的股票
    test_tickers = ['AAPL', 'MSFT', 'GOOGL']
    
    for ticker in test_tickers:
        print(f"\n正在獲取 {ticker} 的財務數據...")
        try:
            data = get_financial_data(ticker)
            
            # 計算數據完整性
            total_fields = len(data[0].keys()) - 7  # 減去非財務數據的欄位
            for year_data in data:
                non_null_fields = sum(1 for k, v in year_data.items() 
                                   if k not in ['ticker', 'company_name', 'filing_type', 'filing_year', 
                                              'created_at', 'data_source', 'last_updated'] 
                                   and v is not None)
                completeness = (non_null_fields / total_fields) * 100
                
                print(f"\n{year_data['filing_year']} 年數據完整度: {completeness:.1f}%")
                print("可用數據欄位:")
                for key, value in year_data.items():
                    if value is not None and key not in ['ticker', 'company_name', 'filing_type', 
                                                        'filing_year', 'created_at', 'data_source', 
                                                        'last_updated', 'data_quality_score', 
                                                        'data_quality_flag']:
                        print(f"- {key}: {value}")
            
        except Exception as e:
            print(f"獲取 {ticker} 數據時發生錯誤: {str(e)}")

if __name__ == "__main__":
    main()
