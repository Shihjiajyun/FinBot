#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stock Price Data Retrieval Script
獲取股價歷史數據的Python腳本
"""

import sys
import json
import yfinance as yf
from datetime import datetime, timedelta
import warnings

# 抑制警告信息
warnings.filterwarnings('ignore')

def get_stock_price_data(ticker, period="6mo"):
    """
    獲取股價歷史數據
    
    Args:
        ticker (str): 股票代號
        period (str): 時間範圍 (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        
    Returns:
        dict: 包含股價數據的字典
    """
    try:
        # 創建股票對象
        stock = yf.Ticker(ticker)
        
        # 獲取歷史價格數據
        hist = stock.history(period=period)
        
        if hist.empty:
            return {
                'success': False,
                'error': f'無法獲取股票 {ticker} 的歷史數據'
            }
        
        # 準備數據
        price_data = []
        for date, row in hist.iterrows():
            price_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'open': round(float(row['Open']), 2),
                'high': round(float(row['High']), 2),
                'low': round(float(row['Low']), 2),
                'close': round(float(row['Close']), 2),
                'volume': int(row['Volume'])
            })
        
        return {
            'success': True,
            'price_data': price_data,  # 修改為前端期望的key名稱
            'period': period,
            'total_days': len(price_data)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'獲取股價數據時發生錯誤: {str(e)}'
        }

def main():
    """主函數"""
    if len(sys.argv) != 3:
        print(json.dumps({
            'success': False,
            'error': '請提供股票代號和時間範圍作為參數'
        }, ensure_ascii=False))
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    period = sys.argv[2]
    
    # 驗證股票代號格式
    if not ticker.isalnum() or len(ticker) > 10:
        print(json.dumps({
            'success': False,
            'error': '無效的股票代號格式'
        }, ensure_ascii=False))
        sys.exit(1)
    
    # 驗證時間範圍
    valid_periods = ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max']
    if period not in valid_periods:
        print(json.dumps({
            'success': False,
            'error': f'無效的時間範圍，請使用: {", ".join(valid_periods)}'
        }, ensure_ascii=False))
        sys.exit(1)
    
    # 獲取股價數據
    result = get_stock_price_data(ticker, period)
    
    # 輸出JSON結果
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
