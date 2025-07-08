import sys
import json
import yfinance as yf
from time import sleep
from random import uniform

def get_current_price(ticker):
    try:
        # 添加隨機延遲以避免頻繁請求
        sleep(uniform(0.1, 0.5))
        
        # 使用yfinance獲取股票資訊
        stock = yf.Ticker(ticker)
        
        # 獲取即時報價
        info = stock.info
        
        if not info:
            return {
                'success': False,
                'error': '無法獲取股票資訊'
            }
            
        current_price = info.get('regularMarketPrice')
        previous_close = info.get('regularMarketPreviousClose')
        
        if not current_price or not previous_close:
            return {
                'success': False,
                'error': '無法獲取價格資訊'
            }
            
        price_change = current_price - previous_close
        change_percent = (price_change / previous_close) * 100
        
        return {
            'success': True,
            'price': current_price,
            'change': price_change,
            'change_percent': change_percent
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(json.dumps({
            'success': False,
            'error': '請提供股票代號'
        }))
        sys.exit(1)
        
    ticker = sys.argv[1]
    result = get_current_price(ticker)
    print(json.dumps(result)) 