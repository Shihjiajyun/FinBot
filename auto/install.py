#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自動下載指定股票的近五年 10-K 財報
基於 apple.py 的邏輯，專門針對 10-K 財報下載
"""

from secedgar import filings, FilingType
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import time
import sys
import os

class TenKDownloader:
    def __init__(self):
        """初始化下載器"""
        self.USER_AGENT = "JIA-JYUN SHIH (shihjiajyun@gmail.com)"
        
        # 計算近五年的日期範圍
        current_year = datetime.now().year
        self.START_DATE = datetime(current_year - 5, 1, 1)  # 5年前的1月1日
        self.END_DATE = datetime(current_year, 12, 31)     # 今年的12月31日
        
        # 設置下載目錄
        self.base_dir = Path("./downloads")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"📅 下載時間範圍: {self.START_DATE.strftime('%Y-%m-%d')} 到 {self.END_DATE.strftime('%Y-%m-%d')}")
        print(f"📁 下載目錄: {self.base_dir.absolute()}")
        
        # 與 data.py 相同的200家知名股票清單
        self.default_companies = [
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
        
        # 移除重複項目並排序，確保與 data.py 一致
        self.default_companies = sorted(list(set(self.default_companies)))
    
    def check_existing_files(self, ticker):
        """檢查是否已經下載過該股票的10-K文件"""
        stock_10k_dir = self.base_dir / ticker / "10-K"
        
        if not stock_10k_dir.exists():
            return False, 0
        
        # 計算已存在的文件數量
        txt_files = list(stock_10k_dir.glob("*.txt"))
        return len(txt_files) > 0, len(txt_files)
    
    def download_10k_for_stock(self, ticker):
        """為單一股票下載10-K財報"""
        print(f"\n🏢 開始處理股票: {ticker}")
        
        # 檢查是否已下載
        has_files, file_count = self.check_existing_files(ticker)
        if has_files:
            print(f"   📋 {ticker} 已有 {file_count} 個10-K文件，跳過下載")
            return True, f"已存在 {file_count} 個文件"
        
        try:
            print(f"   📥 正在下載 {ticker} 的10-K財報 ({self.START_DATE.year}-{self.END_DATE.year})...")
            
            # 創建10-K財報下載請求
            filing = filings(
                cik_lookup=ticker,
                filing_type=FilingType.FILING_10K,
                start_date=self.START_DATE,
                end_date=self.END_DATE,
                user_agent=self.USER_AGENT
            )
            
            # 下載到指定目錄
            filing.save(self.base_dir)
            
            # 下載後檢查文件
            time.sleep(2)  # 等待文件系統同步
            has_files_after, file_count_after = self.check_existing_files(ticker)
            
            if has_files_after:
                print(f"   ✅ {ticker} 10-K下載成功，共 {file_count_after} 個文件")
                return True, f"成功下載 {file_count_after} 個文件"
            else:
                print(f"   ⚠️  {ticker} 下載完成但未找到文件（可能該期間無10-K報告）")
                return True, "下載完成但無文件"
                
        except Exception as e:
            print(f"   ❌ {ticker} 下載失敗: {e}")
            return False, f"下載失敗: {str(e)}"
    
    def download_batch(self, stock_list=None, max_stocks=None):
        """批量下載10-K財報"""
        if stock_list is None:
            stock_list = self.default_companies
        
        # 如果指定了最大數量，則限制清單
        if max_stocks:
            stock_list = stock_list[:max_stocks]
        
        print(f"\n{'='*80}")
        print(f"🚀 批量下載10-K財報")
        print(f"📊 目標股票數量: {len(stock_list)}")
        print(f"📅 時間範圍: 近5年 ({self.START_DATE.year}-{self.END_DATE.year})")
        print(f"{'='*80}")
        
        # 統計變數
        total_stocks = len(stock_list)
        success_count = 0
        skip_count = 0
        error_count = 0
        
        results = {
            'success': [],
            'skipped': [],
            'failed': []
        }
        
        start_time = time.time()
        
        for index, ticker in enumerate(stock_list, 1):
            try:
                # 顯示進度
                print(f"\n[{index}/{total_stocks}] 處理進度: {(index/total_stocks)*100:.1f}%")
                
                # 下載股票
                success, message = self.download_10k_for_stock(ticker)
                
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
                
                # 每5隻股票休息一下，避免對SEC伺服器造成過大負擔
                if index % 5 == 0 and index < total_stocks:
                    print(f"   💤 處理5隻股票後休息10秒...")
                    time.sleep(10)
                else:
                    # 每隻股票間休息2秒
                    time.sleep(2)
                
            except KeyboardInterrupt:
                print(f"\n⏹️  用戶中斷下載，已處理 {index-1} 隻股票")
                break
            except Exception as e:
                print(f"   ❌ 處理 {ticker} 時發生未預期錯誤: {e}")
                error_count += 1
                results['failed'].append((ticker, f"未預期錯誤: {str(e)}"))
        
        # 最終統計報告
        total_time = time.time() - start_time
        processed_count = success_count + skip_count + error_count
        
        print(f"\n{'='*80}")
        print(f"📈 批量下載完成統計報告")
        print(f"{'='*80}")
        print(f"⏱️  總處理時間: {total_time/60:.1f}分鐘")
        print(f"📊 總股票數量: {total_stocks}")
        print(f"✅ 成功下載: {success_count} 隻")
        print(f"⏭️  已存在跳過: {skip_count} 隻")
        print(f"❌ 下載失敗: {error_count} 隻")
        print(f"📈 成功率: {(success_count/(processed_count-skip_count)*100) if (processed_count-skip_count) > 0 else 0:.1f}%")
        
        # 詳細結果
        if results['success']:
            print(f"\n✅ 成功下載的股票 ({len(results['success'])}隻):")
            for ticker, message in results['success']:
                print(f"   • {ticker}: {message}")
        
        if results['skipped']:
            print(f"\n⏭️  已存在跳過的股票 ({len(results['skipped'])}隻):")
            for ticker, message in results['skipped']:
                print(f"   • {ticker}: {message}")
        
        if results['failed']:
            print(f"\n❌ 下載失敗的股票 ({len(results['failed'])}隻):")
            for ticker, message in results['failed']:
                print(f"   • {ticker}: {message}")
        
        return results
    
    def download_single_stock(self, ticker):
        """下載單一股票的10-K財報"""
        print(f"\n{'='*60}")
        print(f"🎯 單一股票10-K下載: {ticker.upper()}")
        print(f"{'='*60}")
        
        success, message = self.download_10k_for_stock(ticker.upper())
        
        if success:
            print(f"\n✅ {ticker.upper()} 處理完成: {message}")
        else:
            print(f"\n❌ {ticker.upper()} 處理失敗: {message}")
        
        return success
    
    def list_downloaded_files(self):
        """列出已下載的文件"""
        print(f"\n📋 已下載的10-K文件統計:")
        print(f"{'='*60}")
        
        total_files = 0
        stock_dirs = [d for d in self.base_dir.iterdir() if d.is_dir()]
        
        for stock_dir in sorted(stock_dirs):
            tenk_dir = stock_dir / "10-K"
            if tenk_dir.exists():
                txt_files = list(tenk_dir.glob("*.txt"))
                if txt_files:
                    print(f"📁 {stock_dir.name}: {len(txt_files)} 個10-K文件")
                    total_files += len(txt_files)
        
        print(f"\n📊 總計: {total_files} 個10-K文件，{len(stock_dirs)} 家公司")

def main():
    """主程式"""
    print("📥 SEC 10-K 財報自動下載器")
    print("基於 apple.py 的下載邏輯，專門下載近5年10-K財報")
    print("="*60)
    
    downloader = TenKDownloader()
    
    if len(sys.argv) > 1:
        # 命令列模式：python install.py AAPL MSFT GOOGL
        stock_list = [ticker.upper() for ticker in sys.argv[1:]]
        print(f"🎯 命令列模式，將下載: {', '.join(stock_list)}")
        
        if len(stock_list) == 1:
            downloader.download_single_stock(stock_list[0])
        else:
            downloader.download_batch(stock_list)
    else:
        # 互動模式
        print("\n選擇下載模式:")
        print("1. 批量下載預設股票清單")
        print("2. 下載指定股票")
        print("3. 查看已下載文件")
        print("4. 測試下載（僅前5隻股票）")
        print("5. 退出")
        
        while True:
            try:
                choice = input("\n請選擇 (1-5): ").strip()
                
                if choice == "1":
                    print(f"\n📊 將下載 {len(downloader.default_companies)} 隻股票的10-K財報")
                    print("這些股票與 data.py 中的清單完全相同")
                    confirm = input(f"確定要開始下載嗎？(y/N): ").strip().lower()
                    if confirm in ['y', 'yes']:
                        downloader.download_batch()
                    break
                    
                elif choice == "2":
                    tickers_input = input("\n請輸入股票代號（用空格分隔，例如: AAPL MSFT GOOGL）: ").strip().upper()
                    if tickers_input:
                        stock_list = tickers_input.split()
                        print(f"將下載: {', '.join(stock_list)}")
                        if len(stock_list) == 1:
                            downloader.download_single_stock(stock_list[0])
                        else:
                            downloader.download_batch(stock_list)
                    break
                    
                elif choice == "3":
                    downloader.list_downloaded_files()
                    break
                    
                elif choice == "4":
                    print("🧪 測試模式：下載前5隻股票")
                    downloader.download_batch(max_stocks=5)
                    break
                    
                elif choice == "5":
                    print("👋 再見！")
                    break
                    
                else:
                    print("❌ 無效選擇，請輸入 1-5")
                    
            except KeyboardInterrupt:
                print("\n👋 程式已取消")
                break
            except Exception as e:
                print(f"\n❌ 發生錯誤: {e}")
                break

if __name__ == "__main__":
    main()
