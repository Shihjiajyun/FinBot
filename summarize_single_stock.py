#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
單一股票 GPT 摘要器
基於 gpt_summarizer.py，專門處理指定股票的選定財報摘要
"""

import sys
import mysql.connector
import openai
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional

class SingleStockGPTSummarizer:
    """單一股票 GPT 摘要處理器"""
    
    def __init__(self, ticker: str, filing_ids: List[int], db_config: Dict = None):
        """
        初始化摘要處理器
        
        Args:
            ticker: 股票代號
            filing_ids: 要摘要的財報ID列表
            db_config: 資料庫連接配置
        """
        self.ticker = ticker.upper()
        self.filing_ids = filing_ids
        
        self.openai_client = openai.OpenAI(
            api_key='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'
        )
        
        self.db_config = db_config or {
            'host': '43.207.210.147',
            'database': 'finbot_db',
            'user': 'myuser',
            'password': '123456789',
            'charset': 'utf8mb4'
        }
        
        self.setup_logging()
        
        # GPT 摘要提示詞模板
        self.summary_prompts = {
            'item_1': """
            請摘要以下 10-K Item 1 (Business) 內容。請遵循以下要求：
            
            1. 如果原文有具體數據，必須在摘要中保留，並提供支持數據的表格或數字
            2. 如果需要從附錄中查找相關資料，請一併整合到摘要中
            3. 只回答有明確根據的內容，沒有信心的不要回答
            4. 每個重點都要說明理由和數據支持
            5. 摘要要包含：業務模式、主要產品/服務、市場地位、競爭優勢等
            
            原文內容：
            {item_content}
            
            附錄內容（如需參考）：
            {appendix_content}
            
            請提供結構化的摘要：
            """,
            
            'item_1a': """
            請摘要以下 10-K Item 1A (Risk Factors) 內容。請遵循以下要求：
            
            1. 保留所有重要的風險數據和量化指標
            2. 對每個風險因素說明潛在影響程度
            3. 只列出有明確描述的風險，不要推測
            4. 如果有歷史數據支持，請包含
            
            原文內容：
            {item_content}
            
            請提供風險因素摘要：
            """,
            
            'financial_items': """
            請摘要以下 10-K 財務相關條目內容。請遵循以下要求：
            
            1. 必須保留所有財務數據、比率、百分比
            2. 如果附錄中有相關財務表格，請整合到摘要中
            3. 說明數據的時間範圍和比較基準
            4. 對重要財務變化提供分析和解釋
            5. 只基於實際數據進行摘要，不要推測
            
            原文內容：
            {item_content}
            
            附錄內容（如需參考）：
            {appendix_content}
            
            請提供財務摘要：
            """,
            
            'governance_items': """
            請摘要以下 10-K 治理相關條目內容。請遵循以下要求：
            
            1. 保留重要的人員資訊、薪酬數據
            2. 如果附錄中有相關治理表格，請整合
            3. 說明治理結構的重要變化
            4. 只基於明確資訊進行摘要
            
            原文內容：
            {item_content}
            
            附錄內容（如需參考）：
            {appendix_content}
            
            請提供治理摘要：
            """,
            
            'default': """
            請摘要以下 10-K 條目內容。請遵循以下要求：
            
            1. 保留所有重要數據和量化資訊
            2. 如果附錄中有相關資料，請整合
            3. 只回答有明確根據的內容
            4. 說明重要變化和趨勢
            
            原文內容：
            {item_content}
            
            附錄內容（如需參考）：
            {appendix_content}
            
            請提供摘要：
            """
        }
        
    def setup_logging(self):
        """設置日誌記錄"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def get_db_connection(self):
        """建立資料庫連接"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            return connection
        except mysql.connector.Error as err:
            self.logger.error(f"資料庫連接失敗: {err}")
            raise
            
    def get_filings_to_process(self) -> List[Dict]:
        """獲取要處理的 10-K 檔案"""
        connection = self.get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            placeholders = ','.join(['%s'] * len(self.filing_ids))
            query = f"""
            SELECT f.* FROM ten_k_filings f
            WHERE f.id IN ({placeholders}) AND f.company_name = %s
            ORDER BY f.report_date DESC
            """
            cursor.execute(query, self.filing_ids + [self.ticker])
            return cursor.fetchall()
            
        finally:
            cursor.close()
            connection.close()
            
    def get_item_prompt(self, item_name: str) -> str:
        """根據 Item 類型選擇合適的提示詞"""
        if item_name == 'item_1':
            return self.summary_prompts['item_1']
        elif item_name == 'item_1a':
            return self.summary_prompts['item_1a']
        elif item_name in ['item_5', 'item_6', 'item_7', 'item_7a', 'item_8', 'item_14']:
            return self.summary_prompts['financial_items']
        elif item_name in ['item_10', 'item_11', 'item_12']:
            return self.summary_prompts['governance_items']
        else:
            return self.summary_prompts['default']
            
    def call_gpt_api(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """調用 GPT API 進行摘要"""
        for attempt in range(max_retries):
            try:
                # 使用 gpt-3.5-turbo 作為便宜的模型選擇
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo-16k",  # 較便宜的模型，有16K上下文窗口
                    messages=[
                        {
                            "role": "system", 
                            "content": "你是一個專業的財務分析師，專門分析 SEC 10-K 檔案。請提供準確、基於數據的摘要。"
                        },
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=2000,
                    temperature=0.3
                )
                
                return response.choices[0].message.content.strip()
                
            except Exception as e:
                self.logger.warning(f"GPT API 調用失敗 (嘗試 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # 指數退避
                else:
                    self.logger.error(f"GPT API 調用最終失敗: {e}")
                    return None
                    
    def estimate_tokens(self, text: str) -> int:
        """估算文本的 token 數量"""
        return len(text) // 3
    
    def summarize_item(self, item_content: str, item_name: str, appendix_content: str = "") -> Optional[str]:
        """摘要單個 Item"""
        if not item_content or item_content.strip() == "":
            return None
        
        # 智能內容截斷，gpt-3.5-turbo-16k 有16K tokens 上下文
        max_total_tokens = 15000  # 使用15K作為安全限制
        max_output_tokens = 2000
        max_input_tokens = max_total_tokens - max_output_tokens
        
        # 選擇合適的提示詞並估算基礎 token
        prompt_template = self.get_item_prompt(item_name)
        base_prompt = prompt_template.format(item_content="", appendix_content="")
        base_tokens = self.estimate_tokens(base_prompt)
        
        # 計算可用於內容的 token 數
        available_tokens = max_input_tokens - base_tokens - 100  # 留出100個token緩衝
        
        # 分配 token 給主要內容和附錄
        content_tokens = int(available_tokens * 0.7)  # 70% 給主要內容
        appendix_tokens = int(available_tokens * 0.3)  # 30% 給附錄
        
        # 截斷內容
        content_chars = content_tokens * 3  # token 轉字符數
        if len(item_content) > content_chars:
            item_content = item_content[:content_chars] + "\n...(內容已截斷)"
            
        # 截斷附錄
        appendix_chars = appendix_tokens * 3
        if len(appendix_content) > appendix_chars:
            appendix_content = appendix_content[:appendix_chars] + "\n...(附錄已截斷)"
        
        # 生成最終 prompt
        prompt = prompt_template.format(
            item_content=item_content,
            appendix_content=appendix_content
        )
        
        # 最終 token 檢查
        final_tokens = self.estimate_tokens(prompt)
        self.logger.info(f"開始摘要 {item_name} (估計 {final_tokens} tokens)")
        
        summary = self.call_gpt_api(prompt)
        
        if summary:
            self.logger.info(f"成功 {item_name} 摘要完成")
            return summary
        else:
            self.logger.error(f"失敗 {item_name} 摘要失敗")
            return None
            
    def create_summary_record(self, filing_data: Dict) -> int:
        """創建摘要記錄"""
        connection = self.get_db_connection()
        cursor = connection.cursor()
        
        try:
            insert_query = """
            INSERT INTO ten_k_filings_summary (
                original_filing_id, file_name, company_name, report_date, processing_status
            ) VALUES (%s, %s, %s, %s, 'processing')
            """
            
            cursor.execute(insert_query, (
                filing_data['id'],
                filing_data['file_name'],
                filing_data['company_name'],  # 現在是股票代號
                filing_data['report_date']
            ))
            
            summary_id = cursor.lastrowid
            connection.commit()
            return summary_id
            
        finally:
            cursor.close()
            connection.close()
            
    def update_summary_item(self, summary_id: int, item_name: str, summary_content: str):
        """更新單個 Item 的摘要"""
        connection = self.get_db_connection()
        cursor = connection.cursor()
        
        try:
            update_query = f"""
            UPDATE ten_k_filings_summary 
            SET {item_name}_summary = %s,
                items_processed_count = items_processed_count + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """
            
            cursor.execute(update_query, (summary_content, summary_id))
            connection.commit()
            
        finally:
            cursor.close()
            connection.close()
            
    def complete_summary(self, summary_id: int, processing_time: int, success_count: int):
        """完成摘要處理"""
        connection = self.get_db_connection()
        cursor = connection.cursor()
        
        try:
            status = 'completed' if success_count > 0 else 'failed'
            
            update_query = """
            UPDATE ten_k_filings_summary 
            SET processing_status = %s,
                processing_time_seconds = %s,
                summary_completed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """
            
            cursor.execute(update_query, (status, processing_time, summary_id))
            connection.commit()
            
        finally:
            cursor.close()
            connection.close()
            
    def process_filing(self, filing_data: Dict) -> bool:
        """處理單個 10-K 檔案的摘要"""
        start_time = time.time()
        
        self.logger.info(f"開始處理: {filing_data['file_name']}")
        self.logger.info(f"   股票代號: {filing_data['company_name']}")
        self.logger.info(f"   報告日期: {filing_data['report_date']}")
        
        # 檢查是否已有摘要
        connection = self.get_db_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute(
                "SELECT id FROM ten_k_filings_summary WHERE original_filing_id = %s",
                (filing_data['id'],)
            )
            existing_summary = cursor.fetchone()
            
            if existing_summary:
                self.logger.info(f"   已存在摘要，跳過: {filing_data['file_name']}")
                return True
                
        finally:
            cursor.close()
            connection.close()
        
        # 創建摘要記錄
        summary_id = self.create_summary_record(filing_data)
        
        # 定義所有 Item 欄位
        item_fields = [
            'item_1', 'item_1a', 'item_1b', 'item_2', 'item_3', 'item_4',
            'item_5', 'item_6', 'item_7', 'item_7a', 'item_8', 'item_9',
            'item_9a', 'item_9b', 'item_10', 'item_11', 'item_12',
            'item_13', 'item_14', 'item_15', 'item_16'
        ]
        
        success_count = 0
        appendix_content = filing_data.get('appendix', '') or ''
        
        for item_field in item_fields:
            item_content = filing_data.get(item_field)
            
            if item_content and item_content.strip():
                summary = self.summarize_item(item_content, item_field, appendix_content)
                
                if summary:
                    self.update_summary_item(summary_id, item_field, summary)
                    success_count += 1
                    
                # 避免 API 限流
                time.sleep(1)
            else:
                self.logger.info(f"   跳過 {item_field} 內容為空")
                
        # 完成處理
        processing_time = int(time.time() - start_time)
        self.complete_summary(summary_id, processing_time, success_count)
        
        self.logger.info(f"   完成摘要: {success_count}/{len(item_fields)} 個Items")
        self.logger.info(f"   處理時間: {processing_time} 秒")
        
        return success_count > 0
        
    def run_processing(self):
        """運行摘要處理"""
        self.logger.info(f"開始處理 {self.ticker} 的指定財報摘要")
        self.logger.info(f"財報ID: {self.filing_ids}")
        
        # 獲取要處理的檔案
        filings = self.get_filings_to_process()
        
        if not filings:
            self.logger.error("沒有找到要處理的財報")
            return False
            
        self.logger.info(f"找到 {len(filings)} 個待處理檔案")
        
        success_count = 0
        
        for i, filing in enumerate(filings, 1):
            try:
                self.logger.info(f"\n--- 處理進度: {i}/{len(filings)} ---")
                
                if self.process_filing(filing):
                    success_count += 1
                    
            except Exception as e:
                self.logger.error(f"失敗 處理檔案失敗: {filing['file_name']}, 錯誤: {e}")
                continue
                
        self.logger.info(f"\n摘要處理完成!")
        self.logger.info(f"成功: {success_count}/{len(filings)}")
        
        return success_count > 0


def main():
    """主函數"""
    if len(sys.argv) != 3:
        print("用法: python summarize_single_stock.py <股票代號> <財報ID,以逗號分隔>")
        print("範例: python summarize_single_stock.py AAPL 1,2,3")
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    filing_ids_str = sys.argv[2]
    
    try:
        filing_ids = [int(id.strip()) for id in filing_ids_str.split(',')]
    except ValueError:
        print("錯誤: 財報ID必須是數字，以逗號分隔")
        sys.exit(1)
    
    print(f"🚀 開始摘要 {ticker} 的財報: {filing_ids}")
    
    # 資料庫配置
    db_config = {
        'host': '43.207.210.147',
        'user': 'myuser',
        'password': '123456789',
        'database': 'finbot_db',
        'charset': 'utf8mb4'
    }
    
    # 創建摘要處理器
    summarizer = SingleStockGPTSummarizer(ticker, filing_ids, db_config)
    
    # 運行處理
    success = summarizer.run_processing()
    
    if success:
        print(f"🎉 {ticker} 摘要完成!")
        sys.exit(0)
    else:
        print(f"❌ {ticker} 摘要失敗!")
        sys.exit(1)


if __name__ == "__main__":
    main() 