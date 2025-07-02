#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量股票財務數據抓取器
自動抓取200家知名股票的財務數據並存入資料庫
基於 dual_source_analyzer.py 的功能
"""

import sys
import os
import time
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import logging

# 添加父目錄到路徑，以便導入 dual_source_analyzer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 導入 dual_source_analyzer
try:
    from dual_source_analyzer import DualSourceAnalyzer
except ImportError as e:
    print(f"無法導入 dual_source_analyzer: {e}")
    print("請確保 dual_source_analyzer.py 在正確的位置")
    sys.exit(1)

class BatchStockDataProcessor:
    def __init__(self):
        """初始化批量處理器"""
        self.setup_logging()
        
        # 200家知名股票代號 - 涵蓋主要指數成分股
        self.stock_list = [
            # 科技巨頭 - FAANG + 微軟
            'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'META', 'NFLX', 'NVDA', 'TSLA',
            
            # 科技股 - 軟體與服務
            'CRM', 'ORCL', 'ADBE', 'NOW', 'INTU', 'IBM', 'CSCO', 'INTC', 'AMD', 'QCOM',
            'TXN', 'AVGO', 'MU', 'AMAT', 'LRCX', 'KLAC', 'MRVL', 'SNPS', 'CDNS', 'FTNT',
            'PANW', 'CRWD', 'ZS', 'OKTA', 'TEAM', 'WDAY', 'VEEV', 'DOCU', 'ZM', 'SPLK',
            'SNOW', 'DDOG', 'NET', 'MDB', 'PLTR', 'COIN', 'ROKU', 'PINS', 'SNAP', 'SPOT',
            
            # 醫療保健
            'JNJ', 'PFE', 'UNH', 'MRK', 'TMO', 'ABT', 'DHR', 'BMY', 'LLY', 'ABBV',
            'AMGN', 'GILD', 'CVS', 'CI', 'HUM', 'ANTM', 'SYK', 'BDX', 'ISRG', 'REGN',
            'VRTX', 'BIIB', 'ILMN', 'MRNA', 'IQV', 'CAH', 'MCK', 'COR', 'ZBH', 'EW',
            'HOLX', 'A', 'DGX', 'LH', 'PKI', 'WAT', 'MTD', 'DXCM', 'ALGN', 'GEHC',
            
            # 金融服務
            'BRK.B', 'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'USB', 'TFC', 'PNC',
            'COF', 'AXP', 'BLK', 'SCHW', 'CME', 'ICE', 'SPGI', 'MCO', 'MMC', 'AON',
            'AJG', 'BRO', 'CB', 'TRV', 'ALL', 'PGR', 'AFL', 'MET', 'PRU', 'AIG',
            'BX', 'KKR', 'APO', 'CG', 'TPG', 'ARES', 'AMG', 'TROW', 'BEN', 'IVZ',
            
            # 消費品與零售
            'WMT', 'HD', 'PG', 'KO', 'PEP', 'COST', 'MCD', 'NKE', 'SBUX', 'TGT',
            'LOW', 'TJX', 'DIS', 'CMCSA', 'VZ', 'T', 'CHTR', 'EA', 'TTWO', 'EBAY',
            'ETSY', 'SQ', 'V', 'MA', 'FISV', 'FIS', 'ADP', 'PAYX', 'YUM', 'QSR',
            'CMG', 'DXCM', 'ORLY', 'AZO', 'AAP', 'GM', 'F', 'RACE', 'RIVN', 'LCID',
            
            # 工業股
            'CAT', 'DE', 'BA', 'HON', 'UPS', 'FDX', 'LMT', 'RTX', 'NOC', 'GD',
            'MMM', 'GE', 'EMR', 'ETN', 'PH', 'ITW', 'CMI', 'ROK', 'DOV', 'IR',
            'XYL', 'IEX', 'FTV', 'AME', 'ROP', 'DHI', 'LEN', 'NVR', 'PHM', 'TOL',
            
            # 能源
            'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'PXD', 'FANG', 'MPC', 'VLO', 'PSX',
            'HES', 'OXY', 'DVN', 'CTRA', 'MRO', 'APA', 'EQT', 'KNTK', 'CNX', 'GPOR',
            
            # 公用事業
            'NEE', 'SO', 'DUK', 'AEP', 'SRE', 'D', 'PEG', 'EXC', 'XEL', 'WEC',
            'ES', 'AWK', 'PPL', 'AEE', 'CMS', 'DTE', 'NI', 'LNT', 'EVRG', 'CNP',
            
            # 材料
            'LIN', 'APD', 'ECL', 'SHW', 'FCX', 'NEM', 'NUE', 'DOW', 'DD', 'PPG',
            'IFF', 'FMC', 'LYB', 'ALB', 'VMC', 'MLM', 'NUE', 'STLD', 'RS', 'RPM',
            
            # REITs
            'PLD', 'AMT', 'CCI', 'EQIX', 'PSA', 'EXR', 'AVB', 'EQR', 'WELL', 'MAA',
            'UDR', 'CPT', 'ESS', 'FRT', 'AIV', 'BXP', 'VTR', 'O', 'STOR', 'SPG',
            
            # 通訊服務
            'GOOGL', 'META', 'VZ', 'T', 'CHTR', 'TMUS', 'DIS', 'CMCSA', 'NFLX', 'DISH'
        ]
        
        # 移除重複項目並排序
        self.stock_list = sorted(list(set(self.stock_list)))
        print(f"總共需要處理 {len(self.stock_list)} 隻股票")
        
        # 資料庫配置
        self.db_config = {
            'host': '43.207.210.147',
            'database': 'finbot_db',
            'user': 'myuser',
            'password': '123456789',
            'charset': 'utf8mb4'
        }
        
        self.analyzer = DualSourceAnalyzer(self.db_config)
        self.start_time = time.time()
        
    def setup_logging(self):
        """設置日誌"""
        log_filename = f"batch_stock_processor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("批量股票數據處理器啟動")
    
    def check_stock_exists_in_db(self, ticker):
        """檢查股票是否已在資料庫中"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            # 檢查是否已有該股票的財務數據
            query = """
                SELECT COUNT(*) as count, MAX(filing_year) as latest_year 
                FROM filings 
                WHERE ticker = %s AND filing_type = 'ANNUAL_FINANCIAL'
            """
            cursor.execute(query, (ticker,))
            result = cursor.fetchone()
            
            cursor.close()
            connection.close()
            
            count = result[0] if result else 0
            latest_year = result[1] if result and result[1] else None
            
            return count > 0, latest_year
            
        except Error as e:
            self.logger.error(f"檢查資料庫時發生錯誤 {ticker}: {e}")
            return False, None
    
    def process_single_stock(self, ticker, index, total):
        """處理單一股票"""
        self.logger.info(f"[{index}/{total}] 開始處理股票: {ticker}")
        
        try:
            # 檢查是否已存在
            exists, latest_year = self.check_stock_exists_in_db(ticker)
            
            if exists:
                self.logger.info(f"[{ticker}] 已存在於資料庫中，最新年份: {latest_year}，跳過處理")
                return True, "已存在"
            
            # 獲取公司名稱
            company_name = self.analyzer.get_company_name_from_ticker(ticker)
            self.logger.info(f"[{ticker}] 公司名稱: {company_name}")
            
            # 執行完整分析
            self.logger.info(f"[{ticker}] 開始數據分析和抓取...")
            comparison_results, final_data, year_data = self.analyzer.analyze_stock_with_database(
                ticker, company_name, save_to_db=True
            )
            
            if year_data:
                # 計算成功存入的年份數量
                successful_years = 0
                for year, data in year_data.items():
                    if data['macrotrends'] or data['yahoo']:
                        successful_years += 1
                
                self.logger.info(f"[{ticker}] 處理完成，成功存入 {successful_years} 年數據")
                return True, f"成功存入 {successful_years} 年數據"
            else:
                self.logger.warning(f"[{ticker}] 無法獲取有效數據")
                return False, "無有效數據"
                
        except Exception as e:
            self.logger.error(f"[{ticker}] 處理失敗: {e}")
            return False, f"錯誤: {str(e)}"
    
    def run_batch_processing(self):
        """執行批量處理"""
        self.logger.info("="*80)
        self.logger.info("開始批量股票財務數據抓取")
        self.logger.info(f"目標股票數量: {len(self.stock_list)}")
        self.logger.info("="*80)
        
        # 統計變數
        total_stocks = len(self.stock_list)
        processed_count = 0
        success_count = 0
        skip_count = 0
        error_count = 0
        
        # 處理結果記錄
        results = {
            'success': [],
            'skipped': [],
            'failed': []
        }
        
        for index, ticker in enumerate(self.stock_list, 1):
            try:
                # 顯示進度
                elapsed_time = time.time() - self.start_time
                if processed_count > 0:
                    avg_time_per_stock = elapsed_time / processed_count
                    remaining_stocks = total_stocks - processed_count
                    estimated_remaining_time = avg_time_per_stock * remaining_stocks
                    
                    self.logger.info(f"進度: {processed_count}/{total_stocks} ({(processed_count/total_stocks)*100:.1f}%)")
                    self.logger.info(f"已耗時: {elapsed_time/60:.1f}分鐘，預估剩餘: {estimated_remaining_time/60:.1f}分鐘")
                
                # 處理股票
                success, message = self.process_single_stock(ticker, index, total_stocks)
                processed_count += 1
                
                if success:
                    if "已存在" in message:
                        skip_count += 1
                        results['skipped'].append((ticker, message))
                    else:
                        success_count += 1
                        results['success'].append((ticker, message))
                else:
                    error_count += 1
                    results['failed'].append((ticker, message))
                
                # 每處理10隻股票休息一下，避免對伺服器造成過大負擔
                if index % 10 == 0:
                    self.logger.info("處理10隻股票後休息30秒...")
                    time.sleep(30)
                else:
                    # 每隻股票間休息2秒
                    time.sleep(2)
                    
            except KeyboardInterrupt:
                self.logger.info("用戶中斷處理")
                break
            except Exception as e:
                self.logger.error(f"處理 {ticker} 時發生未預期錯誤: {e}")
                error_count += 1
                results['failed'].append((ticker, f"未預期錯誤: {str(e)}"))
                processed_count += 1
        
        # 最終統計報告
        total_time = time.time() - self.start_time
        self.logger.info("="*80)
        self.logger.info("批量處理完成統計報告")
        self.logger.info("="*80)
        self.logger.info(f"總處理時間: {total_time/60:.1f}分鐘")
        self.logger.info(f"總股票數量: {total_stocks}")
        self.logger.info(f"已處理數量: {processed_count}")
        self.logger.info(f"成功新增: {success_count}")
        self.logger.info(f"已存在跳過: {skip_count}")
        self.logger.info(f"處理失敗: {error_count}")
        self.logger.info(f"成功率: {(success_count/(processed_count-skip_count)*100) if (processed_count-skip_count) > 0 else 0:.1f}%")
        
        # 詳細結果
        if results['success']:
            self.logger.info(f"\n成功新增的股票 ({len(results['success'])}隻):")
            for ticker, message in results['success'][:10]:  # 只顯示前10個
                self.logger.info(f"  ✅ {ticker}: {message}")
            if len(results['success']) > 10:
                self.logger.info(f"  ... 還有 {len(results['success'])-10} 隻")
        
        if results['skipped']:
            self.logger.info(f"\n已存在跳過的股票 ({len(results['skipped'])}隻):")
            for ticker, message in results['skipped'][:10]:  # 只顯示前10個
                self.logger.info(f"  ⏭️  {ticker}: {message}")
            if len(results['skipped']) > 10:
                self.logger.info(f"  ... 還有 {len(results['skipped'])-10} 隻")
        
        if results['failed']:
            self.logger.info(f"\n處理失敗的股票 ({len(results['failed'])}隻):")
            for ticker, message in results['failed']:
                self.logger.info(f"  ❌ {ticker}: {message}")
        
        return {
            'total': total_stocks,
            'processed': processed_count,
            'success': success_count,
            'skipped': skip_count,
            'failed': error_count,
            'results': results
        }

def main():
    """主程式"""
    print("🚀 FinBot 批量股票財務數據抓取器")
    print("="*60)
    print("功能: 自動抓取200家知名股票的財務數據")
    print("數據源: Macrotrends + Yahoo Finance")
    print("目標: filings 資料表")
    print("="*60)
    
    # 確認執行
    confirm = input("確定要開始批量處理嗎？這可能需要數小時 (y/N): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("取消執行")
        return
    
    # 創建處理器並執行
    processor = BatchStockDataProcessor()
    
    try:
        results = processor.run_batch_processing()
        
        print("\n" + "="*60)
        print("🎉 批量處理完成！")
        print(f"總共處理: {results['processed']}/{results['total']} 隻股票")
        print(f"成功新增: {results['success']} 隻")
        print(f"已存在跳過: {results['skipped']} 隻")
        print(f"處理失敗: {results['failed']} 隻")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n用戶中斷執行")
    except Exception as e:
        print(f"\n程式執行失敗: {e}")
        logging.error(f"程式執行失敗: {e}")

if __name__ == "__main__":
    main()
