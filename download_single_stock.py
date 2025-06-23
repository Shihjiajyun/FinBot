#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
單一股票 10-K 財報下載器
基於 apple.py 的邏輯，下載指定股票代號的近5年 10-K 財報
"""

import sys
import os

# 設定 stdout 編碼，避免 Windows 下的 Unicode 錯誤
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from secedgar import filings, FilingType
from datetime import datetime, timedelta
from pathlib import Path
import time
import argparse

def download_stock_filings(ticker):
    """
    下載指定股票的 10-K 財報
    
    Args:
        ticker: 股票代號 (如 'AAPL', 'MSFT')
    """
    
    USER_AGENT = "JIA-JYUN SHIH (shihjiajyun@gmail.com)"
    
    # 設定時間範圍：近5年
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5*365)  # 5年前
    
    # 基礎下載目錄
    base_dir = Path("./downloads")
    base_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"開始下載 {ticker} 的 10-K 財報")
    print(f"時間範圍: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
    
    try:
        # 先檢查是否已有檔案
        target_dir = base_dir / ticker / "10-K"
        if target_dir.exists():
            existing_files = list(target_dir.glob("*.txt"))
            if len(existing_files) > 0:
                print(f"發現已有 {len(existing_files)} 個 10-K 檔案，跳過下載")
                for file_path in existing_files:
                    print(f"   - {file_path.name}")
                print(f"使用現有的 {len(existing_files)} 個 10-K 檔案")
                return True
        
        print(f"正在下載 10-K 財報...")
        
        # 創建 filings 物件
        filing = filings(
            cik_lookup=ticker,
            filing_type=FilingType.FILING_10K,
            start_date=start_date,
            end_date=end_date,
            user_agent=USER_AGENT
        )
        
        # 下載到指定目錄
        filing.save(base_dir)
        
        print(f"{ticker} 的 10-K 財報下載完成")
        
        # 檢查下載的檔案 - 修復：檢查兩種可能的目錄結構
        # 1. 檢查新版 secedgar 的直接下載目錄
        target_dir = base_dir / ticker / "10-K"
        
        # 2. 檢查舊版 secedgar 的中間目錄
        sec_edgar_dir = base_dir / "sec-edgar-filings" / ticker / "10-K"
        
        downloaded_files = []
        
        # 先檢查直接目錄
        if target_dir.exists():
            downloaded_files = list(target_dir.glob("*.txt"))
            print(f"在目標目錄找到 {len(downloaded_files)} 個檔案")
            for file_path in downloaded_files:
                print(f"   - {file_path.name}")
        
        # 再檢查 sec-edgar-filings 目錄並移動檔案
        elif sec_edgar_dir.exists():
            temp_files = list(sec_edgar_dir.rglob("*.txt"))
            print(f"在 sec-edgar-filings 目錄找到 {len(temp_files)} 個檔案")
            
            # 移動檔案到目標目錄
            target_dir.mkdir(parents=True, exist_ok=True)
            
            for file_path in temp_files:
                target_path = target_dir / file_path.name
                if not target_path.exists():
                    file_path.rename(target_path)
                    print(f"   - 移動: {file_path.name}")
                    downloaded_files.append(target_path)
                else:
                    print(f"   - 跳過: {file_path.name} (已存在)")
                    downloaded_files.append(target_path)
        else:
            print(f"未找到下載的檔案目錄")
            print(f"檢查的路徑: {target_dir} 和 {sec_edgar_dir}")
            return False
        
        if len(downloaded_files) > 0:
            print(f"成功下載 {len(downloaded_files)} 個 10-K 檔案到 {target_dir}")
        else:
            print(f"沒有找到任何 10-K 檔案")
            
        return True
        
    except Exception as e:
        print(f"下載 {ticker} 時發生錯誤: {e}")
        return False

def main():
    """主函數"""
    if len(sys.argv) != 2:
        print("用法: python download_single_stock.py <股票代號>")
        print("範例: python download_single_stock.py AAPL")
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    
    print(f"開始下載 {ticker} 的 10-K 財報")
    
    success = download_stock_filings(ticker)
    
    if success:
        print(f"{ticker} 下載完成!")
        sys.exit(0)
    else:
        print(f"{ticker} 下載失敗!")
        sys.exit(1)

if __name__ == "__main__":
    main() 