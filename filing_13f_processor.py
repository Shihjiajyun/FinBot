#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FinBot 13F-HR 財報處理模組
專門用於處理 SEC 13F-HR 表單文件
將完整內容存入資料庫
"""

import os
import re
import sys
import mysql.connector
from pathlib import Path
from datetime import datetime

# 資料庫配置
DB_CONFIG = {
    'host': '43.207.210.147',
    'database': 'finbot_db',
    'user': 'myuser',
    'password': '123456789',
    'charset': 'utf8mb4'
}

class Filing13FProcessor:
    def __init__(self):
        self.db_connection = None
        self.connect_db()
        
    def connect_db(self):
        """連接資料庫"""
        try:
            self.db_connection = mysql.connector.connect(**DB_CONFIG)
            print("✅ 資料庫連接成功")
        except mysql.connector.Error as err:
            print(f"❌ 資料庫連接失敗: {err}")
            sys.exit(1)
    
    def extract_filing_metadata(self, file_path):
        """從13F-HR文件中提取元數據"""
        result = {}
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(10000)  # 只讀前10000個字符
                
                # 提取各種元數據
                patterns = {
                    'accession_number': r'ACCESSION NUMBER:\s*(.+)',
                    'filing_type': r'CONFORMED SUBMISSION TYPE:\s*(.+)',
                    'report_date': r'CONFORMED PERIOD OF REPORT:\s*(\d{8})',
                    'filed_date': r'FILED AS OF DATE:\s*(\d{8})',
                    'company_name': r'COMPANY CONFORMED NAME:\s*(.+)',
                    'cik': r'CENTRAL INDEX KEY:\s*(\d+)'
                }
                
                for key, pattern in patterns.items():
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        if key in ['report_date', 'filed_date'] and len(value) == 8:
                            # 轉換日期格式 YYYYMMDD -> YYYY-MM-DD
                            value = f"{value[:4]}-{value[4:6]}-{value[6:8]}"
                        result[key] = value
                
                # 從檔案名稱中提取年份
                filename = Path(file_path).name
                year_match = re.search(r'-(\d{2})-', filename)
                if year_match:
                    year_suffix = int(year_match.group(1))
                    # 假設21-99是20xx年，00-20是20xx年
                    if year_suffix >= 21:
                        result['filing_year'] = 2000 + year_suffix
                    else:
                        result['filing_year'] = 2000 + year_suffix
                        
        except Exception as e:
            print(f"❌ 解析文件元數據失敗 {file_path}: {e}")
            
        return result
    
    def process_13f_filing_file(self, file_path):
        """處理單個13F-HR文件"""
        print(f"📄 處理13F-HR文件: {file_path}")
        
        # 提取元數據
        metadata = self.extract_filing_metadata(file_path)
        if not metadata.get('accession_number'):
            print(f"⚠️ 跳過文件（無法提取元數據）: {file_path}")
            return False
        
        # 檢查是否已存在
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT id FROM filings WHERE accession_number = %s", 
                      (metadata['accession_number'],))
        if cursor.fetchone():
            print(f"⚠️ 文件已存在，跳過: {metadata['accession_number']}")
            cursor.close()
            return False
        
        # 讀取完整內容
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                full_content = f.read()
        except Exception as e:
            print(f"❌ 讀取文件內容失敗: {e}")
            cursor.close()
            return False
        
        # 插入資料庫
        try:
            file_url = self.generate_file_url(str(file_path))
            
            sql = """
            INSERT INTO filings (
                cik, company_name, filing_type, filing_year, accession_number, 
                report_date, filed_date, filepath, file_url, content_summary,
                form_13f_hr_content
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                metadata.get('cik', ''),
                metadata.get('company_name', ''),
                metadata.get('filing_type', ''),
                metadata.get('filing_year'),
                metadata.get('accession_number', ''),
                metadata.get('report_date'),
                metadata.get('filed_date'),
                str(file_path),
                file_url,
                f"13F-HR Holdings Report - 公司: {metadata.get('company_name', '')}, 年份: {metadata.get('filing_year', 'N/A')}, 報告日期: {metadata.get('report_date', 'N/A')}",
                full_content  # 存儲完整的13F-HR文件內容
            )
            
            cursor.execute(sql, values)
            self.db_connection.commit()
            print(f"✅ 成功保存13F-HR: {metadata['company_name']} - {metadata.get('report_date', 'N/A')}")
            print(f"   📊 文件大小: {len(full_content):,} 字符")
            cursor.close()
            return True
            
        except mysql.connector.Error as err:
            print(f"❌ 資料庫插入失敗: {err}")
            cursor.close()
            return False
    
    def process_amzn_13f_directory(self, downloads_path="./downloads"):
        """處理AMZN的13F-HR資料夾"""
        downloads_path = Path(downloads_path)
        amzn_13f_path = downloads_path / "AMZN" / "13F-HR"
        
        if not amzn_13f_path.exists():
            print(f"❌ AMZN 13F-HR目錄不存在: {amzn_13f_path}")
            return
        
        print(f"🔍 掃描AMZN 13F-HR目錄: {amzn_13f_path}")
        
        # 獲取所有txt文件
        txt_files = list(amzn_13f_path.glob("*.txt"))
        print(f"📊 找到 {len(txt_files)} 個13F-HR文件")
        
        processed = 0
        
        for file_path in txt_files:
            if self.process_13f_filing_file(file_path):
                processed += 1
                
        print(f"🎉 13F-HR處理完成! 成功處理 {processed} 個文件")
        
        # 顯示處理結果統計
        self.show_13f_statistics()
    
    def show_13f_statistics(self):
        """顯示13F-HR處理統計信息"""
        cursor = self.db_connection.cursor()
        
        try:
            # 統計13F-HR文件數量
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_count,
                    COUNT(DISTINCT filing_year) as year_count,
                    MIN(report_date) as earliest_date,
                    MAX(report_date) as latest_date
                FROM filings 
                WHERE filing_type = '13F-HR' AND company_name LIKE '%AMAZON%'
            """)
            
            result = cursor.fetchone()
            if result:
                print(f"\n📈 AMAZON 13F-HR統計:")
                print(f"   總文件數: {result[0]}")
                print(f"   涵蓋年份: {result[1]} 個年份")
                print(f"   最早報告: {result[2] if result[2] else 'N/A'}")
                print(f"   最新報告: {result[3] if result[3] else 'N/A'}")
                
            # 按年份統計
            cursor.execute("""
                SELECT filing_year, COUNT(*) as count
                FROM filings 
                WHERE filing_type = '13F-HR' AND company_name LIKE '%AMAZON%'
                GROUP BY filing_year
                ORDER BY filing_year DESC
            """)
            
            year_results = cursor.fetchall()
            if year_results:
                print(f"\n📅 按年份統計:")
                for year, count in year_results:
                    print(f"   {year}: {count} 個文件")
                    
        except mysql.connector.Error as err:
            print(f"❌ 統計查詢失敗: {err}")
        finally:
            cursor.close()
    
    def close(self):
        """關閉資料庫連接"""
        if self.db_connection:
            self.db_connection.close()

    def generate_file_url(self, filepath):
        """生成文件的URL"""
        # 將本地路徑轉換為Web URL
        web_path = filepath.replace('\\', '/')
        if 'downloads/' in web_path:
            # 確保包含 downloads/ 前綴
            if not web_path.startswith('downloads/'):
                web_path = 'downloads/' + web_path.split('downloads/')[-1]
        return f"https://shinbwei.com/FinBot/{web_path}"

def main():
    """主函數"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("python filing_13f_processor.py process           # 處理AMZN的13F-HR文件")
        print("python filing_13f_processor.py stats             # 顯示13F-HR統計")
        return
    
    processor = Filing13FProcessor()
    
    try:
        command = sys.argv[1]
        
        if command == "process":
            # 處理AMZN的13F-HR文件
            processor.process_amzn_13f_directory()
        elif command == "stats":
            # 顯示統計信息
            processor.show_13f_statistics()
        else:
            print("❌ 無效的命令，請使用 'process' 或 'stats'")
            
    finally:
        processor.close()

if __name__ == "__main__":
    main() 