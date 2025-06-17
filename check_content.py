#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
檢查資料庫中財報內容統計
"""

import mysql.connector

def check_content_stats():
    """檢查內容統計"""
    try:
        # 連接資料庫
        conn = mysql.connector.connect(
            host='43.207.210.147',
            user='myuser',
            password='123456789',
            database='finbot_db'
        )
        cursor = conn.cursor()
        
        # 統計各文件類型
        sql = """
        SELECT 
            filing_type, 
            COUNT(*) as total,
            COUNT(CASE WHEN item_7_content != '' THEN 1 END) as has_item7,
            COUNT(CASE WHEN item_8_content != '' THEN 1 END) as has_item8,
            COUNT(CASE WHEN file_url IS NOT NULL THEN 1 END) as has_url
        FROM filings 
        GROUP BY filing_type
        ORDER BY total DESC
        """
        
        cursor.execute(sql)
        results = cursor.fetchall()
        
        print("📊 財報內容統計:")
        print("=" * 70)
        print(f"{'類型':<8} {'總數':<6} {'Item7':<6} {'Item8':<6} {'URL':<6} {'Item7%':<8} {'Item8%':<8}")
        print("=" * 70)
        
        for row in results:
            filing_type, total, has_item7, has_item8, has_url = row
            item7_pct = (has_item7 / total * 100) if total > 0 else 0
            item8_pct = (has_item8 / total * 100) if total > 0 else 0
            
            print(f"{filing_type:<8} {total:<6} {has_item7:<6} {has_item8:<6} {has_url:<6} {item7_pct:<8.1f} {item8_pct:<8.1f}")
        
        # 檢查一些具體例子
        print("\n📄 具體例子 (前5個不同類型):")
        print("=" * 70)
        
        for filing_type in ['10-K', '10-Q', '8-K', '4', '13F-HR']:
            sql = """
            SELECT accession_number, company_name, 
                   LENGTH(item_7_content) as item7_len, 
                   LENGTH(item_8_content) as item8_len
            FROM filings 
            WHERE filing_type = %s 
            LIMIT 2
            """
            cursor.execute(sql, (filing_type,))
            examples = cursor.fetchall()
            
            if examples:
                print(f"\n{filing_type} 範例:")
                for acc, company, item7_len, item8_len in examples:
                    print(f"  {acc}: {company}")
                    print(f"    Item7: {item7_len} 字符, Item8: {item8_len} 字符")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ 錯誤: {e}")

if __name__ == "__main__":
    check_content_stats() 