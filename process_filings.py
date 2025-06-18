#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
處理特定股票的財報文件並存儲到資料庫
用法：python process_filings.py AAPL
"""

import os
import re
import sys
import json
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

class FilingProcessor:
    def __init__(self):
        self.db_connection = None
        self.connect_db()
        
    def connect_db(self):
        """連接資料庫"""
        try:
            self.db_connection = mysql.connector.connect(**DB_CONFIG)
            print("[SUCCESS] 資料庫連接成功")
        except mysql.connector.Error as err:
            print(f"[ERROR] 資料庫連接失敗: {err}")
            sys.exit(1)
    
    def extract_filing_metadata(self, file_path):
        """從財報文件中提取元數據"""
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
                    if year_suffix >= 17:
                        result['filing_year'] = 2000 + year_suffix
                    else:
                        result['filing_year'] = 2000 + year_suffix
                        
        except Exception as e:
            print(f"[ERROR] 解析文件元數據失敗 {file_path}: {e}")
            
        return result
    
    def extract_form4_tables(self, content):
        """提取Form 4的交易表格"""
        tables = {}
        
        try:
            # 提取 nonDerivativeTable
            non_derivative_pattern = r'<nonDerivativeTable>(.*?)</nonDerivativeTable>'
            non_derivative_match = re.search(non_derivative_pattern, content, re.DOTALL | re.IGNORECASE)
            if non_derivative_match:
                tables['non_derivative_table'] = non_derivative_match.group(1).strip()
            
            # 提取 derivativeTable
            derivative_pattern = r'<derivativeTable>(.*?)</derivativeTable>'
            derivative_match = re.search(derivative_pattern, content, re.DOTALL | re.IGNORECASE)
            if derivative_match:
                tables['derivative_table'] = derivative_match.group(1).strip()
                        
        except Exception as e:
            print(f"[WARN] Form 4表格提取警告: {e}")
            
        return tables
    
    def extract_10k_items(self, content):
        """提取10K財報的特定Items"""
        items = {}
        
        try:
            # 定義要抓取的Items及其順序
            target_items = [
                ('item_1', r'Item&#160;1\.'),
                ('item_1a', r'Item&#160;1A\.'),
                ('item_2', r'Item&#160;2\.'),
                ('item_7', r'Item&#160;7\.'),
                ('item_7a', r'Item&#160;7A\.'),
                ('item_8', r'Item&#160;8\.')
            ]
            
            # 完整的Items順序用於確定結束點
            all_items_pattern = [
                r'Item&#160;1\.',
                r'Item&#160;1A\.',
                r'Item&#160;1B\.',
                r'Item&#160;1C\.',
                r'Item&#160;2\.',
                r'Item&#160;3\.',
                r'Item&#160;4\.',
                r'Item&#160;7\.',
                r'Item&#160;7A\.',
                r'Item&#160;8\.',
                r'Item&#160;9\.',
                r'Item&#160;9A\.',
                r'Item&#160;9B\.',
                r'Item&#160;9C\.'
            ]
            
            for item_key, item_pattern in target_items:
                print(f"   [SEARCH] 搜尋 {item_key}...")
                
                # 找到所有匹配的位置
                matches = list(re.finditer(item_pattern, content, re.IGNORECASE))
                
                if matches:
                    # 如果找到多個，使用最後一個
                    start_match = matches[-1]
                    start_pos = start_match.end()
                    
                    # 找到下一個Item的位置作為結束點
                    end_pos = len(content)
                    current_item_index = None
                    
                    # 找到當前item在完整列表中的位置
                    for i, pattern in enumerate(all_items_pattern):
                        if pattern == item_pattern:
                            current_item_index = i
                            break
                    
                    if current_item_index is not None:
                        # 搜尋後續的Items作為結束點
                        for next_pattern in all_items_pattern[current_item_index + 1:]:
                            next_matches = list(re.finditer(next_pattern, content[start_pos:], re.IGNORECASE))
                            if next_matches:
                                end_pos = start_pos + next_matches[0].start()
                                break
                    
                    # 提取內容
                    extracted_content = content[start_pos:end_pos].strip()
                    
                    # 限制長度並清理內容
                    if len(extracted_content) > 100000:  # 限制長度
                        extracted_content = extracted_content[:100000] + "... [內容過長，已截斷]"
                    
                    # 移除過多的空白字符
                    extracted_content = re.sub(r'\s+', ' ', extracted_content)
                    
                    items[item_key + '_content'] = extracted_content
                    print(f"   [SUCCESS] 成功提取 {item_key}: {len(extracted_content)} 字符")
                else:
                    print(f"   [WARN] 未找到 {item_key}")
                
        except Exception as e:
            print(f"[WARN] 10K Items提取警告: {e}")
            
        return items
    
    def process_filing_file(self, file_path):
        """處理單個財報文件"""
        print(f"[PROCESS] 處理文件: {file_path}")
        
        # 提取元數據
        metadata = self.extract_filing_metadata(file_path)
        if not metadata.get('accession_number'):
            print(f"[WARN] 跳過文件（無法提取元數據）: {file_path}")
            return False

        # 跳過某些文件類型
        filing_type = metadata.get('filing_type', '')
        if filing_type in ['10-Q', '8-K']:
            print(f"[WARN] 跳過文件類型 {filing_type}: {file_path}")
            return False
        
        # 檢查是否已存在
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT id FROM filings WHERE accession_number = %s", 
                      (metadata['accession_number'],))
        if cursor.fetchone():
            print(f"[WARN] 文件已存在，跳過: {metadata['accession_number']}")
            cursor.close()
            return False
        
        # 讀取完整內容
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            print(f"[ERROR] 讀取文件內容失敗: {e}")
            cursor.close()
            return False
        
        # 根據文件類型提取不同內容
        extracted_data = {}
        
        if filing_type == '4':
            # Form 4 - 提取交易表格
            print(f"   [EXTRACT] 處理Form 4交易數據...")
            tables = self.extract_form4_tables(content)
            extracted_data.update(tables)
            
        elif filing_type == '10-K':
            # 10-K - 提取特定Items
            print(f"   [EXTRACT] 處理10-K Items...")
            items = self.extract_10k_items(content)
            extracted_data.update(items)
            
        elif filing_type == '13F-HR':
            # 13F-HR - 存儲完整內容
            print(f"   [EXTRACT] 處理13F-HR機構持股數據...")
            extracted_data['form_13f_hr_content'] = content
        
        # 插入資料庫
        try:
            file_url = self.generate_file_url(str(file_path))
            
            sql = """
            INSERT INTO filings (
                cik, company_name, filing_type, filing_year, accession_number, 
                report_date, filed_date, filepath, file_url, content_summary,
                item_1_content, item_1a_content, item_2_content, 
                item_7_content, item_7a_content, item_8_content,
                non_derivative_table, derivative_table, form_13f_hr_content
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                f"公司: {metadata.get('company_name', '')}, 類型: {metadata.get('filing_type', '')}, 年份: {metadata.get('filing_year', 'N/A')}",
                # 10K Items
                extracted_data.get('item_1_content', ''),
                extracted_data.get('item_1a_content', ''),
                extracted_data.get('item_2_content', ''),
                extracted_data.get('item_7_content', ''),
                extracted_data.get('item_7a_content', ''),
                extracted_data.get('item_8_content', ''),
                # Form 4 Tables
                extracted_data.get('non_derivative_table', ''),
                extracted_data.get('derivative_table', ''),
                # 13F-HR Content
                extracted_data.get('form_13f_hr_content', '')
            )
            
            cursor.execute(sql, values)
            self.db_connection.commit()
            print(f"[SUCCESS] 成功保存: {metadata['company_name']} - {metadata['filing_type']}")
            cursor.close()
            return True
            
        except mysql.connector.Error as err:
            print(f"[ERROR] 資料庫插入失敗: {err}")
            cursor.close()
            return False
    
    def process_stock_directory(self, stock_symbol, downloads_path="./downloads"):
        """處理特定股票的資料夾"""
        downloads_path = Path(downloads_path)
        stock_path = downloads_path / stock_symbol.upper()
        
        if not stock_path.exists():
            print(f"[ERROR] {stock_symbol}目錄不存在: {stock_path}")
            return False
        
        print(f"[SCAN] 掃描{stock_symbol}目錄: {stock_path}")
        
        # 處理Form 4、10-K和13F-HR文件
        target_folders = ["4", "10-K", "13F-HR"]
        processed = 0
        
        for folder in target_folders:
            folder_path = stock_path / folder
            if folder_path.exists():
                print(f"\n[FOLDER] 處理 {folder} 資料夾...")
                txt_files = list(folder_path.glob("*.txt"))
                print(f"   [INFO] 找到 {len(txt_files)} 個文件")
                
                for file_path in txt_files:
                    if self.process_filing_file(file_path):
                        processed += 1
            else:
                print(f"[WARN] 資料夾不存在: {folder_path}")
                
        print(f"[COMPLETE] 處理完成! 成功處理 {processed} 個文件")
        return processed > 0
    
    def generate_file_url(self, filepath):
        """生成文件的URL"""
        # 將本地路徑轉換為Web URL
        web_path = filepath.replace('\\', '/')
        if 'downloads/' in web_path:
            if not web_path.startswith('downloads/'):
                web_path = 'downloads/' + web_path.split('downloads/')[-1]
        return f"https://shinbwei.com/FinBot/{web_path}"
    
    def close(self):
        """關閉資料庫連接"""
        if self.db_connection:
            self.db_connection.close()

def main():
    """主函數 - 命令行調用"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("python process_filings.py <股票代號>")
        print("例如:")
        print("python process_filings.py AAPL")
        return False
    
    stock_symbol = sys.argv[1].upper()
    
    processor = FilingProcessor()
    
    try:
        success = processor.process_stock_directory(stock_symbol)
        return success
    finally:
        processor.close()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 