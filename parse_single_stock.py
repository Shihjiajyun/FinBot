#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
單一股票 10-K Filing Items Parser
基於 parse_10k_items.py，專門處理單一股票的財報解析
優化版本：增加性能監控和快速處理模式
"""

import os
import re
import sys
import mysql.connector
from mysql.connector import Error
from datetime import datetime
from pathlib import Path
import hashlib
import time

class SingleStockTenKParser:
    def __init__(self, ticker, db_config=None):
        self.ticker = ticker.upper()
        self.start_time = time.time()
        
        # 資料庫配置
        self.db_config = db_config or {
            'host': '43.207.210.147',
            'database': 'finbot_db',
            'user': 'myuser',
            'password': '123456789',
            'charset': 'utf8mb4'
        }
        
        self.db_connection = None
        
        # 編譯正則表達式以提高性能
        self.compiled_patterns = {}
        raw_patterns = {
            'item_1': r'Item\s+1\.\s*(?:Business|BUSINESS|$)',
            'item_1a': r'Item\s+1A\.\s*(?:Risk Factors|RISK FACTORS|$)',
            'item_1b': r'Item\s+1B\.\s*(?:Unresolved Staff Comments|UNRESOLVED STAFF COMMENTS|$)',
            'item_2': r'Item\s+2\.\s*(?:Properties|PROPERTIES|$)',
            'item_3': r'Item\s+3\.\s*(?:Legal Proceedings|LEGAL PROCEEDINGS|$)',
            'item_4': r'Item\s+4\.\s*(?:Mine Safety|MINE SAFETY|$)',
            'item_5': r'Item\s+5\.\s*(?:Market for Registrant|MARKET FOR REGISTRANT|$)',
            'item_6': r'Item\s+6\.\s*(?:Selected Financial Data|SELECTED FINANCIAL DATA|$)',
            'item_7': r'Item\s+7\.\s*(?:Management|MANAGEMENT|$)',
            'item_7a': r'Item\s+7A\.\s*(?:Quantitative and Qualitative|QUANTITATIVE AND QUALITATIVE|$)',
            'item_8': r'Item\s+8\.\s*(?:Financial Statements|FINANCIAL STATEMENTS|$)',
            'item_9': r'Item\s+9\.\s*(?:Changes in and Disagreements|CHANGES IN AND DISAGREEMENTS|$)',
            'item_9a': r'Item\s+9A\.\s*(?:Controls and Procedures|CONTROLS AND PROCEDURES|$)',
            'item_9b': r'Item\s+9B\.\s*(?:Other Information|OTHER INFORMATION|$)',
            'item_10': r'Item\s+10\.\s*(?:Directors|DIRECTORS|$)',
            'item_11': r'Item\s+11\.\s*(?:Executive Compensation|EXECUTIVE COMPENSATION|$)',
            'item_12': r'Item\s+12\.\s*(?:Security Ownership|SECURITY OWNERSHIP|$)',
            'item_13': r'Item\s+13\.\s*(?:Certain Relationships|CERTAIN RELATIONSHIPS|$)',
            'item_14': r'Item\s+14\.\s*(?:Principal Accountant|PRINCIPAL ACCOUNTANT|$)',
            'item_15': r'Item\s+15\.\s*(?:Exhibits|EXHIBITS|$)',
            'item_16': r'Item\s+16\.\s*(?:Form 10-K Summary|FORM 10-K SUMMARY|$)',
            'appendix': r'(?:INDEX\s+TO\s+FINANCIAL\s+STATEMENTS|APPENDIX|CONSOLIDATED\s+FINANCIAL\s+STATEMENTS)'
        }
        
        # 預編譯正則表達式
        print("🚀 預編譯正則表達式以提高性能...")
        for key, pattern in raw_patterns.items():
            self.compiled_patterns[key] = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        
        # 常用的清理模式也預編譯
        self.html_style_pattern = re.compile(r'<style[^>]*>.*?</style>', re.DOTALL | re.IGNORECASE)
        self.html_script_pattern = re.compile(r'<script[^>]*>.*?</script>', re.DOTALL | re.IGNORECASE)
        self.html_tag_pattern = re.compile(r'<[^>]+>')
        self.html_entity_pattern = re.compile(r'&#\d+;')
        self.whitespace_pattern = re.compile(r'\s+')
        
        print(f"✅ 初始化完成 ({self.ticker})")

    def log_performance(self, stage, duration=None):
        """記錄性能資訊"""
        current_time = time.time()
        total_elapsed = current_time - self.start_time
        if duration is None:
            print(f"⏱️ [{stage}] 總耗時: {total_elapsed:.2f}秒")
        else:
            print(f"⏱️ [{stage}] 本階段: {duration:.2f}秒, 總耗時: {total_elapsed:.2f}秒")

    def connect_database(self):
        """連接資料庫"""
        try:
            self.db_connection = mysql.connector.connect(**self.db_config)
            if self.db_connection.is_connected():
                print("✅ 資料庫連接成功")
                return True
        except Error as e:
            print(f"❌ 資料庫連接失敗: {e}")
            return False

    def disconnect_database(self):
        """斷開資料庫連接"""
        if self.db_connection and self.db_connection.is_connected():
            self.db_connection.close()
            print("✅ 資料庫連接已關閉")

    def extract_filing_metadata(self, content):
        """提取10-K報告的基本資訊"""
        metadata = {}
        
        # 提取文件編號
        doc_number_pattern = r'DOCUMENT\s+(\d{10}-\d{2}-\d{6})'
        doc_match = re.search(doc_number_pattern, content)
        metadata['document_number'] = doc_match.group(1) if doc_match else None
        
        # 使用股票代號作為公司名稱
        metadata['company_name'] = self.ticker
        
        # 提取CIK
        cik_pattern = r'CENTRAL INDEX KEY:\s+(\d+)'
        cik_match = re.search(cik_pattern, content)
        metadata['cik'] = cik_match.group(1) if cik_match else None
        
        # 提取報告日期
        date_pattern = r'CONFORMED PERIOD OF REPORT:\s+(\d{8})'
        date_match = re.search(date_pattern, content)
        if date_match:
            date_str = date_match.group(1)
            metadata['report_date'] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        else:
            metadata['report_date'] = None
        
        # 提取提交日期
        filed_pattern = r'FILED AS OF DATE:\s+(\d{8})'
        filed_match = re.search(filed_pattern, content)
        if filed_match:
            filed_str = filed_match.group(1)
            metadata['filed_date'] = f"{filed_str[:4]}-{filed_str[4:6]}-{filed_str[6:8]}"
        else:
            metadata['filed_date'] = None
        
        return metadata

    def find_content_start_position(self, content):
        """找到實際內容開始位置，跳過TABLE OF CONTENTS"""
        
        # 直接尋找所有 Item 1 的位置，然後選擇真正包含內容的那一個
        item1_matches = list(re.finditer(r'Item\s+1\.', content, re.IGNORECASE | re.MULTILINE))
        
        print(f"   📍 找到 {len(item1_matches)} 個 Item 1 位置")
        
        for i, match in enumerate(item1_matches):
            match_pos = match.start()
            # 檢查這個位置後面更大範圍的內容（提高到3000字符）
            sample_content = content[match_pos:match_pos + 3000]
            
            # 檢查是否包含真實的業務內容
            if self.looks_like_real_content(sample_content):
                print(f"   🎯 選擇位置 {i+1}: {match_pos} (包含真實內容)")
                return match_pos
            else:
                print(f"   ⏭️ 跳過位置 {i+1}: {match_pos} (看起來是目錄)")
        
        # 如果都沒找到真實內容，嘗試從 PART I 開始
        part_i_match = re.search(r'PART\s+I\s*[^\w]', content, re.IGNORECASE | re.MULTILINE)
        if part_i_match:
            part_i_pos = part_i_match.end()
            print(f"   📍 使用 PART I 位置: {part_i_pos}")
            return part_i_pos
        
        # 最後手段：從文件的1/3處開始
        fallback_pos = len(content) // 3
        print(f"   📍 使用預設位置: {fallback_pos} (檔案總長度: {len(content)})")
        return fallback_pos

    def looks_like_real_content(self, text):
        """檢查文本是否看起來像真實內容而不是目錄或HTML"""
        # 清理 HTML 標籤和特殊字符
        clean_text = re.sub(r'<[^>]+>', ' ', text)
        clean_text = re.sub(r'&#\d+;', ' ', clean_text)  # 清理HTML實體
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        # 如果太短，可能不是真實內容
        if len(clean_text) < 50:
            return False
        
        # 檢查是否明顯是目錄（包含太多頁碼）
        page_number_pattern = r'\b\d{1,3}\b'
        page_numbers = re.findall(page_number_pattern, clean_text)
        if len(page_numbers) > 10:  # 如果有太多數字，可能是目錄
            return False
        
        # 檢查是否包含明顯的目錄特徵
        toc_indicators = [
            r'Table\s+of\s+Contents',
            r'Part\s+I.*Part\s+II',
            r'Item\s+\d+\..*\d+\s*$',
            r'Page\s*\d+',
            r'\.{3,}',  # 多個點（目錄中常見）
        ]
        
        for indicator in toc_indicators:
            if re.search(indicator, clean_text, re.IGNORECASE):
                return False
        
        # 檢查是否包含實質性的業務內容關鍵字（降低門檻）
        business_keywords = [
            r'Company', r'business', r'operations', r'products', r'services', 
            r'revenue', r'customers', r'markets', r'develops', r'designs', 
            r'manufactures', r'sells', r'technology', r'solutions', r'platform',
            r'segment', r'industry', r'competitive', r'strategy', r'fiscal',
            r'Our Company', r'We are', r'We operate', r'We design', r'We develop'
        ]
        
        keyword_count = 0
        for keyword in business_keywords:
            if re.search(keyword, clean_text, re.IGNORECASE):
                keyword_count += 1
        
        # 只需要至少2個相關關鍵字就認為是真實內容（降低門檻）
        return keyword_count >= 2

    def clean_html_content(self, content):
        """徹底清理HTML標籤、CSS樣式和特殊字符 - 優化版本"""
        stage_start = time.time()
        
        # 使用預編譯的正則表達式
        content = self.html_style_pattern.sub(' ', content)
        content = self.html_script_pattern.sub(' ', content)
        content = self.html_tag_pattern.sub(' ', content)
        content = self.html_entity_pattern.sub(' ', content)
        content = self.whitespace_pattern.sub(' ', content)
        
        # 移除不必要的特殊字符
        content = content.replace('\x00', ' ')  # NULL 字符
        content = content.replace('\r\n', '\n').replace('\r', '\n')  # 統一換行符
        
        stage_duration = time.time() - stage_start
        self.log_performance("HTML清理", stage_duration)
        
        return content.strip()

    def extract_items(self, content):
        """提取所有Item內容 - 改進版，處理少於5個字的目錄區塊"""
        extract_start = time.time()
        items = {}
        
        # 第一步：徹底清理HTML標籤、CSS樣式和特殊字符
        print("   🧹 清理HTML標籤和CSS樣式...")
        clean_content = self.clean_html_content(content)
        
        print(f"   📊 清理前長度: {len(content):,}, 清理後長度: {len(clean_content):,}")
        
        # 找到實際內容開始位置
        content_start = self.find_content_start_position(clean_content)
        print(f"   📍 真實內容開始位置: {content_start:,}")
        
        # 優化：一次性找到所有Item位置，避免重複搜索
        all_item_positions = {}
        for item_key, pattern in self.compiled_patterns.items():
            if item_key == 'appendix':
                continue
            search_content = clean_content[content_start:]
            matches = list(pattern.finditer(search_content))
            if matches:
                all_item_positions[item_key] = [(m.start() + content_start, m.end() + content_start) for m in matches]
        
        print(f"   🔍 找到 {len(all_item_positions)} 種Item類型的匹配位置")
        
        # 處理一般的Items
        for item_key in self.compiled_patterns.keys():
            if item_key == 'appendix':  # 附錄需要特殊處理
                continue
            
            try:
                if item_key not in all_item_positions:
                    items[item_key] = None
                    print(f"   ❌ {item_key}: 在真實內容區域未找到匹配")
                    continue
                
                positions = all_item_positions[item_key]
                found_valid_content = False
                
                for match_idx, (start_pos, end_pos) in enumerate(positions):
                    print(f"   🔍 {item_key} 位置 {match_idx + 1}: 在位置 {start_pos:,} 找到匹配")
                    
                    # 對於某些Item，嘗試找到真正的內容開始位置
                    if item_key == 'item_1':
                        # 尋找 "Business" 標題（可能在Item 1後面一段距離）
                        business_pattern = re.compile(r'Business\s*[^\w]', re.IGNORECASE)
                        business_search_range = clean_content[start_pos:start_pos + 1000]
                        business_match = business_pattern.search(business_search_range)
                        if business_match:
                            # 從Business標題後開始提取內容
                            content_start_pos = start_pos + business_match.end()
                            print(f"   📝 {item_key}: 找到Business標題，從位置 {content_start_pos:,} 開始提取")
                        else:
                            # 如果沒找到Business，從Item匹配位置後開始
                            content_start_pos = end_pos
                    else:
                        content_start_pos = end_pos
                    
                    # 快速查找下一個Item的開始位置作為結束點
                    next_item_pos = len(clean_content)
                    for other_key, other_positions in all_item_positions.items():
                        if other_key == item_key:
                            continue
                        for other_start, _ in other_positions:
                            if other_start > content_start_pos and other_start < next_item_pos:
                                next_item_pos = other_start
                    
                    # 提取Item內容
                    item_content = clean_content[content_start_pos:next_item_pos].strip()
                    
                    # 快速清理內容
                    item_content = self.whitespace_pattern.sub(' ', item_content)
                    
                    print(f"   📏 {item_key} 位置 {match_idx + 1}: 提取了 {len(item_content):,} 字符")
                    
                    # 關鍵檢查：如果內容少於5個字符，認為還在目錄區塊，繼續嘗試下一個匹配
                    if len(item_content.strip()) < 5:
                        print(f"   ⏭️ {item_key} 位置 {match_idx + 1}: 內容太短 ({len(item_content)} 字符)，可能是目錄，繼續搜索...")
                        continue
                    
                    # 額外檢查：如果內容明顯是目錄特徵（只有數字和短詞）
                    if self.looks_like_table_of_contents(item_content):
                        print(f"   ⏭️ {item_key} 位置 {match_idx + 1}: 看起來是目錄內容，繼續搜索...")
                        continue
                    
                    # 檢查內容是否真的有意義（不只是引用或轉向）
                    if self.is_meaningful_content(item_content):
                        # 找到有效內容，限制長度並保存
                        if len(item_content) > 65535:  # TEXT 欄位限制
                            item_content = item_content[:65532] + "..."
                        
                        items[item_key] = item_content
                        found_valid_content = True
                        
                        # 顯示找到的內容預覽
                        preview = item_content[:100] + "..." if len(item_content) > 100 else item_content
                        print(f"   ✅ {item_key}: {len(item_content):,} 字符 (位置 {match_idx + 1}) - {preview}")
                        break  # 找到有效內容後跳出循環
                    else:
                        print(f"   ⏭️ {item_key} 位置 {match_idx + 1}: 內容不夠實質，繼續搜索...")
                        continue
                
                # 如果所有匹配都無效，設為None
                if not found_valid_content:
                    items[item_key] = None
                    print(f"   ❌ {item_key}: 所有位置都無有效內容")
                
            except Exception as e:
                print(f"⚠️ 提取 {item_key} 時發生錯誤: {e}")
                items[item_key] = None
        
        # 特殊處理附錄
        items['appendix'] = self.extract_appendix(clean_content)
        
        extract_duration = time.time() - extract_start
        self.log_performance("Items提取完成", extract_duration)
        
        return items

    def looks_like_table_of_contents(self, text):
        """檢查內容是否看起來像目錄"""
        if len(text.strip()) < 20:  # 太短的內容可能是目錄
            return True
        
        # 對於長內容（超過1000字符），更寬鬆的檢查
        if len(text.strip()) > 1000:
            # 檢查是否有明顯的目錄特徵（提高門檻）
            toc_patterns = [
                r'Table\s+of\s+Contents',
                r'INDEX\s+TO\s+FINANCIAL\s+STATEMENTS',
                r'^\s*Item\s+\d+[A-Z]?\s+[\.]{3,}',  # Item x ....格式
                r'^\s*Page\s+\d+\s*$',  # 單獨的頁碼行
            ]
            
            strong_toc_count = 0
            for pattern in toc_patterns:
                if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
                    strong_toc_count += 1
            
            # 對於長內容，需要至少2個強目錄特徵才認為是目錄
            if strong_toc_count < 2:
                return False
        
        # 檢查是否有太多的頁碼數字（降低門檻）
        numbers = re.findall(r'\b\d{1,3}\b', text)
        words = text.split()
        if len(words) > 0 and len(numbers) > len(words) * 0.4:  # 提高到40%門檻
            return True
        
        # 檢查是否包含明顯的目錄特徵
        toc_patterns = [
            r'\.\.\.',  # 目錄中的點線
            r'Page\s+\d+',  # 頁碼
            r'^\s*\d+\s*$',  # 只有數字的行
            r'Table\s+of\s+Contents',
            r'^\s*Item\s+\d+[A-Z]?\s+[\.]{2,}',  # Item x ....格式
        ]
        
        toc_pattern_count = 0
        for pattern in toc_patterns:
            if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
                toc_pattern_count += 1
        
        # 需要多個目錄特徵才認為是目錄
        return toc_pattern_count >= 2

    def extract_appendix(self, content):
        """特殊處理附錄內容"""
        try:
            # 簡化的附錄提取邏輯
            f_page_pattern = r'F-\d+'
            f_matches = list(re.finditer(f_page_pattern, content))
            
            if not f_matches:
                return None
            
            # 從第一個F-頁碼開始提取
            first_f_match = f_matches[0]
            appendix_start_pos = max(0, first_f_match.start() - 500)
            
            # 提取附錄內容
            appendix_content = content[appendix_start_pos:].strip()
            
            # 清理和限制長度
            appendix_content = re.sub(r'\s+', ' ', appendix_content)
            if len(appendix_content) > 65535:
                appendix_content = appendix_content[:65532] + "..."
            
            if appendix_content:
                preview = appendix_content[:100] + "..." if len(appendix_content) > 100 else appendix_content
                print(f"   ✅ appendix: {len(appendix_content)} 字符 - {preview}")
                return appendix_content
            
            return None
            
        except Exception as e:
            print(f"⚠️ 提取附錄時發生錯誤: {e}")
            return None

    def generate_content_hash(self, content):
        """生成內容的MD5雜湊值，用於檢查重複"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def save_to_database(self, file_path, metadata, items):
        """儲存到資料庫"""
        if not self.db_connection or not self.db_connection.is_connected():
            print("❌ 資料庫未連接")
            return False

        try:
            cursor = self.db_connection.cursor()
            
            # 檢查是否已存在相同的文件
            content_hash = self.generate_content_hash(str(metadata) + str(items))
            check_sql = "SELECT id FROM ten_k_filings WHERE content_hash = %s"
            cursor.execute(check_sql, (content_hash,))
            
            if cursor.fetchone():
                print(f"⚠️ 文件已存在，跳過: {file_path}")
                return True

            # 插入數據
            insert_sql = """
                INSERT INTO ten_k_filings (
                    file_name, document_number, company_name, cik, 
                    report_date, filed_date, content_hash,
                    item_1, item_1a, item_1b, item_2, item_3, item_4,
                    item_5, item_6, item_7, item_7a, item_8, item_9,
                    item_9a, item_9b, item_10, item_11, item_12,
                    item_13, item_14, item_15, item_16, appendix,
                    created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                )
            """
            
            values = (
                os.path.basename(file_path),
                metadata.get('document_number'),
                metadata.get('company_name'),  # 現在是股票代號
                metadata.get('cik'),
                metadata.get('report_date'),
                metadata.get('filed_date'),
                content_hash,
                items.get('item_1'),
                items.get('item_1a'),
                items.get('item_1b'),
                items.get('item_2'),
                items.get('item_3'),
                items.get('item_4'),
                items.get('item_5'),
                items.get('item_6'),
                items.get('item_7'),
                items.get('item_7a'),
                items.get('item_8'),
                items.get('item_9'),
                items.get('item_9a'),
                items.get('item_9b'),
                items.get('item_10'),
                items.get('item_11'),
                items.get('item_12'),
                items.get('item_13'),
                items.get('item_14'),
                items.get('item_15'),
                items.get('item_16'),
                items.get('appendix')
            )
            
            cursor.execute(insert_sql, values)
            self.db_connection.commit()
            
            print(f"✅ 成功儲存: {os.path.basename(file_path)}")
            return True
            
        except Error as e:
            print(f"❌ 資料庫插入失敗: {e}")
            return False

    def process_10k_file(self, file_path):
        """處理單個10-K文件 - 優化版本"""
        print(f"\n📄 處理文件: {os.path.basename(file_path)}")
        file_start_time = time.time()
        
        try:
            # 讀取文件內容
            read_start = time.time()
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
            read_duration = time.time() - read_start
            self.log_performance(f"讀取文件 ({len(content):,} 字符)", read_duration)
            
            # 提取基本資訊
            metadata_start = time.time()
            metadata = self.extract_filing_metadata(content)
            metadata_duration = time.time() - metadata_start
            self.log_performance("提取元數據", metadata_duration)
            
            print(f"   📊 股票代號: {metadata.get('company_name', 'N/A')}")
            print(f"   📅 報告日期: {metadata.get('report_date', 'N/A')}")
            
            # 提取Items
            print(f"   🔍 提取Items...")
            items_start = time.time()
            items = self.extract_items(content)
            items_duration = time.time() - items_start
            self.log_performance("提取Items", items_duration)
            
            # 統計有效Items
            valid_items = sum(1 for v in items.values() if v is not None)
            print(f"   ✅ 成功提取 {valid_items}/{len(items)} 個Items")
            
            # 儲存到資料庫
            db_start = time.time()
            success = self.save_to_database(file_path, metadata, items)
            db_duration = time.time() - db_start
            self.log_performance("數據庫保存", db_duration)
            
            file_total_duration = time.time() - file_start_time
            self.log_performance(f"處理文件完成", file_total_duration)
            
            return success
            
        except Exception as e:
            print(f"❌ 處理文件失敗: {e}")
            return False

    def process_ticker_folder(self):
        """處理指定股票代號資料夾中的所有10-K文件"""
        ticker_10k_path = Path(__file__).parent / "downloads" / self.ticker / "10-K"
        
        if not ticker_10k_path.exists():
            print(f"❌ 找不到 {self.ticker} 10-K資料夾: {ticker_10k_path}")
            return False
        
        # 獲取所有.txt文件
        txt_files = list(ticker_10k_path.glob("*.txt"))
        
        if not txt_files:
            print(f"❌ 沒有找到 {self.ticker} 的10-K文件")
            return False
        
        print(f"🔍 找到 {len(txt_files)} 個 {self.ticker} 的10-K文件")
        
        # 連接資料庫
        if not self.connect_database():
            return False
        
        success_count = 0
        
        try:
            for file_path in txt_files:
                if self.process_10k_file(file_path):
                    success_count += 1
        
        finally:
            self.disconnect_database()
        
        print(f"\n🎉 {self.ticker} 處理完成! 成功: {success_count}/{len(txt_files)}")
        return success_count > 0

    def is_meaningful_content(self, content):
        """檢查內容是否有意義（不只是引用或轉向）"""
        if len(content.strip()) < 10:  # 放寬長度限制
            return False
        
        # 檢查是否只是引用其他文件（更寬鬆的判斷）
        reference_patterns = [
            r'information.*incorporated.*by reference',
            r'see.*proxy statement',
            r'refer to.*form',
            r'included.*elsewhere',
            r'set forth.*below',
            r'discussed.*in.*note',
        ]
        
        clean_content = content.lower()
        reference_count = 0
        for pattern in reference_patterns:
            if re.search(pattern, clean_content):
                reference_count += 1
        
        # 只有當內容很短且主要是引用時才認為無意義
        if reference_count > 0 and len(content.strip()) < 50:
            return False
        
        # 檢查是否只包含無意義的短語
        meaningless_patterns = [
            r'^None\.$',
            r'^Not applicable\.$',
            r'^N/A$',
            r'^\s*-\s*$',
            r'^\s*\d+\s*$'  # 只有數字
        ]
        
        for pattern in meaningless_patterns:
            if re.match(pattern, content.strip(), re.IGNORECASE):
                return False
        
        # 對於內容長度超過100字符的，基本上都認為是有意義的
        if len(content.strip()) >= 100:
            return True
        
        # 對於較短內容，檢查是否包含一些實質性關鍵字
        substantial_keywords = [
            r'Company', r'business', r'operations', r'revenue', r'income',
            r'assets', r'liabilities', r'cash', r'employees', r'products',
            r'services', r'customers', r'markets', r'competition', r'risks',
            r'strategy', r'acquisitions', r'development', r'technology',
            r'headquarters', r'located', r'properties', r'legal', r'proceedings',
            r'management', r'discussion', r'analysis', r'financial', r'statements'
        ]
        
        keyword_count = 0
        for keyword in substantial_keywords:
            if re.search(keyword, content, re.IGNORECASE):
                keyword_count += 1
        
        # 降低關鍵字要求，只需要1個相關關鍵字即可
        return keyword_count >= 1

def main():
    """主函數"""
    if len(sys.argv) != 2:
        print("用法: python parse_single_stock.py <股票代號>")
        print("範例: python parse_single_stock.py AAPL")
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    parser = SingleStockTenKParser(ticker)
    
    success = parser.process_ticker_folder()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main() 