#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FinBot 財務數據抓取器 - 使用 Financial Modeling Prep (FMP) API
自動抓取美股公司 2014-2024 年度財務數據並存入資料庫
支援批量處理，涵蓋損益表、資產負債表、現金流量表數據
"""

import sys
import os
import time
import requests
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import logging
import json
from typing import Dict, List, Optional, Tuple

class FMPStockDataProcessor:
    def __init__(self, api_key: str):
        """
        初始化 FMP 數據處理器
        
        Args:
            api_key: Financial Modeling Prep API 金鑰
        """
        self.api_key = api_key
        self.base_url = "https://financialmodelingprep.com/api/v3"
        self.setup_logging()
        
        # 目標年份範圍 (2014-2024)
        self.target_years = list(range(2014, 2025))
        
        # 200家知名股票代號
        self.stock_list = [
            # 科技巨頭
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
            'CMG', 'ORLY', 'AZO', 'AAP', 'GM', 'F', 'RACE', 'RIVN', 'LCID',
            
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
            'IFF', 'FMC', 'LYB', 'ALB', 'VMC', 'MLM', 'STLD', 'RS', 'RPM',
            
            # REITs
            'PLD', 'AMT', 'CCI', 'EQIX', 'PSA', 'EXR', 'AVB', 'EQR', 'WELL', 'MAA',
            'UDR', 'CPT', 'ESS', 'FRT', 'AIV', 'BXP', 'VTR', 'O', 'STOR', 'SPG',
            
            # 通訊服務  
            'TMUS', 'DISH'
        ]
        
        # 移除重複項目並排序
        self.stock_list = sorted(list(set(self.stock_list)))
        
        # 資料庫配置
        self.db_config = {
            'host': '13.114.174.139',
            'database': 'finbot_db',
            'user': 'myuser',
            'password': '123456789',
            'charset': 'utf8mb4'
        }
        
        self.start_time = time.time()
        
        self.logger.info(f"FMP 股票數據處理器初始化完成")
        self.logger.info(f"目標股票數量: {len(self.stock_list)}")
        self.logger.info(f"目標年份: {self.target_years[0]}-{self.target_years[-1]}")
        
    def setup_logging(self):
        """設置日誌"""
        log_filename = f"fmp_stock_processor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("FMP 股票數據處理器啟動")
    
    def make_api_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """
        發送 FMP API 請求
        
        Args:
            endpoint: API 端點
            params: 額外參數
            
        Returns:
            API 回應數據或 None
        """
        try:
            if params is None:
                params = {}
            
            # 添加 API 金鑰
            params['apikey'] = self.api_key
            
            url = f"{self.base_url}/{endpoint}"
            self.logger.debug(f"發送請求到: {url}")
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # 檢查是否有錯誤訊息
            if isinstance(data, dict) and 'Error Message' in data:
                self.logger.error(f"API 錯誤: {data['Error Message']}")
                return None
                
            return data
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API 請求失敗: {e}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON 解析失敗: {e}")
            return None
    
    def get_company_profile(self, ticker: str) -> Optional[str]:
        """獲取公司名稱"""
        try:
            data = self.make_api_request(f"profile/{ticker}")
            if data and isinstance(data, list) and len(data) > 0:
                return data[0].get('companyName', ticker)
            return ticker
        except Exception as e:
            self.logger.error(f"獲取公司名稱失敗 {ticker}: {e}")
            return ticker
    
    def get_income_statement(self, ticker: str, year: int) -> Optional[Dict]:
        """獲取損益表數據"""
        try:
            params = {'period': 'annual', 'limit': 120}
            data = self.make_api_request(f"income-statement/{ticker}", params)
            
            if data and isinstance(data, list):
                for item in data:
                    # 檢查日期是否匹配目標年份
                    date_str = item.get('date', '')
                    if date_str and str(year) in date_str:
                        return item
            return None
            
        except Exception as e:
            self.logger.error(f"獲取損益表失敗 {ticker} {year}: {e}")
            return None
    
    def get_balance_sheet(self, ticker: str, year: int) -> Optional[Dict]:
        """獲取資產負債表數據"""
        try:
            params = {'period': 'annual', 'limit': 120}
            data = self.make_api_request(f"balance-sheet-statement/{ticker}", params)
            
            if data and isinstance(data, list):
                for item in data:
                    date_str = item.get('date', '')
                    if date_str and str(year) in date_str:
                        return item
            return None
            
        except Exception as e:
            self.logger.error(f"獲取資產負債表失敗 {ticker} {year}: {e}")
            return None
    
    def get_cash_flow_statement(self, ticker: str, year: int) -> Optional[Dict]:
        """獲取現金流量表數據"""
        try:
            params = {'period': 'annual', 'limit': 120}
            data = self.make_api_request(f"cash-flow-statement/{ticker}", params)
            
            if data and isinstance(data, list):
                for item in data:
                    date_str = item.get('date', '')
                    if date_str and str(year) in date_str:
                        return item
            return None
            
        except Exception as e:
            self.logger.error(f"獲取現金流量表失敗 {ticker} {year}: {e}")
            return None
    
    def combine_financial_data(self, ticker: str, year: int, 
                              income_stmt: Dict, balance_sheet: Dict, 
                              cash_flow: Dict, company_name: str) -> Dict:
        """
        組合三大財務報表數據，對應到 filings 資料表欄位
        
        Returns:
            包含所有財務指標的字典
        """
        try:
            # 基本資訊
            filing_data = {
                'ticker': ticker,
                'company_name': company_name,
                'filing_type': 'ANNUAL_FINANCIAL',
                'filing_year': year,
                'data_source': 'fmp_api',
                'data_quality_score': 95.0,
                'data_quality_flag': 'excellent'
            }
            
            # 從損益表抓取數據 (轉換為百萬美元)
            if income_stmt:
                filing_data.update({
                    'revenue': self.safe_convert_to_millions(income_stmt.get('revenue')),
                    'gross_profit': self.safe_convert_to_millions(income_stmt.get('grossProfit')),
                    'operating_expenses': self.safe_convert_to_millions(income_stmt.get('operatingExpenses')),
                    'operating_income': self.safe_convert_to_millions(income_stmt.get('operatingIncome')),
                    'income_before_tax': self.safe_convert_to_millions(income_stmt.get('incomeBeforeTax')),
                    'net_income': self.safe_convert_to_millions(income_stmt.get('netIncome')),
                    'eps_basic': self.safe_convert_float(income_stmt.get('eps')),
                    'outstanding_shares': self.safe_convert_to_millions(income_stmt.get('weightedAverageShsOut')),
                    'cogs': self.safe_convert_to_millions(income_stmt.get('costOfRevenue'))
                })
            
            # 從資產負債表抓取數據
            if balance_sheet:
                filing_data.update({
                    'shareholders_equity': self.safe_convert_to_millions(balance_sheet.get('totalStockholdersEquity')),
                    'total_assets': self.safe_convert_to_millions(balance_sheet.get('totalAssets')),
                    'total_liabilities': self.safe_convert_to_millions(balance_sheet.get('totalLiabilities')),
                    'long_term_debt': self.safe_convert_to_millions(balance_sheet.get('longTermDebt')),
                    'retained_earnings_balance': self.safe_convert_to_millions(balance_sheet.get('retainedEarnings')),
                    'current_assets': self.safe_convert_to_millions(balance_sheet.get('totalCurrentAssets')),
                    'current_liabilities': self.safe_convert_to_millions(balance_sheet.get('totalCurrentLiabilities')),
                    'cash_and_cash_equivalents': self.safe_convert_to_millions(balance_sheet.get('cashAndCashEquivalents'))
                })
                
                # 計算流動比率
                current_assets = filing_data.get('current_assets')
                current_liabilities = filing_data.get('current_liabilities')
                if current_assets and current_liabilities and current_liabilities != 0:
                    filing_data['current_ratio'] = round(current_assets / current_liabilities, 4)
            
            # 從現金流量表抓取數據
            if cash_flow:
                filing_data.update({
                    'operating_cash_flow': self.safe_convert_to_millions(cash_flow.get('netCashProvidedByOperatingActivities')),
                    'cash_flow_investing': self.safe_convert_to_millions(cash_flow.get('netCashUsedForInvestingActivites')),
                    'cash_flow_financing': self.safe_convert_to_millions(cash_flow.get('netCashUsedProvidedByFinancingActivities')),
                    'free_cash_flow': self.safe_convert_to_millions(cash_flow.get('freeCashFlow'))
                })
            
            return filing_data
            
        except Exception as e:
            self.logger.error(f"組合財務數據失敗 {ticker} {year}: {e}")
            return {}
    
    def safe_convert_to_millions(self, value) -> Optional[float]:
        """安全轉換數值為百萬單位"""
        try:
            if value is None or value == '':
                return None
            
            # 如果已經是數字，直接轉換為百萬
            if isinstance(value, (int, float)):
                return round(float(value) / 1000000, 2) if value != 0 else 0.0
            
            # 如果是字串，先轉為數字再轉換
            if isinstance(value, str):
                # 移除逗號和其他符號
                clean_value = value.replace(',', '').replace('$', '').replace('(', '').replace(')', '')
                if clean_value.lower() in ['n/a', 'na', '-', '']:
                    return None
                num_value = float(clean_value)
                return round(num_value / 1000000, 2) if num_value != 0 else 0.0
            
            return None
            
        except (ValueError, TypeError, AttributeError):
            return None
    
    def safe_convert_float(self, value) -> Optional[float]:
        """安全轉換為浮點數"""
        try:
            if value is None or value == '':
                return None
            
            if isinstance(value, (int, float)):
                return round(float(value), 4)
            
            if isinstance(value, str):
                clean_value = value.replace(',', '').replace('$', '').replace('(', '').replace(')', '')
                if clean_value.lower() in ['n/a', 'na', '-', '']:
                    return None
                return round(float(clean_value), 4)
            
            return None
            
        except (ValueError, TypeError, AttributeError):
            return None
    
    def check_existing_data(self, ticker: str, year: int) -> bool:
        """檢查資料庫中是否已存在該股票年份的數據"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            query = """
                SELECT COUNT(*) FROM filings 
                WHERE ticker = %s AND filing_year = %s 
                AND data_source = 'fmp_api'
            """
            cursor.execute(query, (ticker, year))
            count = cursor.fetchone()[0]
            
            cursor.close()
            connection.close()
            
            return count > 0
            
        except Error as e:
            self.logger.error(f"檢查現有數據失敗 {ticker} {year}: {e}")
            return False
    
    def save_to_database(self, filing_data: Dict) -> bool:
        """將財務數據存入資料庫"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            # 檢查是否已存在，如存在則更新，否則插入
            check_query = """
                SELECT id FROM filings 
                WHERE ticker = %s AND filing_year = %s
            """
            cursor.execute(check_query, (filing_data['ticker'], filing_data['filing_year']))
            existing = cursor.fetchone()
            
            if existing:
                # 更新現有記錄
                update_query = """
                    UPDATE filings SET
                        company_name = %s, filing_type = %s, data_source = %s,
                        data_quality_score = %s, data_quality_flag = %s,
                        revenue = %s, gross_profit = %s, operating_expenses = %s,
                        operating_income = %s, income_before_tax = %s, net_income = %s,
                        eps_basic = %s, outstanding_shares = %s, cogs = %s,
                        operating_cash_flow = %s, shareholders_equity = %s,
                        total_assets = %s, total_liabilities = %s, long_term_debt = %s,
                        retained_earnings_balance = %s, current_assets = %s,
                        current_liabilities = %s, current_ratio = %s,
                        free_cash_flow = %s, cash_flow_investing = %s,
                        cash_flow_financing = %s, cash_and_cash_equivalents = %s,
                        last_updated = NOW()
                    WHERE ticker = %s AND filing_year = %s
                """
                values = (
                    filing_data.get('company_name'), filing_data.get('filing_type'),
                    filing_data.get('data_source'), filing_data.get('data_quality_score'),
                    filing_data.get('data_quality_flag'), filing_data.get('revenue'),
                    filing_data.get('gross_profit'), filing_data.get('operating_expenses'),
                    filing_data.get('operating_income'), filing_data.get('income_before_tax'),
                    filing_data.get('net_income'), filing_data.get('eps_basic'),
                    filing_data.get('outstanding_shares'), filing_data.get('cogs'),
                    filing_data.get('operating_cash_flow'), filing_data.get('shareholders_equity'),
                    filing_data.get('total_assets'), filing_data.get('total_liabilities'),
                    filing_data.get('long_term_debt'), filing_data.get('retained_earnings_balance'),
                    filing_data.get('current_assets'), filing_data.get('current_liabilities'),
                    filing_data.get('current_ratio'), filing_data.get('free_cash_flow'),
                    filing_data.get('cash_flow_investing'), filing_data.get('cash_flow_financing'),
                    filing_data.get('cash_and_cash_equivalents'),
                    filing_data.get('ticker'), filing_data.get('filing_year')
                )
                cursor.execute(update_query, values)
                action = "更新"
            else:
                # 插入新記錄
                insert_query = """
                    INSERT INTO filings (
                        ticker, company_name, filing_type, filing_year, data_source,
                        data_quality_score, data_quality_flag, revenue, gross_profit,
                        operating_expenses, operating_income, income_before_tax, net_income,
                        eps_basic, outstanding_shares, cogs, operating_cash_flow,
                        shareholders_equity, total_assets, total_liabilities, long_term_debt,
                        retained_earnings_balance, current_assets, current_liabilities,
                        current_ratio, free_cash_flow, cash_flow_investing,
                        cash_flow_financing, cash_and_cash_equivalents
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """
                values = (
                    filing_data.get('ticker'), filing_data.get('company_name'),
                    filing_data.get('filing_type'), filing_data.get('filing_year'),
                    filing_data.get('data_source'), filing_data.get('data_quality_score'),
                    filing_data.get('data_quality_flag'), filing_data.get('revenue'),
                    filing_data.get('gross_profit'), filing_data.get('operating_expenses'),
                    filing_data.get('operating_income'), filing_data.get('income_before_tax'),
                    filing_data.get('net_income'), filing_data.get('eps_basic'),
                    filing_data.get('outstanding_shares'), filing_data.get('cogs'),
                    filing_data.get('operating_cash_flow'), filing_data.get('shareholders_equity'),
                    filing_data.get('total_assets'), filing_data.get('total_liabilities'),
                    filing_data.get('long_term_debt'), filing_data.get('retained_earnings_balance'),
                    filing_data.get('current_assets'), filing_data.get('current_liabilities'),
                    filing_data.get('current_ratio'), filing_data.get('free_cash_flow'),
                    filing_data.get('cash_flow_investing'), filing_data.get('cash_flow_financing'),
                    filing_data.get('cash_and_cash_equivalents')
                )
                cursor.execute(insert_query, values)
                action = "插入"
            
            connection.commit()
            cursor.close()
            connection.close()
            
            self.logger.info(f"成功{action}數據: {filing_data['ticker']} {filing_data['filing_year']}")
            return True
            
        except Error as e:
            self.logger.error(f"存入資料庫失敗: {e}")
            return False
    
    def process_single_stock_year(self, ticker: str, year: int, company_name: str) -> Tuple[bool, str]:
        """處理單一股票的單一年份數據"""
        try:
            self.logger.info(f"處理 {ticker} {year} 年度數據...")
            
            # 檢查是否已存在
            if self.check_existing_data(ticker, year):
                return True, "已存在"
            
            # 獲取三大財務報表
            income_stmt = self.get_income_statement(ticker, year)
            balance_sheet = self.get_balance_sheet(ticker, year)
            cash_flow = self.get_cash_flow_statement(ticker, year)
            
            # 檢查是否至少有一個報表有數據
            if not any([income_stmt, balance_sheet, cash_flow]):
                return False, f"{year}年無財務數據"
            
            # 組合財務數據
            filing_data = self.combine_financial_data(
                ticker, year, income_stmt, balance_sheet, cash_flow, company_name
            )
            
            if not filing_data:
                return False, f"{year}年數據組合失敗"
            
            # 存入資料庫
            if self.save_to_database(filing_data):
                return True, f"{year}年數據成功存入"
            else:
                return False, f"{year}年存入資料庫失敗"
                
        except Exception as e:
            self.logger.error(f"處理 {ticker} {year} 失敗: {e}")
            return False, f"{year}年處理錯誤: {str(e)}"
    
    def process_single_stock(self, ticker: str, index: int, total: int) -> Tuple[int, int, List[str]]:
        """
        處理單一股票的所有年份數據
        
        Returns:
            (成功年份數, 失敗年份數, 詳細結果列表)
        """
        self.logger.info(f"[{index}/{total}] 開始處理股票: {ticker}")
        
        try:
            # 獲取公司名稱
            company_name = self.get_company_profile(ticker)
            self.logger.info(f"{ticker} 公司名稱: {company_name}")
            
            success_count = 0
            failure_count = 0
            results = []
            
            # 處理每個年份
            for year in self.target_years:
                try:
                    success, message = self.process_single_stock_year(ticker, year, company_name)
                    
                    if success:
                        if "已存在" not in message:
                            success_count += 1
                        results.append(f"✅ {year}: {message}")
                    else:
                        failure_count += 1
                        results.append(f"❌ {year}: {message}")
                    
                    # API 請求間隔
                    time.sleep(0.5)
                    
                except Exception as e:
                    failure_count += 1
                    results.append(f"❌ {year}: 錯誤 - {str(e)}")
                    self.logger.error(f"{ticker} {year} 處理錯誤: {e}")
            
            self.logger.info(f"{ticker} 處理完成: 成功 {success_count} 年，失敗 {failure_count} 年")
            return success_count, failure_count, results
            
        except Exception as e:
            self.logger.error(f"處理股票 {ticker} 失敗: {e}")
            return 0, len(self.target_years), [f"❌ 股票處理失敗: {str(e)}"]
    
    def run_batch_processing(self):
        """執行批量處理"""
        self.logger.info("="*80)
        self.logger.info("開始 FMP API 批量股票財務數據抓取")
        self.logger.info(f"目標股票數量: {len(self.stock_list)}")
        self.logger.info(f"目標年份範圍: {self.target_years[0]}-{self.target_years[-1]}")
        self.logger.info("="*80)
        
        # 統計變數
        total_stocks = len(self.stock_list)
        processed_stocks = 0
        total_success_years = 0
        total_failure_years = 0
        
        # 處理結果記錄
        detailed_results = {}
        
        for index, ticker in enumerate(self.stock_list, 1):
            try:
                # 顯示進度
                elapsed_time = time.time() - self.start_time
                if processed_stocks > 0:
                    avg_time_per_stock = elapsed_time / processed_stocks
                    remaining_stocks = total_stocks - processed_stocks
                    estimated_remaining_time = avg_time_per_stock * remaining_stocks
                    
                    self.logger.info(f"進度: {processed_stocks}/{total_stocks} ({(processed_stocks/total_stocks)*100:.1f}%)")
                    self.logger.info(f"已耗時: {elapsed_time/60:.1f}分鐘，預估剩餘: {estimated_remaining_time/60:.1f}分鐘")
                
                # 處理股票
                success_years, failure_years, results = self.process_single_stock(ticker, index, total_stocks)
                
                processed_stocks += 1
                total_success_years += success_years
                total_failure_years += failure_years
                detailed_results[ticker] = results
                
                # 每處理5隻股票休息一下
                if index % 5 == 0:
                    self.logger.info("處理5隻股票後休息10秒...")
                    time.sleep(10)
                
            except KeyboardInterrupt:
                self.logger.info("用戶中斷處理")
                break
            except Exception as e:
                self.logger.error(f"處理 {ticker} 時發生未預期錯誤: {e}")
                processed_stocks += 1
                detailed_results[ticker] = [f"❌ 未預期錯誤: {str(e)}"]
        
        # 最終統計報告
        total_time = time.time() - self.start_time
        self.logger.info("="*80)
        self.logger.info("FMP API 批量處理完成統計報告")
        self.logger.info("="*80)
        self.logger.info(f"總處理時間: {total_time/60:.1f}分鐘")
        self.logger.info(f"處理股票數: {processed_stocks}/{total_stocks}")
        self.logger.info(f"成功年份數: {total_success_years}")
        self.logger.info(f"失敗年份數: {total_failure_years}")
        self.logger.info(f"總年份數: {total_success_years + total_failure_years}")
        
        success_rate = (total_success_years / (total_success_years + total_failure_years) * 100) if (total_success_years + total_failure_years) > 0 else 0
        self.logger.info(f"年份成功率: {success_rate:.1f}%")
        
        return {
            'processed_stocks': processed_stocks,
            'total_stocks': total_stocks,
            'success_years': total_success_years,
            'failure_years': total_failure_years,
            'detailed_results': detailed_results
        }

def main():
    """主程式"""
    print("🚀 FinBot FMP API 財務數據抓取器")
    print("="*60)
    print("功能: 使用 Financial Modeling Prep API 抓取美股財務數據")
    print("年份範圍: 2014-2024")
    print("數據源: FMP API (損益表 + 資產負債表 + 現金流量表)")
    print("目標: filings 資料表")
    print("="*60)
    
    # 使用您提供的 API 金鑰
    api_key = "f1dtgv3q9ZlPAwMNWfxTnhsozQB26lKe"
    print(f"使用 API Key: {api_key}")
    print()
    
    # 確認執行
    confirm = input("確定要開始批量處理嗎？這可能需要數小時 (y/N): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("取消執行")
        return
    
    # 創建處理器並執行
    processor = FMPStockDataProcessor(api_key)
    
    try:
        results = processor.run_batch_processing()
        
        print("\n" + "="*60)
        print("🎉 FMP API 批量處理完成！")
        print(f"處理股票: {results['processed_stocks']}/{results['total_stocks']}")
        print(f"成功年份: {results['success_years']}")
        print(f"失敗年份: {results['failure_years']}")
        success_rate = (results['success_years'] / (results['success_years'] + results['failure_years']) * 100) if (results['success_years'] + results['failure_years']) > 0 else 0
        print(f"成功率: {success_rate:.1f}%")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n用戶中斷執行")
    except Exception as e:
        print(f"\n程式執行失敗: {e}")
        logging.error(f"程式執行失敗: {e}")

if __name__ == "__main__":
    main()
