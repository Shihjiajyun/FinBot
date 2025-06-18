# FinBot Python 環境設置指南

## 錯誤說明

如果您看到錯誤碼 `9009` 或 `Python環境測試失敗`，表示系統無法執行Python腳本。以下是解決方案：

## Windows 環境設置

### 1. 安裝 Python

1. 前往 [Python官網](https://www.python.org/downloads/) 下載最新版本
2. 安裝時**務必勾選** "Add Python to PATH"
3. 安裝完成後，打開命令提示字元測試：
   ```cmd
   python --version
   ```

### 2. 安裝必要的Python套件

打開命令提示字元，執行以下命令：

```cmd
pip install secedgar
pip install mysql-connector-python
pip install pathlib
```

### 3. 測試環境

在FinBot目錄下執行：
```cmd
cd C:\xampp\htdocs\FinBot
python simple_test.py
```

應該看到類似以下輸出：
```
Python is working!
Python version: 3.x.x
✅ pathlib OK
✅ datetime OK
✅ secedgar OK
✅ mysql.connector OK
Test completed!
```

## 常見問題

### 問題1: 'python' 不是內部或外部命令

**解決方案:**
1. 重新安裝Python，確保勾選 "Add Python to PATH"
2. 或手動添加Python到系統PATH：
   - 找到Python安裝路徑（通常是 `C:\Users\用戶名\AppData\Local\Programs\Python\Python3x\`）
   - 將此路徑添加到系統環境變量PATH中

### 問題2: ModuleNotFoundError: No module named 'secedgar'

**解決方案:**
```cmd
pip install secedgar
```

### 問題3: ModuleNotFoundError: No module named 'mysql'

**解決方案:**
```cmd
pip install mysql-connector-python
```

### 問題4: Python版本過舊

**解決方案:**
- 確保使用Python 3.7+
- 如果有多個Python版本，嘗試使用 `python3` 命令

## 手動安裝套件

如果pip不工作，可以手動下載安裝：

1. **secedgar**: 用於下載SEC財報
   ```cmd
   pip install secedgar
   ```

2. **mysql-connector-python**: 用於連接MySQL資料庫
   ```cmd
   pip install mysql-connector-python
   ```

## 驗證安裝

執行以下命令驗證所有套件都已正確安裝：

```cmd
python -c "import secedgar; print('secedgar OK')"
python -c "import mysql.connector; print('mysql.connector OK')"
```

## XAMPP 特定設置

由於您使用XAMPP，確保：

1. Python路徑正確：應該能在任何目錄執行 `python` 命令
2. 工作目錄正確：PHP腳本會從 `FinBot/php/` 目錄調用Python腳本
3. 權限設置：確保PHP有權執行系統命令

## 測試完整流程

設置完成後，您可以測試一個簡單的問題：

```
[AMZN] 2023年營收表現如何？
```

系統應該能：
1. ✅ 通過Python環境測試
2. ✅ 自動下載缺失的財報數據
3. ✅ 處理財報並存儲到資料庫
4. ✅ 提供專業的財務分析

## 如果仍有問題

請檢查Apache錯誤日誌，尋找詳細的錯誤信息：
- 路徑：`C:\xampp\apache\logs\error.log`
- 或在瀏覽器開發者工具的控制台查看相關錯誤 