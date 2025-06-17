#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
檢查已處理的 AAPL 財務數據
"""

import mysql.connector

# 資料庫配置
DB_CONFIG = {
    'host': '43.207.210.147',
    'database': 'finbot_db',
    'user': 'myuser',
    'password': '123456789',
    'charset': 'utf8mb4'
}

def check_processed_data():
    """檢查已處理的數據"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("✅ 資料庫連接成功")
        
        # 檢查 AAPL 記錄數
        cursor.execute("SELECT COUNT(*) FROM filings WHERE company_name LIKE '%Apple%'")
        apple_count = cursor.fetchone()[0]
        print(f"📊 Apple 相關記錄總數: {apple_count}")
        
        # 檢查最新記錄
        cursor.execute("""
            SELECT company_name, filing_type, filing_year, report_date, 
                   total_revenue, gross_profit, net_income, total_assets, 
                   gross_margin, operating_margin, net_income_margin, roe, roa
            FROM filings 
            WHERE company_name LIKE '%Apple%' 
            AND total_revenue IS NOT NULL
            ORDER BY report_date DESC 
            LIMIT 5
        """)
        
        results = cursor.fetchall()
        
        if results:
            print(f"\n💰 最新的 {len(results)} 筆有財務數據的記錄:")
            print("-" * 120)
            print(f"{'公司':<15} {'類型':<8} {'年份':<6} {'報告日期':<12} {'營收(M)':<10} {'毛利率%':<8} {'淨利率%':<8} {'ROE%':<8} {'ROA%':<8}")
            print("-" * 120)
            
            for row in results:
                company = row[0][:15] if row[0] else "N/A"
                filing_type = row[1] if row[1] else "N/A"
                filing_year = row[2] if row[2] else "N/A"
                report_date = str(row[3]) if row[3] else "N/A"
                revenue = f"{row[4]/1000000:.0f}" if row[4] else "N/A"
                gross_margin = f"{row[8]:.1f}" if row[8] else "N/A"
                net_margin = f"{row[10]:.1f}" if row[10] else "N/A"
                roe = f"{row[11]:.1f}" if row[11] else "N/A"
                roa = f"{row[12]:.1f}" if row[12] else "N/A"
                
                print(f"{company:<15} {filing_type:<8} {filing_year:<6} {report_date:<12} {revenue:<10} {gross_margin:<8} {net_margin:<8} {roe:<8} {roa:<8}")
        
        # 檢查各年份的記錄數
        cursor.execute("""
            SELECT filing_year, filing_type, COUNT(*) as count
            FROM filings 
            WHERE company_name LIKE '%Apple%' 
            GROUP BY filing_year, filing_type
            ORDER BY filing_year DESC, filing_type
        """)
        
        year_results = cursor.fetchall()
        
        if year_results:
            print(f"\n📅 各年份記錄統計:")
            print("-" * 40)
            print(f"{'年份':<8} {'類型':<8} {'數量':<8}")
            print("-" * 40)
            
            for row in year_results:
                year = row[0] if row[0] else "N/A"
                filing_type = row[1] if row[1] else "N/A"
                count = row[2]
                print(f"{year:<8} {filing_type:<8} {count:<8}")
        
        # 檢查有多少記錄包含財務指標
        cursor.execute("""
            SELECT 
                COUNT(*) as total_records,
                COUNT(total_revenue) as has_revenue,
                COUNT(gross_margin) as has_gross_margin,
                COUNT(roe) as has_roe,
                COUNT(current_ratio) as has_current_ratio
            FROM filings 
            WHERE company_name LIKE '%Apple%'
        """)
        
        metrics_result = cursor.fetchone()
        
        if metrics_result:
            print(f"\n🔍 財務指標覆蓋率:")
            print("-" * 40)
            print(f"總記錄數: {metrics_result[0]}")
            print(f"有營收數據: {metrics_result[1]} ({metrics_result[1]/metrics_result[0]*100:.1f}%)")
            print(f"有毛利率: {metrics_result[2]} ({metrics_result[2]/metrics_result[0]*100:.1f}%)")
            print(f"有ROE: {metrics_result[3]} ({metrics_result[3]/metrics_result[0]*100:.1f}%)")
            print(f"有流動比率: {metrics_result[4]} ({metrics_result[4]/metrics_result[0]*100:.1f}%)")
        
    except mysql.connector.Error as e:
        print(f"❌ 資料庫錯誤: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    check_processed_data() 