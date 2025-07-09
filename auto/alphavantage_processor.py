#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alpha Vantage 財務數據抓取器
免費API，提供完整的歷史財務數據（2000年至今）
每分鐘5次請求，每日25次限制
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

class AlphaVantageProcessor:
    def __init__(self, api_key: str):
        """
        初始化 Alpha Vantage 數據處理器
        
        Args:
            api_key: Alpha Vantage API 金鑰
        """
        self.api_key = 'JN9MYEPVM0WGEJ6C'
        self.base_url = "https://www.alphavantage.co/query"
        self.setup_logging()
        
        # 目標年份範圍 (2014-2024)
        self.target_years = list(range(2014, 2025))
        
        # 資料庫配置
        self.db_config = {
            'host': '35.72.199.133',
            'database': 'finbot_db',
            'user': 'admin_user',
            'password': '123456789',
            'charset': 'utf8mb4'
        }
        
        self.start_time = time.time()
        self.logger.info("Alpha Vantage 處理器初始化完成")
        
    def setup_logging(self):
        """設置日誌"""
        log_filename = f"alphavantage_processor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("Alpha Vantage 處理器啟動")
    
    def make_api_request(self, function: str, symbol: str, **params) -> Optional[Dict]:
        """
        發送 Alpha Vantage API 請求
        
        Args:
            function: API 函數名稱
            symbol: 股票代碼
            **params: 額外參數
            
        Returns:
            API 回應數據或 None
        """
        try:
            # 基本參數
            request_params = {
                'function': function,
                'symbol': symbol,
                'apikey': self.api_key
            }
            
            # 添加額外參數
            request_params.update(params)
            
            self.logger.debug(f"發送請求: {function} for {symbol}")
            
            response = requests.get(self.base_url, params=request_params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # 檢查API限制
            if 'Error Message' in data:
                self.logger.error(f"API 錯誤: {data['Error Message']}")
                return None
            
            if 'Note' in data:
                self.logger.warning(f"API 限制: {data['Note']}")
                return None
                
            return data
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API 請求失敗: {e}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON 解析失敗: {e}")
            return None
    
    def get_company_overview(self, symbol: str) -> Optional[str]:
        """獲取公司名稱"""
        try:
            data = self.make_api_request('OVERVIEW', symbol)
            if data and 'Name' in data:
                return data['Name']
            return symbol
        except Exception as e:
            self.logger.error(f"獲取公司名稱失敗 {symbol}: {e}")
            return symbol
    
    def get_income_statement(self, symbol: str) -> Optional[Dict]:
        """獲取損益表數據"""
        try:
            data = self.make_api_request('INCOME_STATEMENT', symbol)
            if data and 'annualReports' in data:
                return data['annualReports']
            return None
        except Exception as e:
            self.logger.error(f"獲取損益表失敗 {symbol}: {e}")
            return None
    
    def get_balance_sheet(self, symbol: str) -> Optional[Dict]:
        """獲取資產負債表數據"""
        try:
            data = self.make_api_request('BALANCE_SHEET', symbol)
            if data and 'annualReports' in data:
                return data['annualReports']
            return None
        except Exception as e:
            self.logger.error(f"獲取資產負債表失敗 {symbol}: {e}")
            return None
    
    def get_cash_flow(self, symbol: str) -> Optional[Dict]:
        """獲取現金流量表數據"""
        try:
            data = self.make_api_request('CASH_FLOW', symbol)
            if data and 'annualReports' in data:
                return data['annualReports']
            return None
        except Exception as e:
            self.logger.error(f"獲取現金流量表失敗 {symbol}: {e}")
            return None
    
    def find_year_data(self, reports: List[Dict], year: int) -> Optional[Dict]:
        """在報表列表中查找指定年份的數據"""
        if not reports:
            return None
            
        for report in reports:
            fiscal_date = report.get('fiscalDateEnding', '')
            if fiscal_date and str(year) in fiscal_date:
                return report
        return None
    
    def safe_convert_to_millions(self, value: str) -> Optional[float]:
        """安全轉換數值為百萬單位"""
        try:
            if not value or value in ['None', 'null', '']:
                return None
            
            # 移除可能的字符
            clean_value = str(value).replace(',', '').replace('$', '').replace('(', '-').replace(')', '')
            
            if clean_value.lower() in ['n/a', 'na', '-', '']:
                return None
                
            num_value = float(clean_value)
            return round(num_value / 1000000, 2) if num_value != 0 else 0.0
            
        except (ValueError, TypeError):
            return None
    
    def safe_convert_float(self, value: str) -> Optional[float]:
        """安全轉換為浮點數"""
        try:
            if not value or value in ['None', 'null', '']:
                return None
                
            clean_value = str(value).replace(',', '').replace('$', '')
            if clean_value.lower() in ['n/a', 'na', '-', '']:
                return None
                
            return round(float(clean_value), 4)
            
        except (ValueError, TypeError):
            return None
    
    def combine_financial_data(self, symbol: str, year: int, 
                              income_data: Dict, balance_data: Dict, 
                              cash_data: Dict, company_name: str) -> Dict:
        """組合財務數據"""
        try:
            filing_data = {
                'ticker': symbol,
                'company_name': company_name,
                'filing_type': 'ANNUAL_FINANCIAL',
                'filing_year': year,
                'data_source': 'alphavantage_api',
                'data_quality_score': 95.0,
                'data_quality_flag': 'excellent'
            }
            
            # 從損益表抓取數據
            if income_data:
                filing_data.update({
                    'revenue': self.safe_convert_to_millions(income_data.get('totalRevenue')),
                    'gross_profit': self.safe_convert_to_millions(income_data.get('grossProfit')),
                    'operating_income': self.safe_convert_to_millions(income_data.get('operatingIncome')),
                    'income_before_tax': self.safe_convert_to_millions(income_data.get('incomeBeforeTax')),
                    'net_income': self.safe_convert_to_millions(income_data.get('netIncome')),
                    'cogs': self.safe_convert_to_millions(income_data.get('costOfRevenue')),
                    'operating_expenses': self.safe_convert_to_millions(income_data.get('operatingExpenses')),
                    # 新增：EPS 數據
                    'eps_basic': self.safe_convert_float(income_data.get('reportedEPS')),
                    # 新增：流通股數（從 weightedAverageShsOutDil 獲取，轉換為百萬股）
                    'outstanding_shares': self.safe_convert_to_millions(income_data.get('weightedAverageShsOutDil'))
                })
            
            # 從資產負債表抓取數據
            if balance_data:
                filing_data.update({
                    'total_assets': self.safe_convert_to_millions(balance_data.get('totalAssets')),
                    'total_liabilities': self.safe_convert_to_millions(balance_data.get('totalLiabilities')),
                    'shareholders_equity': self.safe_convert_to_millions(balance_data.get('totalShareholderEquity')),
                    'long_term_debt': self.safe_convert_to_millions(balance_data.get('longTermDebt')),
                    'retained_earnings_balance': self.safe_convert_to_millions(balance_data.get('retainedEarnings')),
                    'current_assets': self.safe_convert_to_millions(balance_data.get('totalCurrentAssets')),
                    'current_liabilities': self.safe_convert_to_millions(balance_data.get('totalCurrentLiabilities')),
                    'cash_and_cash_equivalents': self.safe_convert_to_millions(balance_data.get('cashAndCashEquivalentsAtCarryingValue'))
                })
                
                # 計算流動比率
                current_assets = filing_data.get('current_assets')
                current_liabilities = filing_data.get('current_liabilities')
                if current_assets and current_liabilities and current_liabilities != 0:
                    filing_data['current_ratio'] = round(current_assets / current_liabilities, 4)
            
            # 從現金流量表抓取數據
            if cash_data:
                operating_cash_flow = self.safe_convert_to_millions(cash_data.get('operatingCashflow'))
                cash_flow_investing = self.safe_convert_to_millions(cash_data.get('cashflowFromInvestment'))
                
                filing_data.update({
                    'operating_cash_flow': operating_cash_flow,
                    'cash_flow_investing': cash_flow_investing,
                    'cash_flow_financing': self.safe_convert_to_millions(cash_data.get('cashflowFromFinancing'))
                })
                
                # 計算自由現金流 = 經營現金流 + 投資現金流中的資本支出部分
                # 注意：Alpha Vantage 的投資現金流通常是負數，代表現金流出
                if operating_cash_flow is not None:
                    # 嘗試從現金流數據中獲取資本支出
                    capital_expenditures = self.safe_convert_to_millions(cash_data.get('capitalExpenditures'))
                    if capital_expenditures is not None:
                        # 資本支出通常是負數，自由現金流 = 經營現金流 + 資本支出
                        filing_data['free_cash_flow'] = round(operating_cash_flow + capital_expenditures, 2)
                    else:
                        # 如果沒有明確的資本支出數據，使用簡化計算
                        # 假設投資現金流主要是資本支出（這是簡化假設）
                        if cash_flow_investing is not None and cash_flow_investing < 0:
                            # 只考慮負的投資現金流（現金流出）作為資本支出的近似
                            filing_data['free_cash_flow'] = round(operating_cash_flow + cash_flow_investing, 2)
            
            return filing_data
            
        except Exception as e:
            self.logger.error(f"組合財務數據失敗 {symbol} {year}: {e}")
            return {}
    
    def save_to_database(self, filing_data: Dict) -> bool:
        """將財務數據存入資料庫"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            # 檢查是否已存在
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
                        cogs = %s, operating_cash_flow = %s, shareholders_equity = %s,
                        total_assets = %s, total_liabilities = %s, long_term_debt = %s,
                        retained_earnings_balance = %s, current_assets = %s,
                        current_liabilities = %s, current_ratio = %s,
                        cash_flow_investing = %s, cash_flow_financing = %s,
                        cash_and_cash_equivalents = %s, eps_basic = %s,
                        outstanding_shares = %s, free_cash_flow = %s, last_updated = NOW()
                    WHERE ticker = %s AND filing_year = %s
                """
                values = (
                    filing_data.get('company_name'), filing_data.get('filing_type'),
                    filing_data.get('data_source'), filing_data.get('data_quality_score'),
                    filing_data.get('data_quality_flag'), filing_data.get('revenue'),
                    filing_data.get('gross_profit'), filing_data.get('operating_expenses'),
                    filing_data.get('operating_income'), filing_data.get('income_before_tax'),
                    filing_data.get('net_income'), filing_data.get('cogs'),
                    filing_data.get('operating_cash_flow'), filing_data.get('shareholders_equity'),
                    filing_data.get('total_assets'), filing_data.get('total_liabilities'),
                    filing_data.get('long_term_debt'), filing_data.get('retained_earnings_balance'),
                    filing_data.get('current_assets'), filing_data.get('current_liabilities'),
                    filing_data.get('current_ratio'), filing_data.get('cash_flow_investing'),
                    filing_data.get('cash_flow_financing'), filing_data.get('cash_and_cash_equivalents'),
                    filing_data.get('eps_basic'), filing_data.get('outstanding_shares'),
                    filing_data.get('free_cash_flow'), filing_data.get('ticker'), filing_data.get('filing_year')
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
                        cogs, operating_cash_flow, shareholders_equity, total_assets,
                        total_liabilities, long_term_debt, retained_earnings_balance,
                        current_assets, current_liabilities, current_ratio,
                        cash_flow_investing, cash_flow_financing, cash_and_cash_equivalents,
                        eps_basic, outstanding_shares, free_cash_flow
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
                    filing_data.get('net_income'), filing_data.get('cogs'),
                    filing_data.get('operating_cash_flow'), filing_data.get('shareholders_equity'),
                    filing_data.get('total_assets'), filing_data.get('total_liabilities'),
                    filing_data.get('long_term_debt'), filing_data.get('retained_earnings_balance'),
                    filing_data.get('current_assets'), filing_data.get('current_liabilities'),
                    filing_data.get('current_ratio'), filing_data.get('cash_flow_investing'),
                    filing_data.get('cash_flow_financing'), filing_data.get('cash_and_cash_equivalents'),
                    filing_data.get('eps_basic'), filing_data.get('outstanding_shares'),
                    filing_data.get('free_cash_flow')
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
    
    def process_stock(self, symbol: str) -> Tuple[int, int, List[str]]:
        """處理單一股票的所有年份數據"""
        self.logger.info(f"開始處理股票: {symbol}")
        
        try:
            # 獲取公司名稱
            company_name = self.get_company_overview(symbol)
            self.logger.info(f"{symbol} 公司名稱: {company_name}")
            
            # 休息避免API限制 (每分鐘5次)
            time.sleep(15)
            
            # 獲取三大財務報表
            income_reports = self.get_income_statement(symbol)
            time.sleep(15)  # API限制間隔
            
            balance_reports = self.get_balance_sheet(symbol)
            time.sleep(15)  # API限制間隔
            
            cash_reports = self.get_cash_flow(symbol)
            time.sleep(15)  # API限制間隔
            
            success_count = 0
            failure_count = 0
            results = []
            
            # 處理每個年份
            for year in self.target_years:
                try:
                    # 查找該年份的數據
                    income_data = self.find_year_data(income_reports, year) if income_reports else None
                    balance_data = self.find_year_data(balance_reports, year) if balance_reports else None
                    cash_data = self.find_year_data(cash_reports, year) if cash_reports else None
                    
                    if not any([income_data, balance_data, cash_data]):
                        failure_count += 1
                        results.append(f"❌ {year}: 無財務數據")
                        continue
                    
                    # 組合財務數據
                    filing_data = self.combine_financial_data(
                        symbol, year, income_data, balance_data, cash_data, company_name
                    )
                    
                    if not filing_data:
                        failure_count += 1
                        results.append(f"❌ {year}: 數據組合失敗")
                        continue
                    
                    # 存入資料庫
                    if self.save_to_database(filing_data):
                        success_count += 1
                        results.append(f"✅ {year}: 數據成功存入")
                    else:
                        failure_count += 1
                        results.append(f"❌ {year}: 存入資料庫失敗")
                        
                except Exception as e:
                    failure_count += 1
                    results.append(f"❌ {year}: 錯誤 - {str(e)}")
                    self.logger.error(f"{symbol} {year} 處理錯誤: {e}")
            
            self.logger.info(f"{symbol} 處理完成: 成功 {success_count} 年，失敗 {failure_count} 年")
            return success_count, failure_count, results
            
        except Exception as e:
            self.logger.error(f"處理股票 {symbol} 失敗: {e}")
            return 0, len(self.target_years), [f"❌ 股票處理失敗: {str(e)}"]

def test_amzn_with_alphavantage():
    """測試使用 Alpha Vantage API 處理 AMZN"""
    print("🧪 Alpha Vantage API - AMZN 測試")
    print("="*50)
    print("免費額度: 每分鐘5次請求，每日25次")
    print("數據範圍: 2000年至今")
    print("="*50)
    
    # 使用已設定的 API Key
    api_key = 'JN9MYEPVM0WGEJ6C'
    
    processor = AlphaVantageProcessor(api_key)
    
    print("\n開始處理 AMZN...")
    print("⚠️ 注意：由於API限制，整個過程需要約5分鐘")
    
    success_count, failure_count, results = processor.process_stock('AMZN')
    
    print("\n" + "="*50)
    print("🎉 Alpha Vantage - AMZN 處理完成！")
    print(f"成功年份: {success_count}")
    print(f"失敗年份: {failure_count}")
    success_rate = (success_count / (success_count + failure_count) * 100) if (success_count + failure_count) > 0 else 0
    print(f"成功率: {success_rate:.1f}%")
    print("="*50)
    
    print("\n🎯 詳細結果：")
    for result in results:
        print(f"  {result}")
    
    return success_count, failure_count, results

if __name__ == "__main__":
    test_amzn_with_alphavantage() 