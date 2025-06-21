#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
10-K Filing Items Parser and Database Inserter
解析 AAPL 資料夾中的 10-K 檔案，並將各個 Item 內容存入資料表
"""

import os
import re
import mysql.connector
from mysql.connector import Error
from datetime import datetime
from pathlib import Path
import hashlib

class TenKParser:
    def __init__(self, db_config=None):
        # 資料庫配置
        self.db_config = db_config or {
            'host': '43.207.210.147',
            'database': 'finbot_db',
            'user': 'myuser',
            'password': '123456789',
            'charset': 'utf8mb4'
        }
        
        self.db_connection = None
        
        # 10-K 中常見的 Item 類型
        self.item_patterns = {
            'item_1': r'Item\s+1\.\s+(?:Business|BUSINESS)',
            'item_1a': r'Item\s+1A\.\s+(?:Risk Factors|RISK FACTORS)',
            'item_1b': r'Item\s+1B\.\s+(?:Unresolved Staff Comments|UNRESOLVED STAFF COMMENTS)',
            'item_2': r'Item\s+2\.\s+(?:Properties|PROPERTIES)',
            'item_3': r'Item\s+3\.\s+(?:Legal Proceedings|LEGAL PROCEEDINGS)',
            'item_4': r'Item\s+4\.\s+(?:Mine Safety|MINE SAFETY)',
            'item_5': r'Item\s+5\.\s+(?:Market for Registrant|MARKET FOR REGISTRANT)',
            'item_6': r'Item\s+6\.\s+(?:Selected Financial Data|SELECTED FINANCIAL DATA)',
            'item_7': r'Item\s+7\.\s+(?:Management|MANAGEMENT)',
            'item_7a': r'Item\s+7A\.\s+(?:Quantitative and Qualitative|QUANTITATIVE AND QUALITATIVE)',
            'item_8': r'Item\s+8\.\s+(?:Financial Statements|FINANCIAL STATEMENTS)',
            'item_9': r'Item\s+9\.\s+(?:Changes in and Disagreements|CHANGES IN AND DISAGREEMENTS)',
            'item_9a': r'Item\s+9A\.\s+(?:Controls and Procedures|CONTROLS AND PROCEDURES)',
            'item_9b': r'Item\s+9B\.\s+(?:Other Information|OTHER INFORMATION)',
            'item_10': r'Item\s+10\.\s+(?:Directors|DIRECTORS)',
            'item_11': r'Item\s+11\.\s+(?:Executive Compensation|EXECUTIVE COMPENSATION)',
            'item_12': r'Item\s+12\.\s+(?:Security Ownership|SECURITY OWNERSHIP)',
            'item_13': r'Item\s+13\.\s+(?:Certain Relationships|CERTAIN RELATIONSHIPS)',
            'item_14': r'Item\s+14\.\s+(?:Principal Accountant|PRINCIPAL ACCOUNTANT)',
            'item_15': r'Item\s+15\.\s+(?:Exhibits|EXHIBITS)',
            'item_16': r'Item\s+16\.\s+(?:Form 10-K Summary|FORM 10-K SUMMARY)',
            'appendix': r'(?:INDEX\s+TO\s+FINANCIAL\s+STATEMENTS|APPENDIX|CONSOLIDATED\s+FINANCIAL\s+STATEMENTS)'
        }

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
        
        # 提取公司名稱
        company_pattern = r'COMPANY CONFORMED NAME:\s+(.+)'
        company_match = re.search(company_pattern, content)
        metadata['company_name'] = company_match.group(1).strip() if company_match else 'Apple Inc.'
        
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
            # 檢查這個位置後面的內容
            sample_content = content[match_pos:match_pos + 1000]
            
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
        if len(clean_text) < 100:
            return False
        
        # 檢查是否包含明確的業務內容關鍵短語
        business_phrases = [
            r'Company\s+Background',
            r'The\s+Company\s+designs',
            r'The\s+Company\s+manufactures',
            r'designs,\s+manufactures\s+and\s+markets',
            r'smartphones,\s+personal\s+computers',
            r'We\s+design\s+and\s+develop',
            r'Our\s+business\s+segments',
            r'fiscal\s+year.*ends',
            r'business\s+operations',
            r'Company.*designs.*manufactures'
        ]
        
        phrase_count = 0
        for phrase in business_phrases:
            if re.search(phrase, clean_text, re.IGNORECASE):
                phrase_count += 1
                
        # 如果包含明確的業務短語，就認為是真實內容
        if phrase_count >= 1:
            return True
        
        # 檢查是否包含足夠的實質性業務關鍵字
        business_keywords = [
            r'Company', r'designs', r'manufactures', r'markets', r'smartphones',
            r'personal\s+computers', r'tablets', r'wearables', r'accessories',
            r'services', r'revenue', r'fiscal\s+year', r'operations', r'products',
            r'customers', r'development', r'iPhone', r'iPad', r'Mac', r'Apple\s+Watch'
        ]
        
        keyword_count = 0
        for keyword in business_keywords:
            if re.search(keyword, clean_text, re.IGNORECASE):
                keyword_count += 1
        
        # 需要至少3個相關關鍵字才認為是真實內容
        return keyword_count >= 3

    def clean_html_content(self, content):
        """徹底清理HTML標籤、CSS樣式和特殊字符"""
        # 移除 <style> 標籤及其內容
        content = re.sub(r'<style[^>]*>.*?</style>', ' ', content, flags=re.DOTALL | re.IGNORECASE)
        
        # 移除 <script> 標籤及其內容
        content = re.sub(r'<script[^>]*>.*?</script>', ' ', content, flags=re.DOTALL | re.IGNORECASE)
        
        # 移除所有HTML標籤
        content = re.sub(r'<[^>]+>', ' ', content)
        
        # 移除HTML實體
        content = re.sub(r'&#\d+;', ' ', content)
        content = re.sub(r'&[a-zA-Z]+;', ' ', content)
        
        # 移除多餘的空白字符
        content = re.sub(r'\s+', ' ', content)
        
        return content.strip()

    def extract_items(self, content):
        """提取所有Item內容 - 改進版，先清理HTML再跳過目錄"""
        items = {}
        
        # 第一步：徹底清理HTML標籤、CSS樣式和特殊字符
        print("   🧹 清理HTML標籤和CSS樣式...")
        original_content = content
        clean_content = self.clean_html_content(content)
        
        print(f"   📊 清理前長度: {len(content)}, 清理後長度: {len(clean_content)}")
        
        # 找到實際內容開始位置
        content_start = self.find_content_start_position(clean_content)
        
        # 處理一般的Items
        for item_key, pattern in self.item_patterns.items():
            if item_key == 'appendix':  # 附錄需要特殊處理
                continue
                
            try:
                # 從內容開始位置搜索當前Item
                search_content = clean_content[content_start:]
                start_match = re.search(pattern, search_content, re.IGNORECASE | re.MULTILINE)
                
                if not start_match:
                    items[item_key] = None
                    continue
                
                # 調整位置（相對於完整清理後內容）
                start_pos = content_start + start_match.end()
                
                # 查找下一個Item的開始位置作為結束點
                next_item_pos = len(clean_content)
                for next_pattern in self.item_patterns.values():
                    if next_pattern == pattern or next_pattern == self.item_patterns['appendix']:
                        continue
                    next_match = re.search(next_pattern, clean_content[start_pos:], re.IGNORECASE | re.MULTILINE)
                    if next_match:
                        candidate_pos = start_pos + next_match.start()
                        if candidate_pos < next_item_pos:
                            next_item_pos = candidate_pos
                
                # 提取Item內容
                item_content = clean_content[start_pos:next_item_pos].strip()
                
                # 清理和限制長度
                item_content = re.sub(r'\s+', ' ', item_content)
                if len(item_content) > 65535:  # TEXT 欄位限制
                    item_content = item_content[:65532] + "..."
                
                items[item_key] = item_content if item_content else None
                
                # 顯示找到的內容預覽
                if item_content:
                    preview = item_content[:100] + "..." if len(item_content) > 100 else item_content
                    print(f"   ✅ {item_key}: {len(item_content)} 字符 - {preview}")
                
            except Exception as e:
                print(f"⚠️ 提取 {item_key} 時發生錯誤: {e}")
                items[item_key] = None
        
        # 特殊處理附錄
        items['appendix'] = self.extract_appendix(clean_content)
        
        return items

    def extract_appendix(self, content):
        """特殊處理附錄內容 - 基於F-頁碼和目錄結構識別（優化版）"""
        try:
            # 第一步：找到所有Items的最晚結束位置
            latest_item_end = 0
            
            # 檢查所有Items，找到最後一個有效Item的結束位置
            for item_key, pattern in self.item_patterns.items():
                if item_key == 'appendix':
                    continue
                    
                matches = list(re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE))
                if matches:
                    # 取最後一個匹配的位置
                    latest_match = matches[-1]
                    # 估算該Item的結束位置（向後搜索1000個字符作為緩衝）
                    item_end_estimate = latest_match.end() + 1000
                    if item_end_estimate > latest_item_end:
                        latest_item_end = item_end_estimate
            
            # 如果沒找到任何Item，從文件中間開始搜索
            if latest_item_end == 0:
                latest_item_end = len(content) // 2
            
            print(f"   📍 從位置 {latest_item_end} 開始搜索附錄...")
            
            # 第二步：限制搜索範圍，避免搜索整個文件
            search_content = content[latest_item_end:]
            max_search_length = min(100000, len(search_content))  # 限制搜索範圍為100KB
            limited_search_content = search_content[:max_search_length]
            
            print(f"   🔍 搜索範圍限制為 {max_search_length} 字符")
            
            # 第三步：簡化的F-頁碼搜索
            f_page_pattern = r'F-\d+'
            f_matches = list(re.finditer(f_page_pattern, limited_search_content))
            
            if not f_matches:
                print("   ❌ 未找到F-頁碼，無附錄內容")
                return None
            
            print(f"   📄 找到 {len(f_matches)} 個F-頁碼")
            
            # 第四步：尋找第一個F-頁碼前的目錄標題
            first_f_match = f_matches[0]
            search_start = max(0, first_f_match.start() - 500)  # 向前搜索500字符
            
            # 簡化的目錄模式（避免複雜的正則表達式）
            title_search_text = limited_search_content[search_start:first_f_match.start() + 100]
            
            # 尋找可能的標題關鍵字
            title_keywords = [
                'INDEX TO FINANCIAL STATEMENTS',
                'FINANCIAL STATEMENTS',
                'CONSOLIDATED FINANCIAL STATEMENTS',
                'BALANCE SHEETS',
                'STATEMENTS OF OPERATIONS'
            ]
            
            appendix_start_offset = first_f_match.start()  # 預設從第一個F-頁碼開始
            
            for keyword in title_keywords:
                keyword_pos = title_search_text.upper().find(keyword)
                if keyword_pos != -1:
                    # 找到標題，從標題開始
                    actual_pos = search_start + keyword_pos
                    if actual_pos < first_f_match.start():
                        appendix_start_offset = actual_pos
                        print(f"   🎯 找到附錄標題: {keyword}")
                        break
            
            # 第五步：計算實際的附錄開始位置
            appendix_start_pos = latest_item_end + appendix_start_offset
            
            # 第六步：提取附錄內容（從找到的位置到文件結尾）
            appendix_content = content[appendix_start_pos:].strip()
            
            # 驗證內容確實包含F-頁碼
            if not re.search(r'F-\d+', appendix_content[:1000]):  # 只檢查前1000字符
                print("   ⚠️ 提取的內容不包含F-頁碼，可能不是附錄")
                return None
            
            # 清理和限制長度
            appendix_content = re.sub(r'\s+', ' ', appendix_content)
            if len(appendix_content) > 65535:  # TEXT 欄位限制
                appendix_content = appendix_content[:65532] + "..."
            
            if appendix_content:
                preview = appendix_content[:100] + "..." if len(appendix_content) > 100 else appendix_content
                f_pages = re.findall(r'F-\d+', appendix_content[:1000])  # 檢查前1000字符中的F-頁碼
                print(f"   ✅ appendix: {len(appendix_content)} 字符，包含頁碼: {f_pages[:5]} - {preview}")
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
                metadata.get('company_name'),
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
        """處理單個10-K文件"""
        print(f"\n📄 處理文件: {os.path.basename(file_path)}")
        
        try:
            # 讀取文件內容
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
            
            # 提取基本資訊
            metadata = self.extract_filing_metadata(content)
            print(f"   📊 公司: {metadata.get('company_name', 'N/A')}")
            print(f"   📅 報告日期: {metadata.get('report_date', 'N/A')}")
            
            # 提取Items
            print(f"   🔍 提取Items...")
            items = self.extract_items(content)
            
            # 統計有效Items
            valid_items = sum(1 for v in items.values() if v is not None)
            print(f"   ✅ 成功提取 {valid_items}/{len(items)} 個Items")
            
            # 儲存到資料庫
            success = self.save_to_database(file_path, metadata, items)
            
            return success
            
        except Exception as e:
            print(f"❌ 處理文件失敗: {e}")
            return False

    def process_aapl_folder(self):
        """處理AAPL資料夾中的所有10-K文件"""
        aapl_10k_path = Path(__file__).parent / "downloads" / "AAPL" / "10-K"
        
        if not aapl_10k_path.exists():
            print(f"❌ 找不到AAPL 10-K資料夾: {aapl_10k_path}")
            return False
        
        # 獲取所有.txt文件
        txt_files = list(aapl_10k_path.glob("*.txt"))
        
        if not txt_files:
            print("❌ 沒有找到10-K文件")
            return False
        
        print(f"🔍 找到 {len(txt_files)} 個10-K文件")
        
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
        
        print(f"\n🎉 處理完成! 成功: {success_count}/{len(txt_files)}")
        return success_count > 0

def main():
    """主函數"""
    parser = TenKParser()
    parser.process_aapl_folder()

if __name__ == "__main__":
    main()