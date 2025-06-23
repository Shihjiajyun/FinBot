#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import mysql.connector

db_config = {
    'host': '43.207.210.147',
    'user': 'myuser', 
    'password': '123456789',
    'database': 'finbot_db',
    'charset': 'utf8mb4'
}

try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    
    # 檢查NFLX摘要結果
    cursor.execute('SELECT * FROM ten_k_filings_summary WHERE original_filing_id = 62')
    result = cursor.fetchone()
    
    if result:
        print('🎉 NFLX摘要完成！摘要統計：')
        print(f'   ✅ 檔案ID: {result[1]}')
        print(f'   ✅ 公司名稱: {result[3]}')
        print(f'   ✅ 報告日期: {result[4]}')
        print(f'   ✅ 使用模型: {result[5]}')
        print(f'   ✅ 完成時間: {result[6]}')
        print(f'   ✅ 處理狀態: {result[7]}')
        print(f'   ✅ 已處理項目: {result[29]}/{result[30]}')
        print()
        
        # 檢查哪些項目有摘要
        item_fields = [
            ('item_1_summary', 'Business'),
            ('item_1a_summary', 'Risk Factors'),
            ('item_1b_summary', 'Unresolved Staff Comments'),
            ('item_2_summary', 'Properties'),
            ('item_3_summary', 'Legal Proceedings'),
            ('item_5_summary', 'Market for Stock'),
            ('item_7a_summary', 'Market Risk'),
            ('item_8_summary', 'Financial Statements'),
            ('item_9a_summary', 'Controls and Procedures'),
            ('item_9b_summary', 'Other Information'),
            ('item_10_summary', 'Directors and Officers'),
            ('item_11_summary', 'Executive Compensation'),
            ('item_13_summary', 'Relationships and Transactions'),
            ('item_16_summary', 'Form 10-K Summary')
        ]
        
        print('📊 各項目摘要狀況：')
        summary_count = 0
        for i, (field_name, title) in enumerate(item_fields):
            field_index = 9 + i  # 摘要欄位從第9個位置開始
            if field_index < len(result) and result[field_index]:
                summary_length = len(result[field_index])
                print(f'   ✅ {field_name.replace("_summary", "").upper()}: {title} ({summary_length} 字符)')
                summary_count += 1
            else:
                print(f'   ❌ {field_name.replace("_summary", "").upper()}: {title} (無摘要)')
        
        print(f'\n總計: {summary_count} 個項目有摘要')
        
        # 顯示第一個項目的摘要示例
        if result[9]:  # item_1_summary
            print('\n📄 Item 1 (Business) 摘要示例:')
            print('=' * 50)
            print(result[9][:500] + '...' if len(result[9]) > 500 else result[9])
            print('=' * 50)
    else:
        print('找不到摘要記錄')
        
except Exception as e:
    print(f'錯誤: {e}')
finally:
    if 'conn' in locals():
        conn.close() 