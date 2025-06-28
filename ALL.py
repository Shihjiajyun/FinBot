#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALL.py - 批量下載股票的近五年10-K財報
==========================================
自動執行以下步驟（排除AAPL和已下載的股票）：
1. 檢查downloads資料夾中已下載的股票
2. 下載尚未下載的股票近五年10-K財報 (download_single_stock.py) 
"""

import sys
import os
import time
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# 設定 stdout 編碼，避免 Windows 下的 Unicode 錯誤
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class BatchStockProcessor:
    def __init__(self):
        """初始化批量處理器"""
        self.start_time = time.time()
        self.setup_logging()
        
        # 大幅擴展的股票列表 - 包含 S&P 500 + Russell 1000 + 其他重要股票
        self.stock_list = [
            # Technology Giants & Software
            'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'META', 'TSLA', 'NFLX', 'ADBE', 'CRM', 'ORCL',
            'IBM', 'INTC', 'AMD', 'PYPL', 'CSCO', 'TXN', 'QCOM', 'AVGO', 'NOW', 'INTU', 'AMAT', 'LRCX',
            'KLAC', 'MRVL', 'MU', 'SNPS', 'CDNS', 'FTNT', 'PANW', 'CRWD', 'ZS', 'OKTA', 'TEAM', 'WDAY',
            'VEEV', 'DOCU', 'ZM', 'SPLK', 'SNOW', 'CZI', 'DDOG', 'NET', 'CFLT', 'MDB', 'PLTR', 'COIN',
            
            # Healthcare & Pharmaceuticals
            'JNJ', 'PFE', 'UNH', 'MRK', 'TMO', 'ABT', 'DHR', 'BMY', 'LLY', 'ABBV', 'AMGN', 'GILD', 
            'CVS', 'CI', 'HUM', 'ANTM', 'SYK', 'BDX', 'ISRG', 'REGN', 'VRTX', 'BIIB', 'ILMN', 'MRNA',
            'IQV', 'CAH', 'MCK', 'COR', 'ZBH', 'EW', 'HOLX', 'A', 'DGX', 'LH', 'PKI', 'WAT', 'MTD',
            'TECH', 'CRL', 'CTLT', 'DXCM', 'ALGN', 'PEN', 'GEHC', 'SOLV', 'VTRS', 'TMDX', 'PODD',
            
            # Financial Services & Banks
            'BRK.B', 'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'USB', 'TFC', 'PNC', 'COF', 'AXP', 'BLK', 
            'SCHW', 'CME', 'ICE', 'SPGI', 'MCO', 'MMC', 'AON', 'AJG', 'BRO', 'CB', 'TRV', 'ALL',
            'PGR', 'AFL', 'MET', 'PRU', 'AIG', 'HIG', 'CNA', 'RLI', 'FNF', 'FAF', 'L', 'GL', 'RGA',
            'BX', 'KKR', 'APO', 'CG', 'TPG', 'ARES', 'OWL', 'AMG', 'TROW', 'BEN', 'IVZ', 'LUV',
            
            # Consumer & Retail
            'WMT', 'HD', 'PG', 'KO', 'PEP', 'COST', 'MCD', 'NKE', 'SBUX', 'TGT', 'LOW', 'TJX', 'DIS', 
            'CMCSA', 'VZ', 'T', 'CHTR', 'EA', 'ATVI', 'TTWO', 'EBAY', 'ETSY', 'W', 'WAYFAIR', 'SHOP',
            'SQ', 'PYPL', 'V', 'MA', 'FISV', 'FIS', 'ADP', 'PAYX', 'INTU', 'CRM', 'ADSK', 'ANSS',
            'YUM', 'QSR', 'CMG', 'DPZ', 'DNKN', 'PNRA', 'WEN', 'JACK', 'TXRH', 'EAT', 'DRI', 'CBRL',
            
            # Industrial & Manufacturing
            'CAT', 'DE', 'MMM', 'HON', 'LMT', 'RTX', 'BA', 'GE', 'EMR', 'ITW', 'ETN', 'PH', 'ROK',
            'DOV', 'FTV', 'XYL', 'IEX', 'FAST', 'WM', 'RSG', 'VRSK', 'INFO', 'BR', 'PAYX', 'CTSH',
            'ACN', 'IBM', 'TYL', 'CTXS', 'ROP', 'KEYS', 'ANSS', 'CDNS', 'SNPS', 'PTC', 'ADSK', 'CRM',
            'NOC', 'LHX', 'GD', 'LDOS', 'CACI', 'SAIC', 'BAH', 'KBR', 'AMEN', 'VST', 'TDG', 'AXON',
            
            # Energy & Oil
            'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'OXY', 'PSX', 'VLO', 'MPC', 'KMI', 'WMB', 'OKE', 
            'EPD', 'ET', 'TRGP', 'ENB', 'TRP', 'TC', 'PPL', 'SO', 'NEE', 'DUK', 'AEP', 'SRE',
            'EXC', 'XEL', 'ED', 'FE', 'ES', 'CMS', 'LNT', 'NI', 'AEE', 'CNP', 'VST', 'ATO', 'NJR',
            'BKR', 'HAL', 'FTI', 'NOV', 'HP', 'WHD', 'RIG', 'VAL', 'LBRT', 'PUMP', 'CLB', 'NINE',
            
            # Transportation & Logistics
            'UPS', 'FDX', 'DAL', 'UAL', 'AAL', 'LUV', 'ALK', 'JBLU', 'SAVE', 'HA', 'MESA', 'SKYW',
            'UNP', 'CSX', 'NSC', 'CP', 'CNI', 'KSU', 'WAB', 'TRN', 'GBX', 'RAIL', 'GATX', 'FWRD',
            'CHRW', 'EXPD', 'XPO', 'JBHT', 'KNX', 'LSTR', 'ODFL', 'SAIA', 'ARCB', 'WERN', 'MATX',
            
            # Real Estate & REITs
            'AMT', 'PLD', 'CCI', 'EQIX', 'DLR', 'SBAC', 'SPG', 'O', 'WELL', 'AVB', 'EQR', 'MAA',
            'UDR', 'ESS', 'CPT', 'BXP', 'VTR', 'PEAK', 'HST', 'RHP', 'BRX', 'REG', 'FRT', 'KIM',
            'ARE', 'AMH', 'ACC', 'EXR', 'PSA', 'CUBE', 'LSI', 'REXR', 'ELS', 'SUI', 'UMH', 'SAFE',
            
            # Materials & Chemicals
            'LIN', 'APD', 'ECL', 'SHW', 'FCX', 'NEM', 'GOLD', 'AEM', 'KGC', 'AU', 'FNV', 'WPM',
            'DD', 'LYB', 'DOW', 'CE', 'EMN', 'FMC', 'ALB', 'CF', 'MOS', 'NTR', 'IFF', 'RPM',
            'AA', 'CENX', 'CLF', 'NUE', 'STLD', 'RS', 'CMC', 'SID', 'TX', 'MT', 'PKX', 'SCCO',
            
            # Utilities
            'NEE', 'SO', 'DUK', 'AEP', 'EXC', 'XEL', 'SRE', 'D', 'PCG', 'EIX', 'FE', 'ED', 'ES',
            'AWK', 'WEC', 'DTE', 'PPL', 'CMS', 'AEE', 'LNT', 'EVRG', 'NI', 'ATO', 'CNP', 'ETR',
            'PNW', 'IDA', 'POR', 'AGR', 'AVA', 'BKH', 'SR', 'MGEE', 'MDU', 'NWE', 'OGS', 'UTL',
            
            # Communication Services
            'META', 'GOOGL', 'GOOG', 'NFLX', 'DIS', 'CMCSA', 'VZ', 'T', 'CHTR', 'TMUS', 'DISH',
            'SIRI', 'NYT', 'NWSA', 'NWS', 'FOXA', 'FOX', 'WBD', 'PARA', 'OMC', 'IPG', 'TTGT',
            
            # Consumer Staples
            'PG', 'KO', 'PEP', 'WMT', 'COST', 'WBA', 'CVS', 'KR', 'SYY', 'ADM', 'TSN', 'CAG',
            'GIS', 'K', 'CPB', 'SJM', 'HRL', 'HSY', 'MDLZ', 'MNST', 'KDP', 'STZ', 'BF.B', 'BF.A',
            'TAP', 'SAM', 'BEER', 'WEST', 'COKE', 'KOF', 'FIZZ', 'CELH', 'PMCR', 'EL', 'CL', 'CHD',
            
            # Electric Vehicles & Green Energy
            'TSLA', 'NIO', 'RIVN', 'LCID', 'XPEV', 'LI', 'FSR', 'GOEV', 'NKLA', 'RIDE', 'SOLO',
            'ENPH', 'SEDG', 'FSLR', 'SPWR', 'NOVA', 'RUN', 'CSIQ', 'JKS', 'DQ', 'SOL', 'MAXN',
            
            # Biotechnology & Life Sciences  
            'AMGN', 'GILD', 'REGN', 'VRTX', 'BIIB', 'MRNA', 'BNTX', 'SRPT', 'ALNY', 'BMRN', 'RARE',
            'BLUE', 'FOLD', 'EDIT', 'CRSP', 'NTLA', 'BEAM', 'VERV', 'SGMO', 'FATE', 'RPTX', 'SAREQ',
            
            # Semiconductors
            'NVDA', 'AMD', 'INTC', 'QCOM', 'AVGO', 'TXN', 'AMAT', 'LRCX', 'KLAC', 'MU', 'MRVL',
            'ADI', 'XLNX', 'SWKS', 'MPWR', 'MCHP', 'RMBS', 'SLAB', 'SIMO', 'MTSI', 'CRUS', 'ALGM',
            
            # E-commerce & Digital
            'AMZN', 'SHOP', 'EBAY', 'ETSY', 'W', 'OSTK', 'PRTS', 'FLWS', 'GRUB', 'DASH', 'UBER',
            'LYFT', 'ABNB', 'BKNG', 'EXPE', 'TRIP', 'PCLN', 'TZOO', 'MMYT', 'DESP', 'WBAI', 'TUYA',
            
            # Gaming & Entertainment
            'ATVI', 'EA', 'TTWO', 'ZNGA', 'RBLX', 'U', 'GMBL', 'SKLZ', 'SLGG', 'FUBO', 'NERD',
            'ESPO', 'HERO', 'BJK', 'VanEck', 'ICLN', 'ARKK', 'ARKQ', 'ARKG', 'ARKF', 'ARKW',
            
            # Additional Large Caps & Growth Stocks
            'F', 'GM', 'FORD', 'HMC', 'TM', 'RACE', 'VLKAF', 'BMWYY', 'MBGYY', 'NSANY', 'HYMTF',
            'BABA', 'JD', 'PDD', 'BIDU', 'NTES', 'TME', 'BILI', 'IQ', 'VIPS', 'YMM', 'DOYU', 'HUYA',
            'WIT', 'DIDI', 'GRAB', 'SE', 'MELI', 'GLBE', 'STNE', 'NU', 'PAGS', 'STONE', 'QFIN',
            
            # SPACs and New Listings (Recent IPOs)
            'HOOD', 'UPST', 'AFRM', 'SQ', 'Z', 'ZG', 'OPEN', 'COMP', 'RDFN', 'ZILLOW', 'REMAX',
            'EXPI', 'RLGY', 'ANYWHERE', 'OPAD', 'TURN', 'OFFERPAD', 'IBUY', 'REZI', 'REX', 'HOUS',
            
            # International ADRs
            'TSM', 'ASML', 'SAP', 'TTE', 'SHEL', 'UL', 'NVS', 'ROCHE', 'NESN', 'MC', 'LVMH',
            'OR', 'L', 'RIO', 'BHP', 'VALE', 'ITUB', 'BBD', 'ABEV', 'SBS', 'CX', 'KB', 'WF',
            
            # Additional Tech & Growth
            'ROKU', 'PINS', 'SNAP', 'TWTR', 'FB', 'SPOT', 'WORK', 'ZI', 'AI', 'PATH', 'FROG',
            'BIGC', 'VTEX', 'SPRT', 'GREE', 'IRNT', 'OPAD', 'TMC', 'GGPI', 'LCID', 'CCIV', 'PIPE'
        ]
        
        # 移除重複項目並排除AAPL
        self.stock_list = list(set(self.stock_list))
        if 'AAPL' in self.stock_list:
            self.stock_list.remove('AAPL')
        
        self.stock_list.sort()  # 按字母順序排序
        
        # 檢查已下載的股票
        self.already_downloaded = self.get_already_downloaded_stocks()
        
        # 過濾出尚未下載的股票
        self.stocks_to_download = [stock for stock in self.stock_list if stock not in self.already_downloaded]
        
        print(f"🚀 批量10-K下載器初始化完成")
        print(f"📊 股票清單總數: {len(self.stock_list)} 家公司")
        print(f"✅ 已下載股票: {len(self.already_downloaded)} 家公司")
        print(f"⬇️ 需要下載: {len(self.stocks_to_download)} 家公司")
        print(f"📝 日誌文件: batch_processor.log")
        
    def get_already_downloaded_stocks(self):
        """檢查downloads資料夾中已經下載的股票代號"""
        downloads_path = Path(__file__).parent / "downloads"
        already_downloaded = []
        
        if downloads_path.exists():
            for item in downloads_path.iterdir():
                if item.is_dir():
                    # 檢查該股票目錄下是否有10-K資料夾和檔案
                    ten_k_path = item / "10-K"
                    if ten_k_path.exists():
                        txt_files = list(ten_k_path.glob("*.txt"))
                        if txt_files:  # 如果有txt檔案，認為已下載
                            already_downloaded.append(item.name.upper())
        
        already_downloaded.sort()
        print(f"🗂️ 已下載的股票: {', '.join(already_downloaded[:10])}{'...' if len(already_downloaded) > 10 else ''}")
        return already_downloaded

    def setup_logging(self):
        """設置日誌記錄"""
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler('batch_processor.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def log_progress(self, current, total, ticker, status):
        """記錄進度資訊"""
        elapsed = time.time() - self.start_time
        progress = (current / total) * 100
        remaining = (elapsed / current) * (total - current) if current > 0 else 0
        
        self.logger.info(f"📈 進度: {current}/{total} ({progress:.1f}%) | "
                        f"當前: {ticker} | 狀態: {status} | "
                        f"已耗時: {elapsed/60:.1f}分 | "
                        f"預估剩餘: {remaining/60:.1f}分")
    
    def run_python_script(self, script_name, args, timeout=300):
        """執行Python腳本"""
        try:
            python_path = sys.executable  # 使用當前Python解釋器路徑
            command = f"{python_path} {script_name} {args}"
            self.logger.info(f"🔧 執行: {command}")
            
            # 設置環境變量
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            # 執行命令並捕獲輸出
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                env=env,
                encoding='utf-8',
                errors='ignore'
            )
            
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                if process.returncode == 0:
                    self.logger.info(f"✅ {script_name} 成功 ({args}) [編碼: utf-8]")
                    return True, stdout
                else:
                    error_msg = stderr.strip() if stderr else stdout.strip()
                    self.logger.error(f"❌ {script_name} 失敗 ({args}) [編碼: utf-8]: {error_msg}")
                    return False, error_msg
            except subprocess.TimeoutExpired:
                process.kill()
                self.logger.error(f"⏰ {script_name} 超時 ({args})")
                return False, "執行超時"
                
        except Exception as e:
            self.logger.error(f"💥 {script_name} 異常 ({args}): {e}")
            return False, str(e)

    def process_single_stock(self, ticker, step_number, total_stocks):
        """處理單一股票的10-K財報下載"""
        self.log_progress(step_number, total_stocks, ticker, "開始下載10-K財報")
        
        # 只執行步驟：下載近五年10-K財報
        self.log_progress(step_number, total_stocks, ticker, "下載近五年10-K財報")
        success, output = self.run_python_script('download_single_stock.py', ticker, timeout=600)
        
        if success:
            self.logger.info(f"✅ {ticker} - 近五年10-K財報下載完成")
            return True
        else:
            self.logger.error(f"❌ {ticker} - 10-K財報下載失敗: {output}")
            return False
    
    def run_batch_processing(self, start_index=0, end_index=None):
        """執行批量處理"""
        if end_index is None:
            end_index = len(self.stocks_to_download)
        
        processing_list = self.stocks_to_download[start_index:end_index]
        total_stocks = len(processing_list)
        
        if total_stocks == 0:
            self.logger.info("🎉 所有股票都已下載完成，無需重複下載!")
            return
        
        self.logger.info(f"🚀 開始批量下載10-K財報")
        self.logger.info(f"📊 處理範圍: {start_index+1} 到 {end_index} (共 {total_stocks} 家公司)")
        self.logger.info(f"📝 股票列表: {', '.join(processing_list[:10])}{'...' if len(processing_list) > 10 else ''}")
        
        successful_stocks = []
        failed_stocks = []
        
        for i, ticker in enumerate(processing_list, 1):
            try:
                self.logger.info(f"\n{'='*60}")
                self.logger.info(f"🎯 開始下載: {ticker} ({i}/{total_stocks})")
                self.logger.info(f"{'='*60}")
                
                is_success = self.process_single_stock(ticker, i, total_stocks)
                
                if is_success:
                    successful_stocks.append(ticker)
                    self.logger.info(f"🎉 {ticker} 下載成功!")
                else:
                    failed_stocks.append(ticker)
                    self.logger.error(f"💥 {ticker} 下載失敗!")
                
                # 每10家公司輸出一次統計
                if i % 10 == 0 or i == total_stocks:
                    self.print_interim_stats(i, total_stocks, successful_stocks, failed_stocks)
                
                # 每家公司之間休息3秒，避免API限制
                if i < total_stocks:
                    time.sleep(3)
                    
            except KeyboardInterrupt:
                self.logger.info(f"\n⏹️ 用戶中斷處理，已處理 {i-1}/{total_stocks} 家公司")
                break
            except Exception as e:
                self.logger.error(f"💥 處理 {ticker} 時發生未預期錯誤: {e}")
                failed_stocks.append(ticker)
        
        # 輸出最終統計
        self.print_final_stats(processing_list, successful_stocks, failed_stocks)
    
    def print_interim_stats(self, current, total, successful, failed):
        """輸出中期統計資訊"""
        elapsed = time.time() - self.start_time
        self.logger.info(f"\n📊 中期統計 ({current}/{total}):")
        self.logger.info(f"   ✅ 下載成功: {len(successful)} 家")
        self.logger.info(f"   ❌ 下載失敗: {len(failed)} 家")
        self.logger.info(f"   ⏱️ 已耗時: {elapsed/60:.1f} 分鐘")
        
    def print_final_stats(self, processing_list, successful, failed):
        """輸出最終統計資訊"""
        total_time = time.time() - self.start_time
        total_stocks = len(processing_list)
        
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"🏁 批量10-K下載完成報告")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"📊 總計處理: {total_stocks} 家公司")
        self.logger.info(f"✅ 下載成功: {len(successful)} 家 ({len(successful)/total_stocks*100:.1f}%)")
        self.logger.info(f"❌ 下載失敗: {len(failed)} 家 ({len(failed)/total_stocks*100:.1f}%)")
        self.logger.info(f"⏱️ 總耗時: {total_time/60:.1f} 分鐘")
        self.logger.info(f"⚡ 平均每家: {total_time/total_stocks:.1f} 秒")
        
        if successful:
            self.logger.info(f"\n✅ 下載成功的公司:")
            for ticker in successful:
                self.logger.info(f"   - {ticker}")
        
        if failed:
            self.logger.info(f"\n❌ 下載失敗的公司:")
            for ticker in failed:
                self.logger.info(f"   - {ticker}")
    
    def show_stock_lists(self):
        """顯示股票列表狀態"""
        print(f"\n📋 股票下載狀態總覽:")
        print("=" * 80)
        
        print(f"\n✅ 已下載的股票 (共 {len(self.already_downloaded)} 家公司):")
        if self.already_downloaded:
            for i in range(0, len(self.already_downloaded), 10):
                group = self.already_downloaded[i:i+10]
                print(f"      {' '.join(f'{ticker:>6}' for ticker in group)}")
        else:
            print("      (無)")
        
        print(f"\n⬇️ 需要下載的股票 (共 {len(self.stocks_to_download)} 家公司):")
        if self.stocks_to_download:
            for i in range(0, len(self.stocks_to_download), 10):
                group = self.stocks_to_download[i:i+10]
                print(f"      {' '.join(f'{ticker:>6}' for ticker in group)}")
        else:
            print("      (無 - 所有股票都已下載)")
        
        print("=" * 80)
        print(f"注意: 已排除 AAPL，將下載近五年10-K財報")

def main():
    """主函數"""
    processor = BatchStockProcessor()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--list':
            processor.show_stock_lists()
            return
        elif sys.argv[1] == '--help':
            print("""
ALL.py - 批量10-K財報下載器使用說明
===================================

用法:
  python ALL.py                    # 下載所有尚未下載的股票10-K財報
  python ALL.py --list             # 顯示已下載和需下載的股票列表  
  python ALL.py --range 0 20       # 下載前20家需下載公司的10-K財報
  python ALL.py --range 20 40      # 下載第21-40家需下載公司的10-K財報
  python ALL.py --help             # 顯示此說明

功能特色:
  - 自動檢查downloads資料夾，避免重複下載
  - 已自動排除 AAPL
  - 大幅擴展股票清單 (S&P 500 + Russell 1000 + 成長股等)
  - 每家公司間隔3秒，避免API限制
  - 日誌保存在 batch_processor.log
  - 可隨時按 Ctrl+C 中斷處理
  - 只下載近五年的10-K財報

處理步驟:
  1. 掃描downloads資料夾檢查已下載股票
  2. 過濾出需要下載的股票列表
  3. 下載近五年10-K財報 (download_single_stock.py)
            """)
            return
        elif sys.argv[1] == '--range' and len(sys.argv) >= 4:
            start_idx = int(sys.argv[2])
            end_idx = int(sys.argv[3])
            processor.run_batch_processing(start_idx, end_idx)
            return
    
    # 預設處理所有需要下載的股票
    processor.show_stock_lists()
    
    if len(processor.stocks_to_download) == 0:
        print("\n🎉 所有股票都已下載完成!")
        return
    
    # 確認是否繼續
    try:
        response = input(f"\n❓ 確認要下載這 {len(processor.stocks_to_download)} 家公司的近五年10-K財報嗎? (y/N): ")
        if response.lower() != 'y':
            print("❌ 已取消下載")
            return
    except KeyboardInterrupt:
        print(f"\n❌ 已取消下載")
        return
    
    # 開始批量處理
    processor.run_batch_processing()

if __name__ == "__main__":
    main() 