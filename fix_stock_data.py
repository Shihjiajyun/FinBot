#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修復股票數據腳本 - 專門解決數據抓取不完整的問題
供PHP調用使用
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from improved_stock_analyzer import ImprovedStockAnalyzer
import json

def main():
    """主函數 - 修復指定股票的數據"""
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "缺少股票代號參數"}))
        return
    
    ticker = sys.argv[1].upper()
    
    try:
        # 創建分析器實例
        analyzer = ImprovedStockAnalyzer()
        
        # 分析股票
        result = analyzer.analyze_stock(ticker)
        
        if result:
            # 計算數據完整度（使用有數據的最新年份）
            valid_years = [year for year, data in result.items() if data and any(v is not None for v in data.values())]
            if valid_years:
                latest_year = max(valid_years)
                latest_data = result[latest_year]
                filled_fields = len([v for v in latest_data.values() if v is not None])
                total_fields = 23
                completeness = (filled_fields / total_fields) * 100
            else:
                latest_year = None
                completeness = 0
            
            print(json.dumps({
                "success": True,
                "ticker": ticker,
                "years_processed": len([year for year, data in result.items() if data]),
                "data_completeness": round(completeness, 1),
                "latest_year": latest_year,
                "message": f"{ticker} 數據修復完成，數據完整度: {completeness:.1f}%"
            }))
        else:
            print(json.dumps({
                "success": False,
                "ticker": ticker,
                "error": "數據抓取失敗"
            }))
            
    except Exception as e:
        print(json.dumps({
            "success": False,
            "ticker": ticker,
            "error": str(e)
        }))

if __name__ == "__main__":
    main() 