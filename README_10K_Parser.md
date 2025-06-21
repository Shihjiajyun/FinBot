# 10-K Filing Items Parser

這個工具可以解析 AAPL 資料夾中的 10-K 檔案，並將各個 Item 內容分別存入資料表中。

## 功能特色

- ✅ 自動解析 10-K 檔案中的所有 16 個 Item
- ✅ 提取檔案基本資訊（公司名、報告日期、CIK等）
- ✅ 防重複插入機制
- ✅ 完整的錯誤處理
- ✅ 進度顯示和日誌記錄

## 檔案結構

```
FinBot/
├── parse_10k_items.py          # 主要解析程式
├── create_ten_k_table.sql      # 資料表創建語法
├── README_10K_Parser.md        # 使用說明
└── downloads/AAPL/10-K/        # 10-K 檔案存放位置
    ├── 0000320193-24-000123.txt
    ├── 0000320193-23-000106.txt
    └── ...
```

## 安裝需求

```bash
pip install mysql-connector-python
```

## 資料表結構

### ten_k_filings 主表

| 欄位名 | 類型 | 說明 |
|--------|------|------|
| id | INT | 自增主鍵 |
| file_name | VARCHAR(255) | 檔案名稱 |
| document_number | VARCHAR(50) | SEC文件編號 |
| company_name | VARCHAR(255) | 公司名稱 |
| cik | VARCHAR(20) | CIK中央索引鍵 |
| report_date | DATE | 報告期間結束日期 |
| filed_date | DATE | 提交日期 |
| content_hash | VARCHAR(32) | 內容雜湊值（防重複） |
| item_1 | TEXT | Item 1: Business |
| item_1a | TEXT | Item 1A: Risk Factors |
| item_1b | TEXT | Item 1B: Unresolved Staff Comments |
| item_2 | TEXT | Item 2: Properties |
| item_3 | TEXT | Item 3: Legal Proceedings |
| item_4 | TEXT | Item 4: Mine Safety |
| item_5 | TEXT | Item 5: Market for Common Equity |
| item_6 | TEXT | Item 6: Selected Financial Data |
| item_7 | TEXT | Item 7: MD&A |
| item_7a | TEXT | Item 7A: Market Risk |
| item_8 | TEXT | Item 8: Financial Statements |
| item_9 | TEXT | Item 9: Accountant Changes |
| item_9a | TEXT | Item 9A: Controls and Procedures |
| item_9b | TEXT | Item 9B: Other Information |
| item_10 | TEXT | Item 10: Directors and Governance |
| item_11 | TEXT | Item 11: Executive Compensation |
| item_12 | TEXT | Item 12: Security Ownership |
| item_13 | TEXT | Item 13: Related Transactions |
| item_14 | TEXT | Item 14: Accountant Fees |
| item_15 | TEXT | Item 15: Exhibits |
| item_16 | TEXT | Item 16: Form 10-K Summary |
| created_at | TIMESTAMP | 創建時間 |
| updated_at | TIMESTAMP | 更新時間 |

## 使用方法

### 1. 創建資料表

首先執行 SQL 語法創建資料表：

```bash
mysql -u myuser -p finbot_db < create_ten_k_table.sql
```

### 2. 執行解析程式

```bash
cd FinBot
python parse_10k_items.py
```

### 3. 查看結果

程式執行後會顯示類似以下的輸出：

```
🔍 找到 10 個10-K文件
✅ 資料庫連接成功

📄 處理文件: 0000320193-24-000123.txt
   📊 公司: Apple Inc.
   📅 報告日期: 2024-09-28
   🔍 提取Items...
   ✅ 成功提取 14/16 個Items
   ✅ 成功儲存: 0000320193-24-000123.txt

📄 處理文件: 0000320193-23-000106.txt
   📊 公司: Apple Inc.
   📅 報告日期: 2023-09-30
   🔍 提取Items...
   ✅ 成功提取 15/16 個Items
   ✅ 成功儲存: 0000320193-23-000106.txt

🎉 處理完成! 成功: 10/10
✅ 資料庫連接已關閉
```

## 資料查詢範例

### 查看所有已處理的報告

```sql
SELECT * FROM ten_k_summary;
```

### 查看特定年份的業務描述 (Item 1)

```sql
SELECT 
    file_name, 
    report_date, 
    LEFT(item_1, 500) as business_preview 
FROM ten_k_filings 
WHERE YEAR(report_date) = 2024 
AND item_1 IS NOT NULL;
```

### 分析風險因素的變化 (Item 1A)

```sql
SELECT 
    file_name, 
    report_date, 
    CHAR_LENGTH(item_1a) as risk_factors_length,
    LEFT(item_1a, 300) as risk_factors_preview 
FROM ten_k_filings 
WHERE item_1a IS NOT NULL 
ORDER BY report_date DESC;
```

### 統計各項目的完整性

```sql
SELECT 
    COUNT(*) as total_filings,
    SUM(CASE WHEN item_1 IS NOT NULL THEN 1 ELSE 0 END) as has_business,
    SUM(CASE WHEN item_1a IS NOT NULL THEN 1 ELSE 0 END) as has_risk_factors,
    SUM(CASE WHEN item_7 IS NOT NULL THEN 1 ELSE 0 END) as has_md_a,
    SUM(CASE WHEN item_8 IS NOT NULL THEN 1 ELSE 0 END) as has_financials
FROM ten_k_filings;
```

## 技術特點

### 智慧解析
- 使用正規表達式精確匹配各個 Item 標題
- 自動處理 HTML 標籤清理
- 智慧識別 Item 區塊邊界

### 資料處理
- TEXT 欄位長度限制處理（65535字符）
- MD5 雜湊值防重複插入
- 完整的 UTF-8 編碼支援

### 錯誤處理
- 資料庫連接異常處理
- 檔案讀取錯誤處理
- Item 解析異常處理

## 常見問題

### Q: 為什麼某些 Item 沒有被提取到？
A: 可能的原因：
1. 該 Item 在此版本的 10-K 中不存在
2. Item 標題格式與正規表達式不匹配
3. Item 內容為空

### Q: 如何處理重複檔案？
A: 程式會自動檢查內容雜湊值，重複的檔案會被跳過而不會重複插入。

### Q: 可以處理其他公司的 10-K 嗎？
A: 可以！只需修改 `process_aapl_folder()` 方法中的路徑即可。

## 擴展功能

### 處理其他公司
修改 `parse_10k_items.py` 中的路徑：

```python
def process_company_folder(self, company_symbol):
    company_10k_path = Path(__file__).parent / "downloads" / company_symbol / "10-K"
    # ... 其餘邏輯相同
```

### 添加更多欄位
可以在資料表中添加更多分析欄位，如：
- 文件大小
- 處理狀態
- 關鍵字提取
- 情感分析結果

## 注意事項

1. 確保有足夠的資料庫儲存空間（每個 10-K 約 10-20MB）
2. 處理大量檔案時建議分批執行
3. 定期備份資料庫
4. 監控記憶體使用情況 