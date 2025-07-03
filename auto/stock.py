#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能10-K財報拆解器
自動檢測並處理已下載但尚未拆解的股票財報
基於 parse_single_stock.py 的邏輯
"""

import os
import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
ROOT_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(str(ROOT_DIR))

import time
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import logging
from parse_single_stock import SingleStockTenKParser

class SmartTenKProcessor:
    def __init__(self):
        """初始化處理器"""
        self.setup_logging()
        
        # 資料庫配置
        self.db_config = {
            'host': '43.207.210.147',
            'database': 'finbot_db',
            'user': 'myuser',
            'password': '123456789',
            'charset': 'utf8mb4'
        }
        
        # 設置下載目錄（使用 stock.py 所在資料夾裡的 downloads）
        current_dir = Path(__file__).resolve().parent
        self.downloads_dir = current_dir / "downloads"
        self.downloads_dir.mkdir(parents=True, exist_ok=True)  # 如果不存在就建立

        print(f"✅ 使用下載目錄: {self.downloads_dir}")
        
        self.start_time = time.time()
    
    def setup_logging(self):
        """設置日誌"""
        # 在專案根目錄下創建logs目錄
        log_dir = ROOT_DIR / "logs"
        log_dir.mkdir(exist_ok=True)
        
        log_filename = log_dir / f"smart_tenk_processor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(str(log_filename), encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("智能10-K財報拆解器啟動")
    
    def connect_database(self):
        """連接資料庫"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            if connection.is_connected():
                self.logger.info("✅ 資料庫連接成功")
                return connection
        except Error as e:
            self.logger.error(f"❌ 資料庫連接失敗: {e}")
            return None
    
    def get_downloaded_stocks(self):
        """獲取已下載10-K的股票清單"""
        downloaded_stocks = []
        
        for stock_dir in self.downloads_dir.iterdir():
            if not stock_dir.is_dir():
                continue
            
            tenk_dir = stock_dir / "10-K"
            if not tenk_dir.exists():
                continue
            
            txt_files = list(tenk_dir.glob("*.txt"))
            if txt_files:  # 只有當有.txt文件時才添加
                downloaded_stocks.append(stock_dir.name)
        
        self.logger.info(f"📁 找到 {len(downloaded_stocks)} 個已下載10-K的股票")
        return downloaded_stocks
    
    def get_processed_stocks(self):
        """從資料庫獲取已處理的股票清單"""
        processed_stocks = set()
        connection = self.connect_database()
        
        if not connection:
            return processed_stocks
        
        try:
            cursor = connection.cursor()
            
            # 查詢已經在ten_k_filings表中的股票
            query = """
                SELECT DISTINCT company_name 
                FROM ten_k_filings 
                WHERE company_name IS NOT NULL
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            processed_stocks = {row[0] for row in results}
            self.logger.info(f"📊 找到 {len(processed_stocks)} 個已處理的股票")
            
        except Error as e:
            self.logger.error(f"❌ 查詢資料庫失敗: {e}")
        
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
        
        return processed_stocks
    
    def find_stocks_to_process(self):
        """找出需要處理的股票"""
        # 獲取已下載的股票
        downloaded_stocks = set(self.get_downloaded_stocks())
        
        # 獲取已處理的股票
        processed_stocks = self.get_processed_stocks()
        
        # 找出已下載但未處理的股票
        stocks_to_process = downloaded_stocks - processed_stocks
        
        self.logger.info(f"🎯 找到 {len(stocks_to_process)} 個需要處理的股票")
        return sorted(list(stocks_to_process))  # 轉換為排序後的列表
    
    def process_stocks(self, stocks_to_process, max_stocks=None):
        """批量處理股票"""
        if max_stocks:
            stocks_to_process = stocks_to_process[:max_stocks]
        
        total_stocks = len(stocks_to_process)
        if total_stocks == 0:
            self.logger.info("✨ 沒有需要處理的股票")
            return True
        
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"🚀 開始批量處理10-K財報")
        self.logger.info(f"📊 目標股票數量: {total_stocks}")
        self.logger.info(f"{'='*80}")
        
        # 統計變數
        success_count = 0
        error_count = 0
        results = {
            'success': [],
            'failed': []
        }
        
        for index, ticker in enumerate(stocks_to_process, 1):
            try:
                self.logger.info(f"\n[{index}/{total_stocks}] 處理進度: {(index/total_stocks)*100:.1f}%")
                self.logger.info(f"🎯 處理股票: {ticker}")
                
                # 使用SingleStockTenKParser處理
                parser = SingleStockTenKParser(ticker, self.db_config)
                success = parser.process_ticker_folder()
                
                if success:
                    success_count += 1
                    results['success'].append(ticker)
                    self.logger.info(f"✅ {ticker} 處理成功")
                else:
                    error_count += 1
                    results['failed'].append(ticker)
                    self.logger.info(f"❌ {ticker} 處理失敗")
                
                # 每處理5隻股票休息一下
                if index % 5 == 0 and index < total_stocks:
                    self.logger.info("💤 處理5隻股票後休息30秒...")
                    time.sleep(30)
                
            except KeyboardInterrupt:
                self.logger.info(f"\n⏹️  用戶中斷處理，已處理 {index} 隻股票")
                break
            except Exception as e:
                self.logger.error(f"❌ 處理 {ticker} 時發生錯誤: {e}")
                error_count += 1
                results['failed'].append(ticker)
        
        # 最終統計報告
        total_time = time.time() - self.start_time
        self.logger.info(f"\n{'='*80}")
        self.logger.info("📈 批量處理完成統計報告")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"⏱️  總處理時間: {total_time/60:.1f}分鐘")
        self.logger.info(f"📊 總股票數量: {total_stocks}")
        self.logger.info(f"✅ 成功處理: {success_count}")
        self.logger.info(f"❌ 處理失敗: {error_count}")
        self.logger.info(f"📈 成功率: {(success_count/total_stocks*100):.1f}%")
        
        # 詳細結果
        if results['success']:
            self.logger.info(f"\n✅ 成功處理的股票 ({len(results['success'])}隻):")
            for ticker in results['success']:
                self.logger.info(f"   • {ticker}")
        
        if results['failed']:
            self.logger.info(f"\n❌ 處理失敗的股票 ({len(results['failed'])}隻):")
            for ticker in results['failed']:
                self.logger.info(f"   • {ticker}")
        
        return success_count > 0

def main():
    """主程式"""
    print("🤖 智能10-K財報拆解器")
    print("功能: 自動檢測並處理已下載但尚未拆解的股票財報")
    print("="*60)
    
    processor = SmartTenKProcessor()
    
    # 找出需要處理的股票
    stocks_to_process = processor.find_stocks_to_process()
    
    if not stocks_to_process:
        print("✨ 所有已下載的股票都已經處理完成")
        return
    
    # 顯示選項
    print("\n選擇處理模式:")
    print("1. 處理所有未處理的股票")
    print("2. 處理指定數量的股票")
    print("3. 顯示待處理的股票清單")
    print("4. 退出")
    
    while True:
        try:
            choice = input("\n請選擇 (1-4): ").strip()
            
            if choice == "1":
                confirm = input(f"\n確定要處理所有 {len(stocks_to_process)} 隻未處理的股票嗎？(y/N): ").strip().lower()
                if confirm in ['y', 'yes']:
                    processor.process_stocks(stocks_to_process)
                break
                
            elif choice == "2":
                try:
                    num_stocks = int(input("\n請輸入要處理的股票數量: ").strip())
                    if 0 < num_stocks <= len(stocks_to_process):
                        print(f"\n將處理前 {num_stocks} 隻股票:")
                        for ticker in stocks_to_process[:num_stocks]:
                            print(f"   • {ticker}")
                        confirm = input("\n確定要開始處理嗎？(y/N): ").strip().lower()
                        if confirm in ['y', 'yes']:
                            processor.process_stocks(stocks_to_process, num_stocks)
                    else:
                        print(f"❌ 請輸入1到{len(stocks_to_process)}之間的數字")
                        continue
                except ValueError:
                    print("❌ 請輸入有效的數字")
                    continue
                break
                
            elif choice == "3":
                print(f"\n📋 待處理的股票清單 ({len(stocks_to_process)}隻):")
                for ticker in stocks_to_process:
                    print(f"   • {ticker}")
                break
                
            elif choice == "4":
                print("👋 再見！")
                break
                
            else:
                print("❌ 無效選擇，請輸入 1-4")
                
        except KeyboardInterrupt:
            print("\n👋 程式已取消")
            break
        except Exception as e:
            print(f"\n❌ 發生錯誤: {e}")
            break

if __name__ == "__main__":
    main()
