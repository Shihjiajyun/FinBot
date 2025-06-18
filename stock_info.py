#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import yfinance as yf
import json
import sys
import warnings
warnings.filterwarnings('ignore')

def format_number(number):
    """格式化數字顯示"""
    if number is None:
        return None
    
    try:
        num = float(number)
        if num >= 1e12:
            return round(num / 1e12, 2)
        elif num >= 1e9:
            return round(num / 1e9, 2)
        elif num >= 1e6:
            return round(num / 1e6, 2)
        else:
            return round(num, 2)
    except:
        return None

def format_percentage(number):
    """格式化百分比"""
    if number is None:
        return None
    try:
        return round(float(number) * 100, 2)
    except:
        return None

def get_stock_info(ticker_symbol):
    """
    獲取股票詳細資訊
    """
    try:
        # 創建股票對象
        stock = yf.Ticker(ticker_symbol)
        
        # 獲取股票資訊
        info = stock.info
        
        # 獲取歷史價格數據（最近2天，用於計算價格變化）
        hist = stock.history(period="2d")
        
        # 計算價格變化
        current_price = None
        price_change = None
        price_change_percent = None
        
        if not hist.empty and len(hist) >= 1:
            current_price = round(hist['Close'].iloc[-1], 2)
            
            if len(hist) >= 2:
                previous_price = hist['Close'].iloc[-2]
                price_change = round(current_price - previous_price, 2)
                price_change_percent = round((price_change / previous_price) * 100, 2)
        
        # 整理股票資訊
        stock_data = {
            'symbol': ticker_symbol.upper(),
            'company_name': info.get('longName', 'N/A'),
            'current_price': current_price,
            'price_change': price_change,
            'price_change_percent': price_change_percent,
            'market_cap': info.get('marketCap'),
            'pe_ratio': info.get('trailingPE'),
            'eps': info.get('trailingEps'),
            'dividend_yield': format_percentage(info.get('dividendYield')),
            'week_52_high': info.get('fiftyTwoWeekHigh'),
            'week_52_low': info.get('fiftyTwoWeekLow'),
            'avg_volume': info.get('averageVolume'),
            'profit_margin': format_percentage(info.get('profitMargins')),
            'return_on_assets': format_percentage(info.get('returnOnAssets')),
            'return_on_equity': format_percentage(info.get('returnOnEquity')),
            'debt_to_equity': info.get('debtToEquity'),
            'exchange': info.get('exchange', 'N/A'),
            'currency': info.get('currency', 'USD'),
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            'country': info.get('country', 'N/A'),
            'website': info.get('website', 'N/A'),
            'business_summary': info.get('longBusinessSummary', 'N/A')
        }
        
        return {
            'success': True,
            'data': stock_data
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f"獲取股票資訊失敗: {str(e)}"
        }

def get_company_mapping():
    """
    獲取常見股票代號與公司名稱的對照表
    """
    return {
        # 科技股
        'AAPL': 'Apple Inc.',
        'MSFT': 'Microsoft Corporation',
        'GOOGL': 'Alphabet Inc.',
        'AMZN': 'Amazon.com Inc.',
        'META': 'Meta Platforms Inc.',
        'TSLA': 'Tesla Inc.',
        'NVDA': 'NVIDIA Corporation',
        'NFLX': 'Netflix Inc.',
        'ADBE': 'Adobe Inc.',
        'CRM': 'Salesforce Inc.',
        'ORCL': 'Oracle Corporation',
        'IBM': 'International Business Machines',
        
        # 金融股
        'JPM': 'JPMorgan Chase & Co.',
        'BAC': 'Bank of America Corp.',
        'WFC': 'Wells Fargo & Company',
        'GS': 'Goldman Sachs Group Inc.',
        'MS': 'Morgan Stanley',
        'C': 'Citigroup Inc.',
        'V': 'Visa Inc.',
        'MA': 'Mastercard Inc.',
        'PYPL': 'PayPal Holdings Inc.',
        
        # 消費股
        'KO': 'Coca-Cola Company',
        'PEP': 'PepsiCo Inc.',
        'WMT': 'Walmart Inc.',
        'COST': 'Costco Wholesale Corp.',
        'HD': 'Home Depot Inc.',
        'MCD': 'McDonald\'s Corporation',
        'SBUX': 'Starbucks Corporation',
        'NKE': 'Nike Inc.',
        
        # 醫療保健
        'JNJ': 'Johnson & Johnson',
        'PFE': 'Pfizer Inc.',
        'UNH': 'UnitedHealth Group Inc.',
        'ABBV': 'AbbVie Inc.',
        'TMO': 'Thermo Fisher Scientific',
        'ABT': 'Abbott Laboratories',
        
        # 工業股
        'BA': 'Boeing Company',
        'CAT': 'Caterpillar Inc.',
        'GE': 'General Electric Company',
        'MMM': '3M Company',
        'HON': 'Honeywell International',
        
        # 能源股
        'XOM': 'Exxon Mobil Corporation',
        'CVX': 'Chevron Corporation',
        'COP': 'ConocoPhillips',
        
        # 電信股
        'VZ': 'Verizon Communications',
        'T': 'AT&T Inc.',
        'TMUS': 'T-Mobile US Inc.',
        
        # 公用事業
        'NEE': 'NextEra Energy Inc.',
        'DUK': 'Duke Energy Corporation',
        'SO': 'Southern Company'
    }

if __name__ == "__main__":
    # 如果有命令行參數，則處理股票查詢
    if len(sys.argv) > 1:
        ticker = sys.argv[1].upper()
        result = get_stock_info(ticker)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # 顯示可用的股票代號
        mapping = get_company_mapping()
        print("可用的股票代號:")
        for symbol, name in mapping.items():
            print(f"{symbol}: {name}") 