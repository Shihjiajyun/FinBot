#!/usr/bin/env python3
"""
驗證股票代號工作流程
確保 ten_k_filings.company_name 中存儲的是股票代號
"""

import mysql.connector
from typing import Dict

def get_db_connection() -> mysql.connector.MySQLConnection:
    """建立資料庫連接"""
    db_config = {
        'host': '43.207.210.147',
        'user': 'myuser',
        'password': '123456789',
        'database': 'finbot_db',
        'charset': 'utf8mb4'
    }
    return mysql.connector.connect(**db_config)

def check_filings_data():
    """檢查 ten_k_filings 表中的數據"""
    print("=== 檢查 ten_k_filings 表 ===")
    
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    
    try:
        query = """
        SELECT id, file_name, company_name, report_date 
        FROM ten_k_filings 
        ORDER BY report_date DESC
        """
        cursor.execute(query)
        filings = cursor.fetchall()
        
        print(f"找到 {len(filings)} 個 10-K 檔案:")
        print("-" * 80)
        for filing in filings:
            print(f"ID: {filing['id']}")
            print(f"檔案名稱: {filing['file_name']}")
            print(f"公司名稱(應為股票代號): {filing['company_name']}")
            print(f"報告日期: {filing['report_date']}")
            print("-" * 80)
            
        return filings
        
    finally:
        cursor.close()
        connection.close()

def check_summary_data():
    """檢查 ten_k_filings_summary 表中的數據"""
    print("\n=== 檢查 ten_k_filings_summary 表 ===")
    
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    
    try:
        query = """
        SELECT id, original_filing_id, file_name, company_name, 
               report_date, processing_status 
        FROM ten_k_filings_summary 
        ORDER BY report_date DESC
        """
        cursor.execute(query)
        summaries = cursor.fetchall()
        
        print(f"找到 {len(summaries)} 個摘要記錄:")
        print("-" * 80)
        for summary in summaries:
            print(f"摘要ID: {summary['id']}")
            print(f"原始檔案ID: {summary['original_filing_id']}")
            print(f"檔案名稱: {summary['file_name']}")
            print(f"公司名稱(應為股票代號): {summary['company_name']}")
            print(f"報告日期: {summary['report_date']}")
            print(f"處理狀態: {summary['processing_status']}")
            print("-" * 80)
            
        return summaries
        
    finally:
        cursor.close()
        connection.close()

def verify_ticker_consistency():
    """驗證兩個表之間的股票代號一致性"""
    print("\n=== 驗證股票代號一致性 ===")
    
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    
    try:
        query = """
        SELECT 
            f.id as filing_id,
            f.company_name as filing_ticker,
            s.id as summary_id,
            s.company_name as summary_ticker,
            f.file_name
        FROM ten_k_filings f
        LEFT JOIN ten_k_filings_summary s ON f.id = s.original_filing_id
        ORDER BY f.report_date DESC
        """
        cursor.execute(query)
        results = cursor.fetchall()
        
        inconsistent_count = 0
        
        for result in results:
            filing_ticker = result['filing_ticker']
            summary_ticker = result['summary_ticker']
            
            if summary_ticker is None:
                print(f"⚠️  檔案 {result['file_name']} 還沒有摘要記錄")
            elif filing_ticker != summary_ticker:
                print(f"❌ 不一致: 檔案={filing_ticker}, 摘要={summary_ticker} ({result['file_name']})")
                inconsistent_count += 1
            else:
                print(f"✅ 一致: {filing_ticker} ({result['file_name']})")
                
        if inconsistent_count == 0:
            print(f"\n🎉 所有記錄的股票代號都一致！")
        else:
            print(f"\n⚠️  發現 {inconsistent_count} 個不一致的記錄")
            
    finally:
        cursor.close()
        connection.close()

def show_available_tickers():
    """顯示可用的股票代號"""
    print("\n=== 可用的股票代號 ===")
    
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    
    try:
        query = """
        SELECT DISTINCT company_name as ticker, COUNT(*) as filing_count
        FROM ten_k_filings 
        GROUP BY company_name
        ORDER BY ticker
        """
        cursor.execute(query)
        tickers = cursor.fetchall()
        
        print("股票代號列表:")
        for ticker_info in tickers:
            ticker = ticker_info['ticker']
            count = ticker_info['filing_count']
            print(f"  - {ticker} ({count} 個檔案)")
            
        print(f"\n總共有 {len(tickers)} 個不同的股票代號")
        
    finally:
        cursor.close()
        connection.close()

def main():
    """主函數"""
    print("🔍 驗證股票代號工作流程")
    print("=" * 60)
    
    try:
        # 檢查原始檔案數據
        filings = check_filings_data()
        
        # 檢查摘要數據
        summaries = check_summary_data()
        
        # 驗證一致性
        verify_ticker_consistency()
        
        # 顯示可用的股票代號
        show_available_tickers()
        
        print("\n✅ 驗證完成！")
        
    except Exception as e:
        print(f"❌ 驗證過程中發生錯誤: {e}")

if __name__ == "__main__":
    main() 