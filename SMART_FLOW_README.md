# FinBot 智能財報獲取流程

## 流程概述

FinBot 現在具備了智能財報獲取功能，可以根據用戶問題自動下載和處理所需的財報數據。整個流程包含以下步驟：

## 完整流程

### 1. 用戶輸入問題
- 用戶使用格式：`[股票代碼] 問題內容`
- 例如：`[AAPL] 2023年的營收表現如何？`

### 2. 問題歷史檢查
- 系統首先檢查是否有相同的問題已經被問過
- 如果找到歷史記錄，直接返回之前的答案
- 避免重複處理，提高響應速度

### 3. GPT 問題分析
- 系統讓GPT分析問題需要什麼類型的財報數據
- GPT會判斷需要：
  - Form 4（內部人交易數據）
  - 10-K 特定年份和項目（年報數據）
  - 13F-HR 特定年份（機構持股數據）

### 4. 財報數據完整性檢查
- 系統檢查資料庫是否已有所需的財報數據
- 根據股票代碼和年份進行精確匹配
- 識別缺失的數據類型和年份

### 5. 自動下載缺失財報（如果需要）
- 如果發現缺失數據，系統會：
  - 調用 `download_filings.py` 下載所需財報
  - 調用 `process_filings.py` 處理並存儲到資料庫
  - 記錄整個過程的日誌

### 6. GPT 智能分析
- 使用完整的財報數據進行分析
- 提供專業、準確的財務分析答案
- 包含具體數字和專業解釋

## 技術架構

### 核心文件

1. **api_improved.php** - 主要API邏輯
   - `handleAsk()` - 處理用戶問題的主函數
   - `checkQuestionHistory()` - 檢查問題歷史
   - `analyzeQuestionWithGPT()` - GPT問題分析
   - `checkMissingFilingData()` - 檢查缺失數據
   - `downloadAndProcessFilings()` - 自動下載處理

2. **download_filings.py** - 財報下載腳本
   ```bash
   python download_filings.py AAPL 10-K,4 2023,2024
   ```

3. **process_filings.py** - 財報處理腳本
   ```bash
   python process_filings.py AAPL
   ```

### 資料庫結構

- **filings** 表：存儲所有財報數據
- **questions** 表：存儲問題和答案
- **conversations** 表：管理對話記錄

## 支援的股票

目前系統支援以下股票代碼：
- AAPL (Apple Inc.)
- AMZN (Amazon.com Inc.)
- MSFT (Microsoft Corp.)
- TSLA (Tesla Inc.)
- META (Meta Platforms Inc.)
- GOOGL/GOOG (Alphabet Inc.)
- NVDA (NVIDIA Corp.)

## 使用範例

### 基本問題
```
[AAPL] 2023年的營收表現如何？
[TSLA] 最新季度的毛利率是多少？
[AMZN] 現金流狀況怎麼樣？
```

### 複雜分析
```
[MSFT] 比較2022年和2023年的研發支出變化
[META] 分析最近的風險因素變化
[NVDA] 內部人交易活動如何？
```

## 系統優勢

1. **智能化**：自動判斷所需數據類型
2. **效率高**：重複問題直接返回歷史答案
3. **完整性**：自動補充缺失的財報數據
4. **準確性**：基於真實SEC財報數據分析
5. **可追蹤**：完整的處理日誌記錄

## 日誌和調試

系統會記錄以下信息：
- GPT通信日誌
- 財報下載過程
- 數據處理結果
- 錯誤和警告信息

可以在瀏覽器控制台和服務器日誌中查看詳細信息。

## 錯誤處理

系統會優雅地處理各種錯誤情況：
- 網路連接問題
- 財報下載失敗
- 數據處理錯誤
- GPT API 調用失敗

當發生錯誤時，系統會提供清晰的錯誤信息並建議用戶稍後重試。 