#!/usr/bin/env python3
import mysql.connector

# 資料庫配置
DB_CONFIG = {
    'host': '43.207.210.147',
    'database': 'finbot_db',
    'user': 'myuser',
    'password': '123456789',
    'charset': 'utf8mb4'
}

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # 總數統計
    cursor.execute('SELECT COUNT(*) FROM filings')
    total_count = cursor.fetchone()[0]
    print(f'🗂️ 已處理財報總數: {total_count}')
    
    print("\n📊 各公司財報統計:")
    cursor.execute('''
        SELECT company_name, filing_type, COUNT(*) as count 
        FROM filings 
        GROUP BY company_name, filing_type 
        ORDER BY company_name, filing_type
    ''')
    
    current_company = None
    for row in cursor.fetchall():
        company, filing_type, count = row
        if company != current_company:
            if current_company is not None:
                print()
            print(f"🏢 {company}:")
            current_company = company
        print(f"   📄 {filing_type}: {count}份")
    
    # 最新處理的文件
    print("\n📅 最近處理的財報:")
    cursor.execute('''
        SELECT company_name, filing_type, report_date, accession_number 
        FROM filings 
        ORDER BY created_at DESC 
        LIMIT 5
    ''')
    
    for row in cursor.fetchall():
        company, filing_type, report_date, accession = row
        print(f"   {company} - {filing_type} ({report_date}) [{accession}]")
    
    conn.close()
    
except Exception as e:
    print(f"❌ 錯誤: {e}") 