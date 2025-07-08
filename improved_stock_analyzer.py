#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改進版股票數據分析器 - 解決數據抓取不完整問題
專門針對MSFT等股票的數據缺失進行優化
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import yfinance as yf
import time
from datetime import datetime, timedelta
import sys
import mysql.connector
from mysql.connector import Error
import os
from decimal import Decimal
import re
import json

class ImprovedStockAnalyzer:
    def __init__(self, db_config=None):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # 資料庫配置
        self.db_config = db_config or {
            'host': '13.114.174.139',
            'database': 'finbot_db',
            'user': 'myuser',
            'password': '123456789',
            'charset': 'utf8mb4'
        }
        
        self.db_connection = None
        
        # 已知的公司slug映射（大幅擴展）
        self.known_slugs = {
            'AAPL': 'apple',
            'MSFT': 'microsoft',
            'GOOGL': 'alphabet',
            'GOOG': 'alphabet', 
            'AMZN': 'amazon',
            'TSLA': 'tesla',
            'META': 'meta-platforms',
            'NVDA': 'nvidia',
            'NFLX': 'netflix',
            'CRM': 'salesforce',
            'ORCL': 'oracle',
            'IBM': 'ibm',
            'INTC': 'intel',
            'AMD': 'amd',
            'ADBE': 'adobe',
            'PYPL': 'paypal'
        }
    
    def connect_database(self):
        """連接資料庫"""
        try:
            self.db_connection = mysql.connector.connect(**self.db_config)
            if self.db_connection.is_connected():
                print("資料庫連接成功")
                return True
        except Error as e:
            print(f"資料庫連接失敗: {e}")
            return False
    
    def disconnect_database(self):
        """斷開資料庫連接"""
        if self.db_connection and self.db_connection.is_connected():
            self.db_connection.close()
            print("資料庫連接已關閉")
    
    def get_comprehensive_yahoo_data(self, ticker):
        """從Yahoo Finance獲取完整的財務數據"""
        print(f"從Yahoo Finance抓取 {ticker} 的完整數據...")
        
        try:
            stock = yf.Ticker(ticker)
            
            # 獲取財務報表
            financials = stock.financials
            balance_sheet = stock.balance_sheet
            cash_flow = stock.cashflow
            
            yahoo_data = {}
            
            # 收入數據（嘗試多個可能的欄位名稱）
            revenue_labels = ['Total Revenue', 'Generating Revenue', 'Revenue']
            for label in revenue_labels:
                if label in financials.index:
                    revenue_data = financials.loc[label].dropna()
                    revenue_df = pd.DataFrame({
                        'Year': [date.year for date in revenue_data.index],
                        'Revenue (M USD)': pd.to_numeric(revenue_data.values, errors='coerce') / 1e6
                    }).sort_values('Year', ascending=False)
                    yahoo_data['revenue'] = revenue_df
                    print(f"   收入數據: {len(revenue_df)} 年 (使用: {label})")
                    break
            
            # 淨利潤（嘗試多個可能的欄位名稱）
            income_labels = ['Net Income', 'Net Income Common Stockholders', 'Net Income From Continuing Operations']
            for label in income_labels:
                if label in financials.index:
                    income_data = financials.loc[label].dropna()
                    income_df = pd.DataFrame({
                        'Year': [date.year for date in income_data.index],
                        'Net Income (M USD)': pd.to_numeric(income_data.values, errors='coerce') / 1e6
                    }).sort_values('Year', ascending=False)
                    yahoo_data['income'] = income_df
                    print(f"   淨利潤數據: {len(income_df)} 年 (使用: {label})")
                    break
            
            # 營運現金流（嘗試多個可能的欄位名稱）
            cf_labels = ['Operating Cash Flow', 'Cash Flow From Continuing Operating Activities']
            for label in cf_labels:
                if label in cash_flow.index:
                    cf_data = cash_flow.loc[label].dropna()
                    cf_df = pd.DataFrame({
                        'Year': [date.year for date in cf_data.index],
                        'Operating Cash Flow (M USD)': pd.to_numeric(cf_data.values, errors='coerce') / 1e6
                    }).sort_values('Year', ascending=False)
                    yahoo_data['cash_flow'] = cf_df
                    print(f"   營運現金流數據: {len(cf_df)} 年 (使用: {label})")
                    break
            
            # 股東權益
            equity_labels = ['Stockholders Equity', 'Total Stockholder Equity', 'Shareholders Equity']
            for label in equity_labels:
                if label in balance_sheet.index:
                    equity_data = balance_sheet.loc[label].dropna()
                    equity_df = pd.DataFrame({
                        'Year': [date.year for date in equity_data.index],
                        'Shareholders Equity (M USD)': pd.to_numeric(equity_data.values, errors='coerce') / 1e6
                    }).sort_values('Year', ascending=False)
                    yahoo_data['equity'] = equity_df
                    print(f"   股東權益數據: {len(equity_df)} 年")
                    break
            
            # 總資產
            if 'Total Assets' in balance_sheet.index:
                assets_data = balance_sheet.loc['Total Assets'].dropna()
                assets_df = pd.DataFrame({
                    'Year': [date.year for date in assets_data.index],
                    'Total Assets (M USD)': pd.to_numeric(assets_data.values, errors='coerce') / 1e6
                }).sort_values('Year', ascending=False)
                yahoo_data['total_assets'] = assets_df
                print(f"   總資產數據: {len(assets_df)} 年")
            
            # 總負債（嘗試多個可能的欄位名稱）
            total_liab_labels = ['Total Liabilities Net Minority Interest', 'Total Liab', 'Total Liabilities']
            for label in total_liab_labels:
                if label in balance_sheet.index:
                    liab_data = balance_sheet.loc[label].dropna()
                    liab_df = pd.DataFrame({
                        'Year': [date.year for date in liab_data.index],
                        'Total Liabilities (M USD)': pd.to_numeric(liab_data.values, errors='coerce') / 1e6
                    }).sort_values('Year', ascending=False)
                    yahoo_data['total_liabilities'] = liab_df
                    print(f"   總負債數據: {len(liab_df)} 年 (使用: {label})")
                    break
            
            # 長期負債
            if 'Long Term Debt' in balance_sheet.index:
                debt_data = balance_sheet.loc['Long Term Debt'].dropna()
                debt_df = pd.DataFrame({
                    'Year': [date.year for date in debt_data.index],
                    'Long Term Debt (M USD)': pd.to_numeric(debt_data.values, errors='coerce') / 1e6
                }).sort_values('Year', ascending=False)
                yahoo_data['long_term_debt'] = debt_df
                print(f"   長期負債數據: {len(debt_df)} 年")
            
            # 流動資產
            if 'Current Assets' in balance_sheet.index:
                current_assets_data = balance_sheet.loc['Current Assets'].dropna()
                current_assets_df = pd.DataFrame({
                    'Year': [date.year for date in current_assets_data.index],
                    'Current Assets (M USD)': pd.to_numeric(current_assets_data.values, errors='coerce') / 1e6
                }).sort_values('Year', ascending=False)
                yahoo_data['current_assets'] = current_assets_df
                print(f"   流動資產數據: {len(current_assets_df)} 年")
            
            # 流動負債
            if 'Current Liabilities' in balance_sheet.index:
                current_liab_data = balance_sheet.loc['Current Liabilities'].dropna()
                current_liab_df = pd.DataFrame({
                    'Year': [date.year for date in current_liab_data.index],
                    'Current Liabilities (M USD)': pd.to_numeric(current_liab_data.values, errors='coerce') / 1e6
                }).sort_values('Year', ascending=False)
                yahoo_data['current_liabilities'] = current_liab_df
                print(f"   流動負債數據: {len(current_liab_df)} 年")
            
            # 自由現金流
            if 'Free Cash Flow' in cash_flow.index:
                fcf_data = cash_flow.loc['Free Cash Flow'].dropna()
                fcf_df = pd.DataFrame({
                    'Year': [date.year for date in fcf_data.index],
                    'Free Cash Flow (M USD)': pd.to_numeric(fcf_data.values, errors='coerce') / 1e6
                }).sort_values('Year', ascending=False)
                yahoo_data['free_cash_flow'] = fcf_df
                print(f"   自由現金流數據: {len(fcf_df)} 年")
            
            # 毛利潤（計算或直接獲取）
            if 'Gross Profit' in financials.index:
                gp_data = financials.loc['Gross Profit'].dropna()
                gp_df = pd.DataFrame({
                    'Year': [date.year for date in gp_data.index],
                    'Gross Profit (M USD)': pd.to_numeric(gp_data.values, errors='coerce') / 1e6
                }).sort_values('Year', ascending=False)
                yahoo_data['gross_profit'] = gp_df
                print(f"   毛利潤數據: {len(gp_df)} 年")
            
            # 營運費用
            if 'Operating Expense' in financials.index:
                oe_data = financials.loc['Operating Expense'].dropna()
                oe_df = pd.DataFrame({
                    'Year': [date.year for date in oe_data.index],
                    'Operating Expenses (M USD)': pd.to_numeric(oe_data.values, errors='coerce') / 1e6
                }).sort_values('Year', ascending=False)
                yahoo_data['operating_expenses'] = oe_df
                print(f"   營運費用數據: {len(oe_df)} 年")
            
            # 營運收入
            if 'Operating Income' in financials.index:
                oi_data = financials.loc['Operating Income'].dropna()
                oi_df = pd.DataFrame({
                    'Year': [date.year for date in oi_data.index],
                    'Operating Income (M USD)': pd.to_numeric(oi_data.values, errors='coerce') / 1e6
                }).sort_values('Year', ascending=False)
                yahoo_data['operating_income'] = oi_df
                print(f"   營運收入數據: {len(oi_df)} 年")
            
            # 稅前收入
            if 'Pretax Income' in financials.index:
                pi_data = financials.loc['Pretax Income'].dropna()
                pi_df = pd.DataFrame({
                    'Year': [date.year for date in pi_data.index],
                    'Income Before Tax (M USD)': pd.to_numeric(pi_data.values, errors='coerce') / 1e6
                }).sort_values('Year', ascending=False)
                yahoo_data['income_before_tax'] = pi_df
                print(f"   稅前收入數據: {len(pi_df)} 年")
            
            # EPS和股數
            try:
                if 'Basic EPS' in financials.index:
                    eps_data = financials.loc['Basic EPS'].dropna()
                    eps_df = pd.DataFrame({
                        'Year': [date.year for date in eps_data.index],
                        'EPS Basic (USD)': pd.to_numeric(eps_data.values, errors='coerce')
                    }).sort_values('Year', ascending=False)
                    yahoo_data['eps_basic'] = eps_df
                    print(f"   EPS數據: {len(eps_df)} 年")
                
                if 'Basic Average Shares' in financials.index:
                    shares_data = financials.loc['Basic Average Shares'].dropna()
                    shares_df = pd.DataFrame({
                        'Year': [date.year for date in shares_data.index],
                        'Outstanding Shares (M)': pd.to_numeric(shares_data.values, errors='coerce') / 1e6
                    }).sort_values('Year', ascending=False)
                    yahoo_data['outstanding_shares'] = shares_df
                    print(f"   股數數據: {len(shares_df)} 年")
            except:
                pass
            
            # 保留盈餘
            if 'Retained Earnings' in balance_sheet.index:
                re_data = balance_sheet.loc['Retained Earnings'].dropna()
                re_df = pd.DataFrame({
                    'Year': [date.year for date in re_data.index],
                    'Retained Earnings (M USD)': pd.to_numeric(re_data.values, errors='coerce') / 1e6
                }).sort_values('Year', ascending=False)
                yahoo_data['retained_earnings'] = re_df
                print(f"   保留盈餘數據: {len(re_df)} 年")
            
            # 投資現金流
            inv_cf_labels = ['Investing Cash Flow', 'Cash Flow From Continuing Investing Activities']
            for label in inv_cf_labels:
                if label in cash_flow.index:
                    inv_cf_data = cash_flow.loc[label].dropna()
                    inv_cf_df = pd.DataFrame({
                        'Year': [date.year for date in inv_cf_data.index],
                        'Cash Flow Investing (M USD)': pd.to_numeric(inv_cf_data.values, errors='coerce') / 1e6
                    }).sort_values('Year', ascending=False)
                    yahoo_data['cash_flow_investing'] = inv_cf_df
                    print(f"   投資現金流數據: {len(inv_cf_df)} 年 (使用: {label})")
                    break
            
            # 融資現金流
            fin_cf_labels = ['Financing Cash Flow', 'Cash Flow From Continuing Financing Activities']
            for label in fin_cf_labels:
                if label in cash_flow.index:
                    fin_cf_data = cash_flow.loc[label].dropna()
                    fin_cf_df = pd.DataFrame({
                        'Year': [date.year for date in fin_cf_data.index],
                        'Cash Flow Financing (M USD)': pd.to_numeric(fin_cf_data.values, errors='coerce') / 1e6
                    }).sort_values('Year', ascending=False)
                    yahoo_data['cash_flow_financing'] = fin_cf_df
                    print(f"   融資現金流數據: {len(fin_cf_df)} 年 (使用: {label})")
                    break
            
            # 現金及現金等價物
            cash_labels = ['Cash And Cash Equivalents', 'End Cash Position', 'Cash Equivalents', 'Cash Financial']
            for label in cash_labels:
                if label in balance_sheet.index:
                    cash_data = balance_sheet.loc[label].dropna()
                    cash_df = pd.DataFrame({
                        'Year': [date.year for date in cash_data.index],
                        'Cash and Cash Equivalents (M USD)': pd.to_numeric(cash_data.values, errors='coerce') / 1e6
                    }).sort_values('Year', ascending=False)
                    yahoo_data['cash_and_cash_equivalents'] = cash_df
                    print(f"   現金數據: {len(cash_df)} 年 (使用: {label})")
                    break
            
            # 計算流動比率
            if 'current_assets' in yahoo_data and 'current_liabilities' in yahoo_data:
                ca_df = yahoo_data['current_assets']
                cl_df = yahoo_data['current_liabilities']
                merged_df = pd.merge(ca_df, cl_df, on='Year', how='inner')
                if not merged_df.empty:
                    current_ratio_df = pd.DataFrame()
                    current_ratio_df['Year'] = merged_df['Year']
                    current_ratio_df['Current Ratio'] = (merged_df['Current Assets (M USD)'] / merged_df['Current Liabilities (M USD)']).round(4)
                    yahoo_data['current_ratio'] = current_ratio_df
                    print(f"   流動比率計算成功: {len(current_ratio_df)} 年")
            
            return yahoo_data
            
        except Exception as e:
            print(f"Yahoo Finance數據抓取失敗: {e}")
            return {}
    
    def merge_data_sources(self, yahoo_data):
        """處理Yahoo Finance數據"""
        print("處理數據源...")
        
        merged_data = {}
        current_year = datetime.now().year
        target_years = list(range(current_year - 9, current_year + 1))
        
        # 數據欄位映射
        field_mapping = {
            'revenue': 'revenue',
            'income': 'net_income',
            'cash_flow': 'operating_cash_flow',
            'equity': 'shareholders_equity',
            'total_assets': 'total_assets',
            'total_liabilities': 'total_liabilities',
            'long_term_debt': 'long_term_debt',
            'current_assets': 'current_assets',
            'current_liabilities': 'current_liabilities',
            'current_ratio': 'current_ratio',
            'free_cash_flow': 'free_cash_flow',
            'gross_profit': 'gross_profit',
            'operating_expenses': 'operating_expenses',
            'operating_income': 'operating_income',
            'income_before_tax': 'income_before_tax',
            'eps_basic': 'eps_basic',
            'outstanding_shares': 'outstanding_shares',
            'retained_earnings': 'retained_earnings_balance',
            'cash_flow_investing': 'cash_flow_investing',
            'cash_flow_financing': 'cash_flow_financing',
            'cash_and_cash_equivalents': 'cash_and_cash_equivalents'
        }
        
        for year in target_years:
            year_data = {}
            
            # 處理Yahoo Finance數據
            for yahoo_key, df in yahoo_data.items():
                if df is not None and not df.empty and 'Year' in df.columns:
                    year_row = df[df['Year'] == year]
                    if not year_row.empty:
                        value_col = [col for col in df.columns if col != 'Year'][0]
                        try:
                            value = float(year_row.iloc[0][value_col])
                            mapped_key = field_mapping.get(yahoo_key, yahoo_key)
                            year_data[mapped_key] = value
                        except (ValueError, TypeError, IndexError):
                            continue
            
            # 計算COGS（如果有收入和毛利潤）
            if 'revenue' in year_data and 'gross_profit' in year_data:
                year_data['cogs'] = year_data['revenue'] - year_data['gross_profit']
            
            merged_data[year] = year_data
        
        return merged_data
    
    def save_to_database(self, ticker, company_name, merged_data):
        """保存合併後的數據到資料庫"""
        if not self.db_connection or not self.db_connection.is_connected():
            print("資料庫未連接")
            return False
        
        try:
            cursor = self.db_connection.cursor()
            success_count = 0
            
            for year, data in merged_data.items():
                if not data:
                    continue
                
                # 計算數據品質分數
                total_fields = 23
                filled_fields = len([v for v in data.values() if v is not None])
                quality_score = min(100, (filled_fields / total_fields) * 100)
                
                if quality_score >= 80:
                    quality_flag = 'excellent'
                elif quality_score >= 60:
                    quality_flag = 'good'
                elif quality_score >= 40:
                    quality_flag = 'fair'
                else:
                    quality_flag = 'poor'
                
                # 準備插入語句（包含所有欄位）
                insert_query = """
                INSERT INTO filings (
                    ticker, company_name, filing_type, filing_year, created_at, 
                    data_source, data_quality_score, data_quality_flag, last_updated,
                    revenue, gross_profit, operating_expenses, operating_income, income_before_tax,
                    eps_basic, outstanding_shares, cogs, net_income, operating_cash_flow,
                    shareholders_equity, total_assets, total_liabilities, long_term_debt,
                    retained_earnings_balance, current_assets, current_liabilities, current_ratio,
                    free_cash_flow, cash_flow_investing, cash_flow_financing, cash_and_cash_equivalents
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON DUPLICATE KEY UPDATE
                    data_quality_score = VALUES(data_quality_score),
                    data_quality_flag = VALUES(data_quality_flag),
                    last_updated = VALUES(last_updated),
                    revenue = VALUES(revenue),
                    gross_profit = VALUES(gross_profit),
                    operating_expenses = VALUES(operating_expenses),
                    operating_income = VALUES(operating_income),
                    income_before_tax = VALUES(income_before_tax),
                    eps_basic = VALUES(eps_basic),
                    outstanding_shares = VALUES(outstanding_shares),
                    cogs = VALUES(cogs),
                    net_income = VALUES(net_income),
                    operating_cash_flow = VALUES(operating_cash_flow),
                    shareholders_equity = VALUES(shareholders_equity),
                    total_assets = VALUES(total_assets),
                    total_liabilities = VALUES(total_liabilities),
                    long_term_debt = VALUES(long_term_debt),
                    retained_earnings_balance = VALUES(retained_earnings_balance),
                    current_assets = VALUES(current_assets),
                    current_liabilities = VALUES(current_liabilities),
                    current_ratio = VALUES(current_ratio),
                    free_cash_flow = VALUES(free_cash_flow),
                    cash_flow_investing = VALUES(cash_flow_investing),
                    cash_flow_financing = VALUES(cash_flow_financing),
                    cash_and_cash_equivalents = VALUES(cash_and_cash_equivalents)
                """
                
                values = (
                    ticker.upper(), company_name, 'ANNUAL_FINANCIAL', year, datetime.now(),
                    'yahoo_finance_enhanced', quality_score, quality_flag, datetime.now(),
                    data.get('revenue'), data.get('gross_profit'), data.get('operating_expenses'),
                    data.get('operating_income'), data.get('income_before_tax'), data.get('eps_basic'),
                    data.get('outstanding_shares'), data.get('cogs'), data.get('net_income'), data.get('operating_cash_flow'),
                    data.get('shareholders_equity'), data.get('total_assets'), data.get('total_liabilities'),
                    data.get('long_term_debt'), data.get('retained_earnings_balance'), data.get('current_assets'),
                    data.get('current_liabilities'), data.get('current_ratio'), data.get('free_cash_flow'),
                    data.get('cash_flow_investing'), data.get('cash_flow_financing'), data.get('cash_and_cash_equivalents')
                )
                
                cursor.execute(insert_query, values)
                success_count += 1
                print(f"   {year}年數據保存成功 (品質分數: {quality_score:.1f}%)")
            
            self.db_connection.commit()
            print(f"總共保存了 {success_count} 年的數據")
            return True
            
        except Error as e:
            print(f"資料庫保存失敗: {e}")
            self.db_connection.rollback()
            return False
    
    def analyze_stock(self, ticker, company_name=None):
        """完整的股票分析流程"""
        if not company_name:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                company_name = info.get('longName') or info.get('shortName') or ticker.upper()
            except:
                company_name = ticker.upper()
        
        print(f"\n{'='*80}")
        print(f"改進版股票分析: {company_name} ({ticker.upper()})")
        print(f"{'='*80}")
        
        # 連接資料庫
        if not self.connect_database():
            print("WARNING: 資料庫連接失敗，將跳過資料庫保存")
            return None
        
        try:
            # 獲取數據
            yahoo_data = self.get_comprehensive_yahoo_data(ticker)
            
            # 處理數據
            merged_data = self.merge_data_sources(yahoo_data)
            
            # 保存到資料庫
            if merged_data:
                self.save_to_database(ticker, company_name, merged_data)
                print(f"\n✅ {ticker} 的數據分析和保存完成")
                return merged_data
            else:
                print(f"❌ {ticker} 的數據獲取失敗")
                return None
                
        finally:
            self.disconnect_database()

def main():
    """主程序"""
    if len(sys.argv) >= 2:
        ticker = sys.argv[1].upper()
        
        print(f"改進版股票分析器 - 分析 {ticker}")
        
        analyzer = ImprovedStockAnalyzer()
        result = analyzer.analyze_stock(ticker)
        
        if result:
            print(f"\n✅ {ticker} 分析完成")
        else:
            print(f"\n❌ {ticker} 分析失敗")
    else:
        print("用法: python improved_stock_analyzer.py <TICKER>")
        print("例如: python improved_stock_analyzer.py MSFT")

if __name__ == "__main__":
    main() 