### 📄 程式功能說明

#### 1️⃣ `dual_source_analyzer.py`
- **存入表格**：`filings`
- **功能**：寫入財務數據（包含收入、淨利潤、現金流、資產負債表等）
- **數據來源**：Macrotrends 與 Yahoo Finance
- **執行時機**：需要分析新股票時

#### 2️⃣ `parse_single_stock.py`
- **存入表格**：`ten_k_filings`
- **功能**：解析下載的 10-K 財報，拆解為各個項目（Item 1、Item 1A、Item 2 等）並存入
- **數據內容**：10-K 財報各段落
- **執行時機**：完成 10-K 財報下載後

#### 3️⃣ `improved_stock_analyzer.py`
- **存入表格**：`filings`
- **功能**：補強並更新財務數據
- **數據來源**：主要來自 Yahoo Finance
- **執行時機**：用作資料修復或補強工具

#### 4️⃣ `summarize_single_stock.py`
- **存入表格**：`ten_k_filings_summary`
- **功能**：生成 10-K 財報的 AI 摘要
- **數據內容**：針對財報內容的摘要與重點分析

#### 5️⃣ `gpt_summarizer.py` & `o3_summarizer.py`
- **存入表格**：`ten_k_filings_summary`
- **功能**：利用不同 AI 模型生成財報摘要
