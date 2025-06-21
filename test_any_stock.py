#!/usr/bin/env python3
"""
測試任意股票代號是否能正常工作
"""

from dual_source_analyzer import DualSourceAnalyzer

def test_stock_support(ticker):
    """測試股票代號支持"""
    print(f"\n測試股票: {ticker}")
    print("=" * 50)
    
    analyzer = DualSourceAnalyzer()
    
    # 測試公司名稱獲取
    company_name = analyzer.get_company_name_from_ticker(ticker)
    print(f"公司名稱: {company_name}")
    
    # 測試 Yahoo Finance 數據獲取
    try:
        yahoo_data = analyzer.get_yahoo_finance_data(ticker)
        if yahoo_data:
            print(f"Yahoo Finance 數據: ✅")
            for key, df in yahoo_data.items():
                if df is not None and not df.empty:
                    print(f"  - {key}: {len(df)} 年數據")
        else:
            print(f"Yahoo Finance 數據: ❌")
    except Exception as e:
        print(f"Yahoo Finance 錯誤: {e}")
    
    # 測試 SEC 數據獲取
    try:
        sec_data = analyzer.get_sec_historical_data(ticker)
        if sec_data:
            print(f"SEC 歷史數據: ✅")
            for key, df in sec_data.items():
                if df is not None and not df.empty:
                    print(f"  - {key}: {len(df)} 年數據")
        else:
            print(f"SEC 歷史數據: ❌")
    except Exception as e:
        print(f"SEC 數據錯誤: {e}")

if __name__ == "__main__":
    # 測試不同類型的股票
    test_stocks = [
        "AAPL",  # 已知支持的股票
        "IBM",   # 新添加的股票
        "KO",    # 可口可樂 - 未在預設列表中
        "INTC",  # 英特爾 - 未在預設列表中
        "XYZ123" # 不存在的股票
    ]
    
    for ticker in test_stocks:
        test_stock_support(ticker)
    
    print("\n" + "=" * 50)
    print("測試完成") 