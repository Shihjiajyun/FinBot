# FinBot 股票查詢功能 - 設置指南

## 📋 功能說明

新增的股票查詢功能讓用戶可以：
- 輸入股票代號查詢詳細財務資訊
- 查看實時股價、市值、PE比等關鍵指標
- 快速選擇熱門股票
- 直接將股票資訊導入 FinBot 進行深度分析

## 🚀 安裝步驟

### 1. 安裝 Python 依賴項

```bash
cd FinBot
pip install -r requirements.txt
```

或手動安裝：
```bash
pip install yfinance pandas numpy requests
```

### 2. 創建數據庫表

執行以下 SQL 文件來創建所需的數據庫表：

```sql
-- 在你的 MySQL 數據庫中執行
source create_stock_table.sql;
```

或手動執行SQL語句創建表。

### 3. 驗證 Python 腳本

測試 Python 腳本是否正常工作：

```bash
cd FinBot
python stock_info.py AAPL
```

應該會返回 Apple 的股票資訊 JSON 數據。

### 4. 檢查文件權限

確保 PHP 可以執行 Python 腳本：

```bash
chmod +x stock_info.py
```

## 📁 新增文件說明

- `stock_info.py` - Python 腳本，使用 yfinance 獲取股票資訊
- `php/stock_api.php` - PHP API，處理前端的股票查詢請求
- `create_stock_table.sql` - 數據庫表創建腳本
- `requirements.txt` - Python 依賴項清單

## 🎯 使用方法

1. 登入 FinBot 系統
2. 點擊左側導覽列的「股票查詢」按鈕
3. 輸入股票代號（如：AAPL, TSLA, MSFT）
4. 查看詳細的股票資訊
5. 點擊「詢問 FinBot 關於此股票」直接進行深度分析

## 🔧 故障排除

### Python 腳本無法執行
- 確認 Python 已安裝且在系統 PATH 中
- 檢查 `yfinance` 是否正確安裝
- 確認網路連線正常（需要連接 Yahoo Finance API）

### 數據庫錯誤
- 確認數據庫表已正確創建
- 檢查數據庫連線設定

### 權限問題
- 確認 PHP 有執行 Python 腳本的權限
- 檢查文件路徑是否正確

## 📈 支持的股票市場

目前支持的股票代號格式：
- 美股：AAPL, MSFT, GOOGL 等
- 可透過 Yahoo Finance 查詢的所有股票

## 💡 功能特色

✅ **實時數據** - 從 Yahoo Finance 獲取最新股票資訊  
✅ **豐富指標** - 包含市值、PE比、EPS、股息等關鍵財務指標  
✅ **使用者友善** - 直觀的界面設計  
✅ **歷史記錄** - 自動儲存查詢歷史  
✅ **無縫整合** - 可直接轉換為 FinBot 對話分析  

## 🔐 安全性

- 輸入驗證：只允許有效的股票代號格式
- 用戶認證：需要登入才能使用
- 數據清理：防止 SQL 注入和 XSS 攻擊

## 📊 熱門股票清單

系統預設包含以下熱門股票：

**科技股**
- AAPL (Apple)
- MSFT (Microsoft) 
- GOOGL (Alphabet)
- AMZN (Amazon)
- TSLA (Tesla)
- META (Meta)
- NVDA (NVIDIA)
- NFLX (Netflix)

**金融股**
- JPM (JPMorgan Chase)
- V (Visa)

**其他**
- JNJ (Johnson & Johnson)
- KO (Coca-Cola)

## 📞 技術支援

如有問題，請檢查：
1. Python 環境是否正確設置
2. 網路連線是否正常
3. 數據庫表是否存在
4. PHP 錯誤日誌

---

🎉 **現在您可以開始使用 FinBot 的股票查詢功能了！** 