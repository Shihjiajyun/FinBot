"""
10-K Filing GPT-4O Model Summarizer
========================================
此腳本使用 OpenAI GPT-4O 模型分析 10-K 檔案並生成摘要
專門為 FinBot 對話系統設計
"""

import mysql.connector
import openai
import json
import time
import logging
import sys
from datetime import datetime
from typing import Dict, Optional, List
import re

class TenKGPT4OSummarizer:
    """10-K 檔案 GPT-4O 模型摘要處理器"""
    
    def __init__(self):
        """初始化摘要處理器"""
        self.openai_client = openai.OpenAI(
            api_key='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'
        )
        
        self.db_config = {
            'host': '13.114.174.139',
            'user': 'myuser',
            'password': '123456789',
            'database': 'finbot_db',
            'charset': 'utf8mb4'
        }
        
        self.setup_logging()
        
    def setup_logging(self):
        """設置日誌記錄"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('o3_summarizer.log'),
                logging.StreamHandler()
            ]
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
            
    def call_gpt4o_api(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """
        調用 GPT-4O API 進行摘要
        
        Args:
            prompt: 提示詞
            max_retries: 最大重試次數
            
        Returns:
            GPT-4O 回應內容或 None
        """
        for attempt in range(max_retries):
            try:
                # 使用 GPT-4O 模型
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o",  # 使用 GPT-4O 模型
                    messages=[
                        {
                            "role": "system", 
                            "content": "您是一位專業的財務分析專家，專門分析 SEC 10-K 檔案。請提供準確、基於數據的摘要，突出關鍵財務指標、業務策略和風險因素。"
                        },
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=4000,  # GPT-4O模型使用max_tokens
                    temperature=0.2
                )
                
                return response.choices[0].message.content.strip()
                
            except Exception as e:
                self.logger.warning(f"GPT-4O API 調用失敗 (嘗試 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # 指數退避
                else:
                    self.logger.error(f"GPT-4O API 調用最終失敗: {e}")
                    return None
                    
    def create_comprehensive_summary(self, filing_data: Dict) -> Optional[str]:
        """
        創建綜合摘要（包含所有重要 Items）
        
        Args:
            filing_data: 檔案資料
            
        Returns:
            綜合摘要內容或 None
        """
        # 收集所有重要的內容
        important_items = []
        
        # 重要的 Items 優先順序
        priority_items = [
            ('item_1', 'Business Overview'),
            ('item_1a', 'Risk Factors'),
            ('item_7', 'Management Discussion & Analysis'),
            ('item_8', 'Financial Statements'),
            ('item_2', 'Properties'),
            ('item_3', 'Legal Proceedings')
        ]
        
        content_parts = []
        
        for item_key, item_title in priority_items:
            item_content = filing_data.get(item_key, '')
            if item_content and len(item_content.strip()) > 100:
                # 截取前5000字符避免超出限制
                truncated_content = item_content[:5000]
                if len(item_content) > 5000:
                    truncated_content += "...(內容已截斷)"
                
                content_parts.append(f"=== {item_title} ===\n{truncated_content}\n")
        
        if not content_parts:
            self.logger.warning("沒有找到足夠的內容進行摘要")
            return None
            
        # 組合所有內容
        combined_content = "\n".join(content_parts)
        
        # 獲取附錄內容作為參考
        appendix_content = filing_data.get('appendix', '') or ''
        if len(appendix_content) > 2000:  # 限制附錄長度
            appendix_content = appendix_content[:2000] + "...(附錄已截斷)"
        
        # 創建專業的摘要提示詞（參考gpt_summarizer.py的風格）
        prompt = f"""
請為以下 10-K 檔案內容提供全面且專業的摘要分析。請嚴格遵循以下要求：

**重要原則：**
1. 如果原文有具體數據，必須在摘要中保留，並提供支持數據的表格或數字
2. 如果需要從附錄中查找相關資料，請一併整合到摘要中
3. 只回答有明確根據的內容，沒有信心的不要回答
4. 每個重點都要說明理由和數據支持
5. 必須保留所有財務數據、比率、百分比
6. 說明數據的時間範圍和比較基準
7. 對重要變化提供分析和解釋
8. 只基於實際數據進行摘要，不要推測

**請按照以下結構組織回答：**

## 🏢 業務概況 (Business Overview)
- 公司主要業務模式、產品和服務（包含具體數據）
- 市場地位和競爭優勢（引用原文數據支持）
- 重要的業務變化或策略（必須有數據支持）
- 主要業務部門和收入貢獻（保留所有百分比和金額）

## 📊 財務表現 (Financial Performance)
- 收入和獲利能力分析（保留所有具體數字）
- 重要的財務指標和趨勢（包含年度比較數據）
- 現金流狀況和資產負債情況
- 與前一年度的具體比較數據

## ⚠️ 風險因素 (Risk Factors)
- 主要風險因素及其潛在影響程度
- 對業務的量化影響（如有數據）
- 管理層的應對策略和措施
- 行業特定風險和監管風險

## 🔮 未來展望 (Future Outlook)
- 管理層對未來的具體預測和目標
- 重要的計劃投資金額和時間表
- 市場機會和挑戰的量化分析
- 預期的財務影響和業務發展

**品質要求：**
- 保留所有重要的數字和百分比
- 突出年度變化和趨勢
- 基於實際內容，不要推測
- 使用清晰的中文表達
- 確保每個陳述都有原文數據支持

**10-K 檔案主要內容：**
{combined_content}

**附錄參考內容（如需要）：**
{appendix_content}

請根據以上內容提供專業的摘要分析：
"""
        
        return self.call_gpt4o_api(prompt)
        
    def create_summary_record(self, filing_data: Dict) -> int:
        """
        創建摘要記錄
        
        Args:
            filing_data: 原始檔案資料
            
        Returns:
            新創建的摘要記錄 ID
        """
        connection = self.get_db_connection()
        cursor = connection.cursor()
        
        try:
            insert_query = """
            INSERT INTO ten_k_filings_summary (
                original_filing_id, file_name, company_name, report_date, 
                summary_model, processing_status
            ) VALUES (%s, %s, %s, %s, 'gpt-4o', 'processing')
            """
            
            cursor.execute(insert_query, (
                filing_data['id'],
                filing_data['file_name'],
                filing_data['company_name'],
                filing_data['report_date']
            ))
            
            summary_id = cursor.lastrowid
            connection.commit()
            return summary_id
            
        finally:
            cursor.close()
            connection.close()
            
    def create_item_summary(self, item_content: str, item_name: str, item_title: str) -> Optional[str]:
        """
        為單個項目創建摘要
        
        Args:
            item_content: 項目內容
            item_name: 項目名稱 (如 item_1, item_1a)
            item_title: 項目標題 (如 Business, Risk Factors)
            
        Returns:
            項目摘要內容或 None
        """
        if not item_content or len(item_content.strip()) < 100:
            return None
            
        # 截取內容避免超出API限制
        truncated_content = item_content[:8000]  # 單個項目允許更多內容
        if len(item_content) > 8000:
            truncated_content += "...(內容已截斷)"
        
        # 根據項目類型創建特定的提示詞
        item_prompts = {
            'item_1': f"""
請為以下 10-K 檔案的 {item_title} 部分提供專業摘要。重點關注：
1. 公司主要業務模式和產品服務
2. 市場地位和競爭策略
3. 業務部門和收入結構
4. 重要的業務變化和發展
請保留所有具體數據和財務指標。

內容：
{truncated_content}
""",
            'item_1a': f"""
請為以下 10-K 檔案的 {item_title} 部分提供專業摘要。重點關注：
1. 主要風險因素及其影響程度
2. 財務和營運風險
3. 市場和競爭風險
4. 監管和法律風險
請量化風險影響並說明管理層應對措施。

內容：
{truncated_content}
""",
            'item_7': f"""
請為以下 10-K 檔案的 {item_title} 部分提供專業摘要。重點關注：
1. 財務表現分析和趨勢
2. 營收和獲利能力變化
3. 現金流和資本結構
4. 管理層對未來的展望
請保留所有財務數據和比較分析。

內容：
{truncated_content}
""",
            'item_8': f"""
請為以下 10-K 檔案的 {item_title} 部分提供專業摘要。重點關注：
1. 主要財務報表項目
2. 會計政策和重要估計
3. 財務狀況變化
4. 關鍵財務比率
請保留所有數字和財務指標。

內容：
{truncated_content}
""",
            'default': f"""
請為以下 10-K 檔案的 {item_title} 部分提供專業且精簡的摘要。
重點提取關鍵信息，保留重要數據，用清晰的中文表達。

內容：
{truncated_content}
"""
        }
        
        # 選擇適當的提示詞
        prompt = item_prompts.get(item_name, item_prompts['default'])
        
        return self.call_gpt4o_api(prompt)

    def get_available_items(self, filing_data: Dict) -> List[tuple]:
        """
        獲取檔案中所有有內容的項目
        
        Args:
            filing_data: 檔案資料
            
        Returns:
            [(item_name, item_title, content_length), ...] 的列表
        """
        # 定義所有項目及其標題
        all_items = [
            ('item_1', 'Business'),
            ('item_1a', 'Risk Factors'),
            ('item_1b', 'Unresolved Staff Comments'),
            ('item_2', 'Properties'),
            ('item_3', 'Legal Proceedings'),
            ('item_4', 'Mine Safety'),
            ('item_5', 'Market for Stock'),
            ('item_6', 'Selected Financial Data'),
            ('item_7', 'Management Discussion & Analysis'),
            ('item_7a', 'Market Risk'),
            ('item_8', 'Financial Statements'),
            ('item_9', 'Changes and Disagreements'),
            ('item_9a', 'Controls and Procedures'),
            ('item_9b', 'Other Information'),
            ('item_10', 'Directors and Officers'),
            ('item_11', 'Executive Compensation'),
            ('item_12', 'Security Ownership'),
            ('item_13', 'Relationships and Transactions'),
            ('item_14', 'Principal Accountant'),
            ('item_15', 'Exhibits'),
            ('item_16', 'Form 10-K Summary')
        ]
        
        available_items = []
        
        for item_name, item_title in all_items:
            content = filing_data.get(item_name, '')
            if content and len(str(content).strip()) > 100:  # 只處理有實質內容的項目
                available_items.append((item_name, item_title, len(str(content))))
                
        return available_items

    def update_summary_content(self, summary_id: int, item_summaries: Dict[str, str], total_items: int):
        """
        更新摘要內容 - 支援多個項目摘要
        
        Args:
            summary_id: 摘要記錄ID
            item_summaries: 項目摘要字典 {item_name: summary_content}
            total_items: 總項目數量
        """
        connection = self.get_db_connection()
        cursor = connection.cursor()
        
        try:
            # 構建更新查詢 - 動態設置各個項目摘要欄位
            update_fields = []
            update_values = []
            
            # 處理每個項目摘要
            for item_name, summary_content in item_summaries.items():
                if summary_content:  # 只更新有內容的摘要
                    update_fields.append(f"{item_name}_summary = %s")
                    update_values.append(summary_content)
            
            if not update_fields:
                self.logger.warning("沒有摘要內容需要更新")
                return
                
            # 添加統計和狀態欄位
            update_fields.extend([
                "items_processed_count = %s",
                "total_items_count = %s", 
                "processing_status = 'completed'",
                "summary_completed_at = CURRENT_TIMESTAMP",
                "updated_at = CURRENT_TIMESTAMP"
            ])
            
            update_values.extend([len(item_summaries), total_items, summary_id])
            
            update_query = f"""
            UPDATE ten_k_filings_summary 
            SET {', '.join(update_fields)}
            WHERE id = %s
            """
            
            cursor.execute(update_query, update_values)
            connection.commit()
            
            self.logger.info(f"成功更新 {len(item_summaries)} 個項目摘要")
            
        finally:
            cursor.close()
            connection.close()
            
    def get_filing_data(self, filing_id: int) -> Optional[Dict]:
        """獲取檔案數據"""
        connection = self.get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            query = """
            SELECT * FROM ten_k_filings 
            WHERE id = %s
            """
            cursor.execute(query, (filing_id,))
            return cursor.fetchone()
            
        finally:
            cursor.close()
            connection.close()
            
    def process_filing(self, filing_id: int, ticker: str) -> bool:
        """
        處理單個檔案的摘要 - 對每個項目進行個別摘要
        
        Args:
            filing_id: 檔案ID
            ticker: 股票代號
            
        Returns:
            處理是否成功
        """
        start_time = time.time()
        
        # 獲取檔案數據
        filing_data = self.get_filing_data(filing_id)
        if not filing_data:
            self.logger.error(f"找不到檔案ID: {filing_id}")
            return False
            
        self.logger.info(f"開始處理: {filing_data['file_name']}")
        self.logger.info(f"   股票代號: {ticker}")
        self.logger.info(f"   報告日期: {filing_data['report_date']}")
        
        # 獲取所有有內容的項目
        available_items = self.get_available_items(filing_data)
        self.logger.info(f"   發現 {len(available_items)} 個有內容的項目")
        
        for item_name, item_title, content_length in available_items:
            self.logger.info(f"     - {item_name} ({item_title}): {content_length} 字符")
        
        if not available_items:
            self.logger.warning("沒有找到足夠的內容進行摘要")
            return False
        
        # 檢查是否已有摘要
        connection = self.get_db_connection()
        cursor = connection.cursor()
        
        try:
            check_query = """
            SELECT id, processing_status FROM ten_k_filings_summary 
            WHERE original_filing_id = %s
            """
            cursor.execute(check_query, (filing_id,))
            existing = cursor.fetchone()
            
            if existing:
                if existing[1] == 'completed':
                    self.logger.info(f"   檔案已有完成的摘要，跳過處理")
                    return True
                else:
                    # 如果有未完成的記錄，使用現有的summary_id
                    summary_id = existing[0]
                    self.logger.info(f"   找到未完成的摘要記錄，繼續處理 (ID: {summary_id})")
            else:
                # 創建新的摘要記錄
                summary_id = self.create_summary_record(filing_data)
                self.logger.info(f"   創建新的摘要記錄 (ID: {summary_id})")
                
        finally:
            cursor.close()
            connection.close()
        
        # 對每個項目進行個別摘要
        item_summaries = {}
        successful_items = 0
        
        for i, (item_name, item_title, content_length) in enumerate(available_items, 1):
            self.logger.info(f"   處理項目 {i}/{len(available_items)}: {item_name} ({item_title})")
            
            try:
                item_content = filing_data.get(item_name, '')
                if item_content:
                    summary = self.create_item_summary(item_content, item_name, item_title)
                    
                    if summary:
                        item_summaries[item_name] = summary
                        successful_items += 1
                        self.logger.info(f"     ✅ {item_name} 摘要完成")
                    else:
                        self.logger.warning(f"     ❌ {item_name} 摘要失敗")
                
                # 避免API限流 - 每個項目之間延遲
                if i < len(available_items):
                    time.sleep(1)
                    
            except Exception as e:
                self.logger.error(f"     ❌ {item_name} 摘要過程出錯: {e}")
                continue
        
        if item_summaries:
            # 更新所有項目摘要到資料庫
            self.update_summary_content(summary_id, item_summaries, len(available_items))
            
            processing_time = int(time.time() - start_time)
            self.logger.info(f"   摘要完成！成功處理 {successful_items}/{len(available_items)} 個項目")
            self.logger.info(f"   總處理時間: {processing_time} 秒")
            return True
        else:
            self.logger.error(f"   所有項目摘要都失敗了")
            return False
            
    def run_batch_processing(self, ticker: str, filing_ids: List[int]):
        """
        批次處理多個檔案
        
        Args:
            ticker: 股票代號
            filing_ids: 檔案ID列表
        """
        self.logger.info(f"開始 GPT-4O 摘要批次處理: {ticker}")
        self.logger.info(f"待處理檔案: {filing_ids}")
        
        success_count = 0
        
        for i, filing_id in enumerate(filing_ids, 1):
            try:
                self.logger.info(f"\n--- 處理進度: {i}/{len(filing_ids)} ---")
                
                if self.process_filing(filing_id, ticker):
                    success_count += 1
                    
                # 避免 API 限流
                if i < len(filing_ids):
                    time.sleep(2)
                    
            except Exception as e:
                self.logger.error(f"處理檔案失敗: ID {filing_id}, 錯誤: {e}")
                continue
                
        self.logger.info(f"\n批次處理完成!")
        self.logger.info(f"成功: {success_count}/{len(filing_ids)}")
        
        return success_count > 0


def main():
    """主函數"""
    if len(sys.argv) != 3:
        print("使用方法: python o3_summarizer.py <ticker> <filing_ids>")
        print("範例: python o3_summarizer.py AAPL 1,2,3")
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    filing_ids_str = sys.argv[2]
    
    try:
        filing_ids = [int(id.strip()) for id in filing_ids_str.split(',')]
    except ValueError:
        print("錯誤: filing_ids 必須是逗號分隔的數字")
        sys.exit(1)
    
    # 創建摘要處理器
    summarizer = TenKGPT4OSummarizer()
    
    # 運行批次處理
    success = summarizer.run_batch_processing(ticker, filing_ids)
    
    if success:
        print(f"摘要處理成功完成: {ticker}")
        sys.exit(0)
    else:
        print(f"摘要處理失敗: {ticker}")
        sys.exit(1)


if __name__ == "__main__":
    main() 