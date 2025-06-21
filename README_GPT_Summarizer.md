# 10-K Filing GPT Summarizer 使用說明

這個工具可以將已解析的 10-K 檔案內容使用 GPT 進行智能摘要，並將結果存入專門的摘要資料表中。

## 功能特色

- ✅ **智能摘要**：針對不同類型的 Item 使用不同的摘要策略
- ✅ **附錄整合**：自動結合附錄內容進行更完整的摘要
- ✅ **數據保留**：確保重要數據和支持表格在摘要中保留
- ✅ **嚴格驗證**：只對有明確根據的內容進行摘要
- ✅ **批次處理**：支援大量檔案的自動化處理
- ✅ **進度追蹤**：完整的處理狀態和時間記錄

## 檔案結構

```
FinBot/
├── create_ten_k_summary_table.sql  # 摘要資料表創建語法
├── gpt_summarizer.py               # GPT 摘要主程式
├── README_GPT_Summarizer.md        # 本使用說明
└── gpt_summarizer.log              # 運行日誌檔案
```

## 安裝需求

### Python 套件

```bash
pip install mysql-connector-python openai
```

### 資料庫準備

1. 確保已有原始的 `ten_k_filings` 表
2. 執行摘要資料表創建語法：

```bash
mysql -u myuser -p finbot_db < create_ten_k_summary_table.sql
```

## 摘要資料表結構

### ten_k_filings_summary 主表

| 欄位名 | 類型 | 說明 |
|--------|------|------|
| id | INT | 摘要表主鍵 |
| original_filing_id | INT | 關聯原始檔案 ID |
| file_name | VARCHAR(255) | 檔案名稱 |
| company_name | VARCHAR(255) | 公司名稱 |
| report_date | DATE | 報告日期 |
| summary_model | VARCHAR(50) | GPT 模型版本 |
| processing_status | ENUM | 處理狀態 (pending/processing/completed/failed) |
| processing_notes | TEXT | 處理備註 |
| item_1_summary | TEXT | Item 1 摘要（含附錄支持數據） |
| item_1a_summary | TEXT | Item 1A 摘要 |
| ... | ... | 其他 Item 摘要欄位 |
| items_processed_count | INT | 已完成摘要的 Item 數量 |
| processing_time_seconds | INT | 處理耗時 |
| created_at | TIMESTAMP | 創建時間 |
| updated_at | TIMESTAMP | 更新時間 |

### 輔助視圖

- **ten_k_summary_progress**：查看摘要進度
- **ten_k_summary_stats**：統計摘要完成情況

## 使用方法

### 1. 配置設定

編輯 `gpt_summarizer.py` 中的配置：

```python
# 資料庫配置
db_config = {
    'host': 'localhost',
    'user': 'myuser',          # 替換為您的資料庫用戶
    'password': 'mypassword',  # 替換為您的資料庫密碼
    'database': 'finbot_db',
    'charset': 'utf8mb4'
}

# OpenAI API 金鑰
openai_api_key = "your-openai-api-key-here"  # 替換為您的實際金鑰
```

### 2. 執行摘要處理

```bash
cd FinBot
python gpt_summarizer.py
```

### 3. 查看處理結果

程式執行後會顯示類似以下的輸出：

```
🚀 開始 GPT 摘要批次處理
📋 找到 3 個待處理檔案

--- 處理進度: 1/3 ---
📄 開始處理: 0000320193-24-000123.txt
   📊 公司: Apple Inc.
   📅 報告日期: 2024-09-28
開始摘要 item_1
✅ item_1 摘要完成
開始摘要 item_1a
✅ item_1a 摘要完成
   ✅ 完成摘要: 14/21 個Items
   ⏱️ 處理時間: 180 秒

🎉 批次處理完成!
✅ 成功: 3/3
```

## GPT 摘要策略

### 不同 Item 的摘要重點

| Item 類型 | 摘要重點 | 附錄整合 |
|-----------|----------|----------|
| **Item 1 (Business)** | 業務模式、產品服務、市場地位、數據支持 | ✅ 整合業務相關附錄 |
| **Item 1A (Risk Factors)** | 風險量化、影響程度、歷史數據 | ❌ 通常不需要 |
| **財務相關** (5,6,7,7A,8,14) | 財務數據、比率、時間序列、變化分析 | ✅ 整合財務表格 |
| **治理相關** (10,11,12) | 人員資訊、薪酬數據、治理變化 | ✅ 整合治理表格 |
| **其他 Items** | 重要數據、趨勢變化、具體事實 | ✅ 如有相關則整合 |

### 摘要原則

1. **數據保留**：所有具體數字、百分比、金額必須保留
2. **表格整合**：從附錄中提取相關支持數據
3. **嚴格驗證**：沒有根據的內容不寫入摘要
4. **結構化輸出**：提供清晰的分段和重點

## 查詢摘要結果

### 查看摘要進度

```sql
SELECT * FROM ten_k_summary_progress;
```

### 查看特定公司的摘要

```sql
SELECT 
    file_name,
    report_date,
    processing_status,
    item_1_summary,
    item_7_summary
FROM ten_k_filings_summary 
WHERE company_name = 'Apple Inc.' 
ORDER BY report_date DESC;
```

### 比較原文和摘要長度

```sql
SELECT 
    s.file_name,
    s.report_date,
    CHAR_LENGTH(o.item_1) as original_length,
    CHAR_LENGTH(s.item_1_summary) as summary_length,
    ROUND(CHAR_LENGTH(s.item_1_summary) / CHAR_LENGTH(o.item_1) * 100, 2) as compression_ratio
FROM ten_k_filings_summary s
JOIN ten_k_filings o ON s.original_filing_id = o.id
WHERE s.item_1_summary IS NOT NULL 
AND o.item_1 IS NOT NULL
ORDER BY s.report_date DESC;
```

### 統計摘要完成情況

```sql
SELECT * FROM ten_k_summary_stats;
```

## 進階配置

### 自訂 GPT 模型

```python
# 在 call_gpt_api 方法中修改
response = self.openai_client.chat.completions.create(
    model="gpt-4-turbo",  # 或其他模型
    # ... 其他參數
)
```

### 調整批次大小

```python
# 限制處理檔案數量
summarizer.run_batch_processing(max_filings=5)

# 處理所有待處理檔案
summarizer.run_batch_processing()
```

### 自訂提示詞

在 `summary_prompts` 字典中修改各種 Item 的提示詞模板。

## 成本估算

### OpenAI API 成本

以 GPT-4 為例：
- 每個 Item 平均消耗：15,000 tokens
- 每個 10-K 檔案（16 Items）：約 240,000 tokens
- 估算成本：每檔案約 $7.20 USD

### 處理時間

- 每個 Item：平均 8-15 秒
- 每個檔案：約 3-5 分鐘
- 100 個檔案：約 5-8 小時

## 錯誤處理

### 常見問題

1. **API 限流**：程式內建重試機制和延遲處理
2. **資料庫連接**：自動重連和錯誤記錄
3. **內容過長**：自動截斷以符合 GPT 限制
4. **網路中斷**：支援斷點續傳

### 監控日誌

```bash
tail -f gpt_summarizer.log
```

## 最佳實踐

1. **小批次測試**：先處理少量檔案確認結果品質
2. **定期備份**：處理前備份資料庫
3. **監控成本**：密切關注 OpenAI API 使用量
4. **品質檢查**：定期抽查摘要品質
5. **分時處理**：避開 API 高峰時段

## 品質驗證

### 摘要品質指標

```sql
-- 檢查摘要長度合理性
SELECT 
    AVG(CHAR_LENGTH(item_1_summary)) as avg_summary_length,
    MIN(CHAR_LENGTH(item_1_summary)) as min_summary_length,
    MAX(CHAR_LENGTH(item_1_summary)) as max_summary_length
FROM ten_k_filings_summary 
WHERE item_1_summary IS NOT NULL;

-- 檢查數據保留情況（以收入為例）
SELECT 
    file_name,
    report_date,
    CASE 
        WHEN item_7_summary LIKE '%revenue%' OR item_7_summary LIKE '%收入%' 
        THEN '包含收入資訊' 
        ELSE '可能遺漏收入資訊' 
    END as revenue_check
FROM ten_k_filings_summary 
WHERE item_7_summary IS NOT NULL;
```

## 故障排除

### 處理失敗的檔案

```sql
-- 查看失敗的處理
SELECT * FROM ten_k_filings_summary 
WHERE processing_status = 'failed';

-- 重新處理失敗的檔案
DELETE FROM ten_k_filings_summary 
WHERE processing_status = 'failed';
-- 然後重新運行程式
```

### 更新現有摘要

```sql
-- 刪除特定檔案的摘要以重新處理
DELETE FROM ten_k_filings_summary 
WHERE file_name = '0000320193-24-000123.txt';
```

## 注意事項

1. 確保 OpenAI API 金鑰有效且有足夠餘額
2. 處理大量檔案時注意網路穩定性
3. 定期檢查摘要品質並調整提示詞
4. 遵守 OpenAI 使用條款和限制
5. 注意資料隱私和安全要求 