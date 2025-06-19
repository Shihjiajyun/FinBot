#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stock Information Retrieval Script
獲取股票資訊的Python腳本
"""

import sys
import json
import yfinance as yf
from datetime import datetime, timedelta
import warnings

# 抑制警告信息
warnings.filterwarnings('ignore')

def get_stock_info(ticker):
    """
    獲取股票資訊
    
    Args:
        ticker (str): 股票代號
        
    Returns:
        dict: 包含股票資訊的字典
    """
    try:
        # 創建股票對象
        stock = yf.Ticker(ticker)
        
        # 獲取股票資訊
        info = stock.info
        
        # 獲取歷史價格數據（最近5天）
        hist = stock.history(period="5d")
        
        if hist.empty:
            return {
                'success': False,
                'error': f'無法獲取股票 {ticker} 的歷史數據'
            }
        
        # 獲取最新價格
        latest_price = hist['Close'].iloc[-1] if not hist.empty else None
        
        # 計算價格變化
        if len(hist) >= 2:
            prev_price = hist['Close'].iloc[-2]
            price_change = latest_price - prev_price
            price_change_percent = (price_change / prev_price) * 100
        else:
            price_change = 0
            price_change_percent = 0
        
        # 提取關鍵資訊
        stock_data = {
            'symbol': ticker,
            'company_name': info.get('longName', info.get('shortName', ticker)),
            'current_price': round(latest_price, 2) if latest_price else None,
            'price_change': round(price_change, 2) if price_change else 0,
            'price_change_percent': round(price_change_percent, 2) if price_change_percent else 0,
            'market_cap': info.get('marketCap'),
            'pe_ratio': info.get('trailingPE'),
            'eps': info.get('trailingEps'),
            'dividend_yield': info.get('dividendYield'),
            'week_52_high': info.get('fiftyTwoWeekHigh'),
            'week_52_low': info.get('fiftyTwoWeekLow'),
            'avg_volume': info.get('averageVolume'),
            'profit_margin': info.get('profitMargins'),
            'return_on_assets': info.get('returnOnAssets'),
            'exchange': info.get('exchange'),
            'sector': info.get('sector'),
            'industry': info.get('industry'),
            'beta': info.get('beta'),
            'book_value': info.get('bookValue'),
            'debt_to_equity': info.get('debtToEquity'),
            'revenue_growth': info.get('revenueGrowth'),
            'earnings_growth': info.get('earningsGrowth')
        }
        
        # 格式化數值
        if stock_data['dividend_yield']:
            stock_data['dividend_yield'] = round(stock_data['dividend_yield'] * 100, 2)
        
        if stock_data['profit_margin']:
            stock_data['profit_margin'] = round(stock_data['profit_margin'] * 100, 2)
            
        if stock_data['return_on_assets']:
            stock_data['return_on_assets'] = round(stock_data['return_on_assets'] * 100, 2)
            
        if stock_data['revenue_growth']:
            stock_data['revenue_growth'] = round(stock_data['revenue_growth'] * 100, 2)
            
        if stock_data['earnings_growth']:
            stock_data['earnings_growth'] = round(stock_data['earnings_growth'] * 100, 2)
        
        return {
            'success': True,
            'data': stock_data
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'獲取股票資訊時發生錯誤: {str(e)}'
        }

def main():
    """主函數"""
    if len(sys.argv) != 2:
        print(json.dumps({
            'success': False,
            'error': '請提供股票代號作為參數'
        }, ensure_ascii=False))
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    
    # 驗證股票代號格式
    if not ticker.isalnum() or len(ticker) > 10:
        print(json.dumps({
            'success': False,
            'error': '無效的股票代號格式'
        }, ensure_ascii=False))
        sys.exit(1)
    
    # 獲取股票資訊
    result = get_stock_info(ticker)
    
    # 輸出JSON結果
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main() 