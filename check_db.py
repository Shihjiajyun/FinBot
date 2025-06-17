#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
檢查資料庫結構和內容
"""

import mysql.connector

try:
    conn = mysql.connector.connect(
        host='43.207.210.147',
        user='myuser',
        password='123456789',
        database='finbot_db'
    )
    cursor = conn.cursor()
    
    print("✅ 資料庫連接成功")
    
    # 檢查資料表
    cursor.execute('SHOW TABLES')
    tables = cursor.fetchall()
    print(f"📊 資料表: {[t[0] for t in tables]}")
    
    # 檢查filings表結構
    cursor.execute('DESCRIBE filings')
    structure = cursor.fetchall()
    print(f"\n📋 filings表結構:")
    for col in structure:
        print(f"  {col[0]}: {col[1]} {col[2]} {col[3]} {col[4]} {col[5]}")
    
    # 檢查記錄數
    cursor.execute('SELECT COUNT(*) FROM filings')
    count = cursor.fetchone()[0]
    print(f"\n📊 filings總記錄數: {count}")
    
    if count > 0:
        # 檢查前幾條記錄
        cursor.execute('SELECT id, company_name, filing_type, accession_number, LENGTH(item_7_content), LENGTH(item_8_content), file_url FROM filings LIMIT 5')
        samples = cursor.fetchall()
        print(f"\n📄 樣本記錄:")
        for sample in samples:
            print(f"  ID{sample[0]}: {sample[1]} - {sample[2]} [{sample[3]}]")
            print(f"    Item7: {sample[4]}字符, Item8: {sample[5]}字符")
            print(f"    URL: {sample[6]}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ 錯誤: {e}") 