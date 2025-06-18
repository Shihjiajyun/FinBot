#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os

print("Python is working!")
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")
print(f"Python executable: {sys.executable}")

# 測試基本模組
try:
    import pathlib
    print("✅ pathlib OK")
except ImportError as e:
    print(f"❌ pathlib failed: {e}")

try:
    import datetime
    print("✅ datetime OK")
except ImportError as e:
    print(f"❌ datetime failed: {e}")

# 測試高級模組
try:
    import secedgar
    print("✅ secedgar OK")
except ImportError as e:
    print(f"❌ secedgar missing: {e}")

try:
    import mysql.connector
    print("✅ mysql.connector OK")  
except ImportError as e:
    print(f"❌ mysql.connector missing: {e}")

print("Test completed!") 