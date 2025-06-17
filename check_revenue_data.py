#!/usr/bin/env python3
import mysql.connector
from mysql.connector import Error

def check_revenue_data():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='finbot_db',
            user='root',
            password=''
        )
        
        cursor = connection.cursor()
        
        # 檢查 total_revenue 欄位的數據
        cursor.execute('''
            SELECT company_name, filing_type, filing_year, total_revenue, net_income
            FROM filings 
            WHERE company_name LIKE '%Apple%' 
            AND (total_revenue IS NOT NULL AND total_revenue > 0)
            ORDER BY filing_year DESC, report_date DESC
            LIMIT 10
        ''')
        
        results = cursor.fetchall()
        print('🔍 Apple 的營收數據:')
        print('公司名稱 | 類型 | 年份 | 營收 | 淨利')
        print('-' * 60)
        
        for row in results:
            company, filing_type, year, revenue, income = row
            revenue_str = f'${revenue/1000000:.0f}M' if revenue else 'N/A'
            income_str = f'${income/1000000:.0f}M' if income else 'N/A'
            print(f'{company[:15]} | {filing_type} | {year} | {revenue_str} | {income_str}')
            
        if not results:
            print('⚠️  沒有找到有效的營收數據')
            
            # 檢查是否有 total_revenue 欄位
            cursor.execute('DESCRIBE filings')
            columns = cursor.fetchall()
            print('\n📋 filings 表相關欄位:')
            for col in columns:
                if 'revenue' in col[0] or 'income' in col[0] or 'gross' in col[0]:
                    print(f'  {col[0]}: {col[1]}')
                    
            # 檢查所有 Apple 記錄的 total_revenue 狀況
            cursor.execute('''
                SELECT COUNT(*) as total_count,
                       SUM(CASE WHEN total_revenue IS NOT NULL THEN 1 ELSE 0 END) as has_revenue,
                       SUM(CASE WHEN total_revenue > 0 THEN 1 ELSE 0 END) as positive_revenue
                FROM filings 
                WHERE company_name LIKE '%Apple%'
            ''')
            
            stats = cursor.fetchone()
            print(f'\n📊 Apple 記錄統計:')
            print(f'  總記錄數: {stats[0]}')
            print(f'  有營收欄位: {stats[1]}')
            print(f'  營收 > 0: {stats[2]}')
        
    except Error as e:
        print(f'❌ 資料庫錯誤: {e}')
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    check_revenue_data() 