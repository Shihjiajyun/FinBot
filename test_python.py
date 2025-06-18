#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試Python環境和路徑
"""

import sys
import os
from pathlib import Path

print("🐍 Python 測試腳本")
print(f"Python 版本: {sys.version}")
print(f"當前工作目錄: {os.getcwd()}")
print(f"腳本位置: {__file__}")

# 測試相對路徑
downloads_path = Path("./downloads")
print(f"下載目錄路徑: {downloads_path}")
print(f"下載目錄絕對路徑: {downloads_path.resolve()}")
print(f"下載目錄是否存在: {downloads_path.exists()}")

# 嘗試創建目錄
try:
    downloads_path.mkdir(parents=True, exist_ok=True)
    print("✅ 成功創建/確認下載目錄")
except Exception as e:
    print(f"❌ 創建下載目錄失敗: {e}")

# 測試必要的Python模組
required_modules = ['secedgar', 'mysql.connector', 'pathlib', 'datetime']
for module in required_modules:
    try:
        __import__(module)
        print(f"✅ {module} 模組正常")
    except ImportError as e:
        print(f"❌ {module} 模組缺失: {e}")

print("🎉 測試完成") 