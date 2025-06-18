#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下載特定股票的財報文件
用法：python download_filings.py AAPL 10-K,4 2023,2024
"""

import sys
import time
from pathlib import Path
from datetime import datetime
from secedgar import filings, FilingType

# 財報類型映射
FILING_TYPE_MAP = {
    "10-K": FilingType.FILING_10K,
    "10-Q": FilingType.FILING_10Q,
    "8-K": FilingType.FILING_8K,
    "4": FilingType.FILING_4,
    "13F-HR": FilingType.FILING_13FHR
}

USER_AGENT = "JIA-JYUN SHIH (shihjiajyun@gmail.com)"

def download_filings(stock_symbol, filing_types, years=None):
    """
    下載指定股票的財報文件
    
    Args:
        stock_symbol: 股票代號，如 'AAPL'
        filing_types: 財報類型列表，如 ['10-K', '4']
        years: 年份列表，如 [2023, 2024]。如果None則下載所有年份
    """
    
    # 設定日期範圍
    if years:
        start_year = min(years)
        end_year = max(years)
        START_DATE = datetime(start_year, 1, 1)
        END_DATE = datetime(end_year, 12, 31)
    else:
        START_DATE = datetime(2015, 1, 1)
        END_DATE = datetime(2025, 12, 31)
    
    # 創建下載目錄 - 使用腳本所在目錄的downloads資料夾
    script_dir = Path(__file__).parent
    base_dir = script_dir / "downloads"
    base_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"[INFO] 下載股票: {stock_symbol}")
    print(f"[INFO] 財報類型: {', '.join(filing_types)}")
    if years:
        print(f"[INFO] 年份範圍: {', '.join(map(str, years))}")
    else:
        print(f"[INFO] 年份範圍: 全部 ({START_DATE.year}-{END_DATE.year})")
    
    success_count = 0
    error_count = 0
    
    for ftype in filing_types:
        try:
            if ftype not in FILING_TYPE_MAP:
                print(f"   [ERROR] 不支援的財報類型: {ftype}")
                error_count += 1
                continue
                
            print(f"   [DOWNLOAD] 下載 {ftype} for {stock_symbol}...")
            
            filing = filings(
                cik_lookup=stock_symbol,
                filing_type=FILING_TYPE_MAP[ftype],
                start_date=START_DATE,
                end_date=END_DATE,
                user_agent=USER_AGENT
            )
            
            # 下載到指定目錄
            filing.save(base_dir)
            time.sleep(0.5)  # 避免請求過於頻繁
            
            print(f"   [SUCCESS] {ftype} 下載成功")
            success_count += 1
            
        except Exception as e:
            error_msg = str(e)
            if ftype == "13F-HR" and ("not found" in error_msg.lower() or "no filings" in error_msg.lower()):
                print(f"   [WARN] {stock_symbol} 沒有 {ftype} 財報（非機構投資者）")
            else:
                print(f"   [ERROR] {stock_symbol} - {ftype} 下載失敗: {e}")
            error_count += 1
    
    print(f"[COMPLETE] 下載完成! 成功: {success_count}, 失敗: {error_count}")
    return success_count > 0

def main():
    """主函數 - 命令行調用"""
    if len(sys.argv) < 3:
        print("使用方法:")
        print("python download_filings.py <股票代號> <財報類型> [年份]")
        print("例如:")
        print("python download_filings.py AAPL 10-K,4 2023,2024")
        print("python download_filings.py MSFT 13F-HR")
        return False
    
    stock_symbol = sys.argv[1].upper()
    filing_types_str = sys.argv[2]
    
    # 解析財報類型
    filing_types = [ftype.strip() for ftype in filing_types_str.split(',')]
    
    # 解析年份（可選）
    years = None
    if len(sys.argv) > 3:
        years_str = sys.argv[3]
        try:
            years = [int(year.strip()) for year in years_str.split(',')]
        except ValueError:
            print("[ERROR] 年份格式錯誤，請使用逗號分隔的數字，如：2023,2024")
            return False
    
    # 執行下載
    return download_filings(stock_symbol, filing_types, years)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 