#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dual source stock financial analysis tool
Extract data from macrotrends.net and Yahoo Finance and compare them
"""

import sys
import os

# 設置標準輸出編碼為UTF-8，避免Windows下的編碼問題
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

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

class DualSourceAnalyzer:
    def __init__(self, db_config=None):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # 資料庫配置 (基於 config.php)
        self.db_config = db_config or {
            'host': '13.114.174.139',
            'database': 'finbot_db',
            'user': 'myuser',
            'password': '123456789',
            'charset': 'utf8mb4'
        }
        
        self.db_connection = None
    
    def get_company_name_from_ticker(self, ticker):
        """get company name from ticker - 支持任何股票代號"""
        # 嘗試從 Yahoo Finance 獲取公司名稱
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)
            info = stock.info
            company_name = info.get('longName') or info.get('shortName') or ticker.upper()
            print(f"從 Yahoo Finance 獲取公司名稱: {ticker} -> {company_name}")
            return company_name
        except Exception as e:
            print(f"無法從 Yahoo Finance 獲取 {ticker} 的公司名稱，使用預設值: {e}")
            
        # 預設的常見公司名稱對應（作為備用）
        company_names = {
            'AAPL': 'Apple',
            'MSFT': 'Microsoft', 
            'GOOGL': 'Google',
            'AMZN': 'Amazon',
            'TSLA': 'Tesla',
            'META': 'Meta',
            'NVDA': 'NVIDIA',
            'NFLX': 'Netflix',
            'CRM': 'Salesforce',
            'ORCL': 'Oracle',
            'IBM': 'IBM'
        }
        
        return company_names.get(ticker.upper(), ticker.upper())
    
    # ============= 資料庫操作方法 =============
    
    def connect_database(self):
        """connect database"""
        try:
            self.db_connection = mysql.connector.connect(**self.db_config)
            if self.db_connection.is_connected():
                print("Database connected successfully")
                return True
        except Error as e:
            print(f"Database connection failed: {e}")
            return False
    
    def disconnect_database(self):
        """Disconnect database"""
        if self.db_connection and self.db_connection.is_connected():
            self.db_connection.close()
            print("Database connection closed")
    
    def calculate_data_quality(self, macrotrends_data, yahoo_data):
        """Calculate data quality score (improved version - supports Macrotrends four data types)"""
        score = 0
        
        # Basic data scoring (revenue and net income)
        revenue_count = 0
        if macrotrends_data.get('revenue') is not None: revenue_count += 1
        if yahoo_data.get('revenue') is not None: revenue_count += 1
        
        income_count = 0
        if macrotrends_data.get('income') is not None: income_count += 1
        if yahoo_data.get('income') is not None: income_count += 1
        
        # Operating cash flow calculation (including Macrotrends)
        cash_flow_count = 0
        if macrotrends_data.get('cash_flow') is not None: cash_flow_count += 1
        if yahoo_data.get('cash_flow') is not None: cash_flow_count += 1
        
        # Shareholder equity calculation (including Macrotrends)
        equity_count = 0
        if macrotrends_data.get('equity') is not None: equity_count += 1
        if yahoo_data.get('equity') is not None: equity_count += 1
        
        # Revenue score (max 30 points)
        if revenue_count == 2: score += 30  # Dual data source
        elif revenue_count == 1: score += 20  # Single data source
        
        # Net income score (max 30 points)
        if income_count == 2: score += 30  # Dual data source
        elif income_count == 1: score += 20  # Single data source
        
        # Operating cash flow score (max 20 points)
        if cash_flow_count == 2: score += 20  # Dual data source (Macrotrends + Yahoo)
        elif cash_flow_count == 1: score += 15  # Single data source
        
        # Shareholder equity score (max 20 points)
        if equity_count == 2: score += 20  # Dual data source (Macrotrends + Yahoo)
        elif equity_count == 1: score += 15  # Single data source
        
        # Ensure score does not exceed 100
        total_score = min(score, 100)
        
        # Rating criteria
        if total_score >= 80:
            return total_score, 'excellent'
        elif total_score >= 60:
            return total_score, 'good'
        elif total_score >= 40:
            return total_score, 'fair'
        else:
            return total_score, 'poor'
    
    def calculate_variance(self, value1, value2):
        """Calculate variance percentage between two values"""
        if value1 is None or value2 is None or value2 == 0:
            return None
        return abs((value1 - value2) / value2 * 100)
    
    def save_to_database(self, ticker, company_name, year_data_dict):
        """Batch save 10-year data to database"""
        if not self.db_connection or not self.db_connection.is_connected():
            print("Database not connected")
            return False
        
        try:
            cursor = self.db_connection.cursor()
            success_count = 0
            
            for year, data in year_data_dict.items():
                macrotrends_data = data.get('macrotrends', {})
                yahoo_data = data.get('yahoo', {})
                
                # 計算數據品質
                quality_score, quality_flag = self.calculate_data_quality(macrotrends_data, yahoo_data)
                
                # 準備數據
                macro_revenue = macrotrends_data.get('revenue')
                macro_income = macrotrends_data.get('income')
                macro_cash_flow = macrotrends_data.get('cash_flow')
                macro_equity = macrotrends_data.get('equity')
                yahoo_revenue = yahoo_data.get('revenue')
                yahoo_income = yahoo_data.get('income')
                yahoo_cash_flow = yahoo_data.get('cash_flow')
                yahoo_equity = yahoo_data.get('equity')
                
                # 新增核心財務指標
                macro_gross_profit = macrotrends_data.get('gross_profit')
                macro_operating_expenses = macrotrends_data.get('operating_expenses')
                macro_operating_income = macrotrends_data.get('operating_income')
                macro_income_before_tax = macrotrends_data.get('income_before_tax')
                macro_eps_basic = macrotrends_data.get('eps_basic')
                macro_outstanding_shares = macrotrends_data.get('outstanding_shares')
                macro_cogs = macrotrends_data.get('cogs')
                
                # 新增現金流指標（直接從organize_data_by_year處理好的數據中提取）
                macro_free_cash_flow = macrotrends_data.get('free_cash_flow')
                macro_cash_flow_investing = macrotrends_data.get('cash_flow_investing')
                macro_cash_flow_financing = macrotrends_data.get('cash_flow_financing')
                macro_cash_and_cash_equivalents = macrotrends_data.get('cash_and_cash_equivalents')
                
                # =============== 新增：资产负债表指标 ===============
                macro_total_assets = macrotrends_data.get('total_assets')
                macro_total_liabilities = macrotrends_data.get('total_liabilities')
                macro_long_term_debt = macrotrends_data.get('long_term_debt')
                macro_retained_earnings_balance = macrotrends_data.get('retained_earnings_balance')
                # 注意：Macrotrends 不提供流动资产和流动负债的单独页面
                
                yahoo_total_assets = yahoo_data.get('total_assets')
                yahoo_total_liabilities = yahoo_data.get('total_liabilities')
                yahoo_long_term_debt = yahoo_data.get('long_term_debt')
                yahoo_current_assets = yahoo_data.get('current_assets')
                yahoo_current_liabilities = yahoo_data.get('current_liabilities')
                yahoo_current_ratio = yahoo_data.get('current_ratio')
                
                # 計算差異百分比
                revenue_variance = self.calculate_variance(macro_revenue, yahoo_revenue)
                income_variance = self.calculate_variance(macro_income, yahoo_income)
                
                # 選擇最佳數據（營收和淨利優先Yahoo，現金流和權益優先Macrotrends）
                final_revenue = yahoo_revenue if yahoo_revenue is not None else macro_revenue
                final_income = yahoo_income if yahoo_income is not None else macro_income
                final_cash_flow = macro_cash_flow if macro_cash_flow is not None else yahoo_cash_flow
                final_equity = macro_equity if macro_equity is not None else yahoo_equity
                
                # =============== 新增：选择最佳数据（优先使用可用的数据源）===============
                final_total_assets = macro_total_assets if macro_total_assets is not None else yahoo_total_assets
                final_total_liabilities = macro_total_liabilities if macro_total_liabilities is not None else yahoo_total_liabilities
                final_long_term_debt = macro_long_term_debt if macro_long_term_debt is not None else yahoo_long_term_debt
                
                # 保留盈餘：優先使用 Yahoo Finance，Macrotrends 作為備用
                final_retained_earnings_balance = yahoo_data.get('retained_earnings_balance') if yahoo_data.get('retained_earnings_balance') is not None else macro_retained_earnings_balance
                
                # 流動資產和流動負債：使用 Yahoo Finance 數據（Macrotrends 沒有這些獨立頁面）
                final_current_assets = yahoo_current_assets
                final_current_liabilities = yahoo_current_liabilities
                
                # 计算流动比率：优先使用最终选择的数据源
                final_current_ratio = None
                if final_current_assets is not None and final_current_liabilities is not None and final_current_liabilities != 0:
                    final_current_ratio = round(final_current_assets / final_current_liabilities, 4)
                elif yahoo_current_ratio is not None:
                    final_current_ratio = yahoo_current_ratio  # 备用：使用Yahoo计算的比率
                
                # =============== 选择最佳现金流数据（優先使用可用的數據源）===============
                final_free_cash_flow = macro_free_cash_flow if macro_free_cash_flow is not None else yahoo_data.get('free_cash_flow')
                final_cash_flow_investing = macro_cash_flow_investing if macro_cash_flow_investing is not None else yahoo_data.get('cash_flow_investing')
                final_cash_flow_financing = macro_cash_flow_financing if macro_cash_flow_financing is not None else yahoo_data.get('cash_flow_financing')
                final_cash_and_cash_equivalents = macro_cash_and_cash_equivalents if macro_cash_and_cash_equivalents is not None else yahoo_data.get('cash_and_cash_equivalents')
                
                # 檢查是否有足夠的基礎數據才存入資料庫
                if final_revenue is None and final_income is None:
                    print(f" {year} data is not enough, skip storage")
                    continue
                
                # 更新SQL语句，添加新的资产负债表字段和现金流字段
                sql = """
                INSERT INTO filings (
                    ticker, company_name, filing_year, filing_type,
                    revenue, net_income,
                    data_source, data_quality_score, data_quality_flag,
                    gross_profit, operating_expenses, operating_income, income_before_tax,
                    eps_basic, outstanding_shares, cogs,
                    operating_cash_flow, shareholders_equity,
                    total_assets, total_liabilities, long_term_debt, retained_earnings_balance,
                    current_assets, current_liabilities, current_ratio,
                    free_cash_flow, cash_flow_investing, cash_flow_financing, cash_and_cash_equivalents
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s
                ) ON DUPLICATE KEY UPDATE
                    company_name = VALUES(company_name),
                    revenue = VALUES(revenue),
                    net_income = VALUES(net_income),
                    data_source = VALUES(data_source),
                    data_quality_score = VALUES(data_quality_score),
                    data_quality_flag = VALUES(data_quality_flag),
                    gross_profit = VALUES(gross_profit),
                    operating_expenses = VALUES(operating_expenses),
                    operating_income = VALUES(operating_income),
                    income_before_tax = VALUES(income_before_tax),
                    eps_basic = VALUES(eps_basic),
                    outstanding_shares = VALUES(outstanding_shares),
                    cogs = VALUES(cogs),
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
                    cash_and_cash_equivalents = VALUES(cash_and_cash_equivalents),
                    last_updated = NOW()
                """
                
                values = (
                    ticker, company_name, year, 'ANNUAL_FINANCIAL',
                    final_revenue, final_income,
                    'dual_source', quality_score, quality_flag,
                    macro_gross_profit, macro_operating_expenses, macro_operating_income,
                    macro_income_before_tax, macro_eps_basic, macro_outstanding_shares, macro_cogs,
                    final_cash_flow, final_equity,
                    final_total_assets, final_total_liabilities, final_long_term_debt, final_retained_earnings_balance,
                    final_current_assets, final_current_liabilities, final_current_ratio,
                    final_free_cash_flow, final_cash_flow_investing, final_cash_flow_financing, final_cash_and_cash_equivalents
                )
                
                cursor.execute(sql, values)
                success_count += 1
                
                # 顯示存入的數據詳情
                data_summary = []
                if final_revenue: data_summary.append(f"Revenue: {final_revenue:,.0f}M")
                if final_income: data_summary.append(f"Net Income: {final_income:,.0f}M")
                if final_cash_flow: data_summary.append(f"Cash Flow: {final_cash_flow:,.0f}M")
                if final_equity: data_summary.append(f"Equity: {final_equity:,.0f}M")
                if macro_gross_profit: data_summary.append(f"Gross Profit: {macro_gross_profit:,.0f}M")
                if macro_operating_income: data_summary.append(f"Operating Income: {macro_operating_income:,.0f}M")
                if macro_eps_basic: data_summary.append(f"EPS: ${macro_eps_basic:.2f}")
                # 新增：资产负债表指标显示
                if final_total_assets: data_summary.append(f"Total Assets: {final_total_assets:,.0f}M")
                if final_total_liabilities: data_summary.append(f"Total Liabilities: {final_total_liabilities:,.0f}M")
                if final_long_term_debt: data_summary.append(f"Long Term Debt: {final_long_term_debt:,.0f}M")
                if final_current_assets: data_summary.append(f"Current Assets: {final_current_assets:,.0f}M")
                if final_current_liabilities: data_summary.append(f"Current Liabilities: {final_current_liabilities:,.0f}M")
                if final_current_ratio: data_summary.append(f"Current Ratio: {final_current_ratio:.2f}")
                # 新增：现金流指标显示
                if final_free_cash_flow: data_summary.append(f"Free Cash Flow: {final_free_cash_flow:,.0f}M")
                if final_cash_flow_investing: data_summary.append(f"Investing Cash Flow: {final_cash_flow_investing:,.0f}M")
                if final_cash_flow_financing: data_summary.append(f"Financing Cash Flow: {final_cash_flow_financing:,.0f}M")
                if final_cash_and_cash_equivalents: data_summary.append(f"Cash and Cash Equivalents: {final_cash_and_cash_equivalents:,.0f}M")
                
                print(f" {year} data has been stored: {', '.join(data_summary)} (quality: {quality_flag})")
            
            self.db_connection.commit()
            print(f"\nSuccessfully stored {success_count} years of financial data to the database")
            return True
            
        except Error as e:
            print(f" Database operation failed: {e}")
            if self.db_connection:
                self.db_connection.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
    
    # ============= MACROTRENDS 數據抓取 =============
    
    def get_macrotrends_table(self, url, title_keyword):
        """fetch specified table data from macrotrends.net (improved version with retry mechanism)"""
        max_retries = 3
        base_delay = 2
        
        for attempt in range(max_retries):
            try:
                print(f"    Macrotrends: {url} (attempt {attempt + 1})")
                
                # 增加延遲以避免429錯誤
                if attempt > 0:
                    delay = base_delay * (2 ** attempt)  # 指數退避
                    print(f"    Waiting {delay} seconds before retry...")
                    time.sleep(delay)
                
                res = requests.get(url, headers=self.headers, timeout=15)
                res.raise_for_status()
                soup = BeautifulSoup(res.text, 'html.parser')

                # 使用與 test.py 相同的表格查找邏輯
                tables = soup.find_all("table", class_="historical_data_table")
                
                if not tables:
                    print(f"     historical_data_table not found")
                    continue
                    
                # 通常第一個表格就是我們要的主數據表
                table = tables[0]
                rows = table.find_all("tr")
                
                if len(rows) < 2:  # 至少要有標題行和一行數據
                    print(f"     table row is not enough")
                    continue
                
                # 手動解析表格數據（更可靠）
                data = []
                for row in rows[1:]:  # 跳過標題行
                    cols = row.find_all("td")
                    if len(cols) >= 2:
                        year_text = cols[0].text.strip()
                        value_text = cols[1].text.strip().replace("$", "").replace(",", "").replace("B", "")
                        
                        try:
                            # 提取年份
                            year_match = re.search(r'(\d{4})', year_text)
                            if year_match:
                                year = int(year_match.group(1))
                                value = float(value_text)
                                
                                # 只保留近15年的數據
                                if 2010 <= year <= 2024:
                                    data.append((year, value))
                        except (ValueError, TypeError):
                            continue
                
                if not data:
                    print(f"no valid data parsed")
                    continue
                
                # 轉換為 DataFrame
                df = pd.DataFrame(data, columns=["Year", title_keyword])
                df = df.sort_values('Year', ascending=False)  # 按年份降序排列
                
                print(f" Successfully parsed {len(df)} years of {title_keyword} data")
                return df
                
            except requests.exceptions.RequestException as e:
                if "429" in str(e):
                    print(f"     Rate limited (429), attempt {attempt + 1}/{max_retries}")
                    if attempt < max_retries - 1:
                        continue
                    else:
                        print(f"     Max retries reached, skipping {title_keyword}")
                        return None
                else:
                    print(f"     Macrotrends error: {e}")
                    if attempt < max_retries - 1:
                        continue
                    else:
                        return None
                        
        return None
    
    def get_macrotrends_data(self, ticker, company_name):
        """get financial data from macrotrends"""
        print("fetching data from Macrotrends...")
        
        # 為不同股票使用正確的公司名稱 slug
        company_name_slug = self.get_company_slug_for_macrotrends(ticker, company_name)
        print(f"Using company slug: {company_name_slug} for {ticker}")
        
        macrotrends_data = {}

        # 核心財務指標（修正版 - 基於 test.py 的成功經驗）
        print("fetching core financial metrics...")
        metrics = {
            "Revenue": "revenue",
            "Gross Profit": "gross-profit",
            "Operating Expenses": "operating-expenses",
            "Operating Income": "operating-income",
            "Income Before Taxes": "pre-tax-income",  # 修正：使用 test.py 中成功的 URL
            "Net Income": "net-income",
            "EPS Basic": "eps-earnings-per-share-diluted",   # 修正：使用 test.py 中成功的 URL
            "Outstanding Shares": "shares-outstanding"
        }

        for metric_name, metric_url in metrics.items():
            print(f"     fetching {metric_name}...")
            url = f"https://www.macrotrends.net/stocks/charts/{ticker}/{company_name_slug}/{metric_url}"
            df = self.get_macrotrends_table(url, metric_name)
            if df is not None:
                # 將數據標準化為百萬美元單位
                if metric_name == "EPS Basic":
                    # EPS 保持原單位（美元/股）
                    df[f"{metric_name} (USD)"] = df[metric_name]
                elif metric_name == "Outstanding Shares":
                    # 股數轉換為百萬股
                    df[f"{metric_name} (M)"] = df[metric_name]
                else:
                    # 其他財務數據轉換為百萬美元
                    df[f"{metric_name} (M USD)"] = df[metric_name]
                
                # 根據指標類型存儲到對應的鍵中
                if metric_name == "Revenue":
                    macrotrends_data['revenue'] = df[['Year', f"{metric_name} (M USD)"]]
                elif metric_name == "Net Income":
                    macrotrends_data['income'] = df[['Year', f"{metric_name} (M USD)"]]
                elif metric_name == "Gross Profit":
                    macrotrends_data['gross_profit'] = df[['Year', f"{metric_name} (M USD)"]]
                elif metric_name == "Operating Expenses":
                    macrotrends_data['operating_expenses'] = df[['Year', f"{metric_name} (M USD)"]]
                elif metric_name == "Operating Income":
                    macrotrends_data['operating_income'] = df[['Year', f"{metric_name} (M USD)"]]
                elif metric_name == "Income Before Taxes":
                    macrotrends_data['income_before_tax'] = df[['Year', f"{metric_name} (M USD)"]]
                elif metric_name == "EPS Basic":
                    macrotrends_data['eps_basic'] = df[['Year', f"{metric_name} (USD)"]]
                elif metric_name == "Outstanding Shares":
                    macrotrends_data['outstanding_shares'] = df[['Year', f"{metric_name} (M)"]]
                
                print(f"   {metric_name} data fetched successfully")
            else:
                print(f"       {metric_name} data fetched failed")
            
            time.sleep(1)  # 防止請求過快

        # 計算銷貨成本 (COGS)
        if 'revenue' in macrotrends_data and 'gross_profit' in macrotrends_data:
            revenue_df = macrotrends_data['revenue']
            gross_profit_df = macrotrends_data['gross_profit']
            
            if len(revenue_df.columns) >= 2 and len(gross_profit_df.columns) >= 2:
                revenue_col = revenue_df.columns[1]  # 第二列是數值
                gross_profit_col = gross_profit_df.columns[1]  # 第二列是數值
                
                # 合併數據並計算 COGS
                merged_df = pd.merge(revenue_df, gross_profit_df, on='Year', how='inner')
                if not merged_df.empty:
                    cogs_df = pd.DataFrame()
                    cogs_df['Year'] = merged_df['Year']
                    cogs_df['COGS (M USD)'] = merged_df[revenue_col] - merged_df[gross_profit_col]
                    macrotrends_data['cogs'] = cogs_df
                    print("COGS calculation successful")
        
        # 自由現金流 - 使用新的抓取方法
        print("fetching free cash flow data...")
        cash_flow_df = self.fetch_free_cash_flow_macrotrends(ticker, company_name_slug)
        if cash_flow_df is not None:
            macrotrends_data['cash_flow'] = cash_flow_df
            print("free cash flow data fetched successfully")
        else:
            print("free cash flow data fetched failed")
        
        time.sleep(1)
        
        # 股東權益 - 使用改進的 JavaScript 解析方法（基於成功的 test_simple_equity.py）
        print("fetching shareholder equity data...")
        equity_df = self.get_shareholder_equity(ticker, company_name_slug)
        if equity_df is not None:
            macrotrends_data['equity'] = equity_df
            print("shareholder equity data fetched successfully")
        else:
            print("shareholder equity data fetched failed")
        
        # =============== 新增：资产负债表指标（基于 final_scraper.py 的成功经验）===============
        print("fetching balance sheet metrics...")
        balance_sheet_metrics = {
            "Total Assets": "total-assets",
            "Total Liabilities": "total-liabilities", 
            "Long Term Debt": "long-term-debt",
            "Retained Earnings Balance": "accumulated-other-comprehensive-income"  # 使用final_scraper.py中成功的URL
            # 注意：Macrotrends 没有单独的 current-assets 和 current-liabilities 页面
            # 这些数据只能从 Yahoo Finance 获取（2021年后有数据）
            # 历史数据缺失是正常现象，因为数据源限制
        }

        for metric_name, metric_url in balance_sheet_metrics.items():
            print(f"     fetching {metric_name}...")
            url = f"https://www.macrotrends.net/stocks/charts/{ticker}/{company_name_slug}/{metric_url}"
            df = self.get_macrotrends_table(url, metric_name)
            if df is not None:
                # 將數據標準化為百萬美元單位
                df[f"{metric_name} (M USD)"] = df[metric_name]
                
                # 根據指標類型存儲到對應的鍵中
                if metric_name == "Total Assets":
                    macrotrends_data['total_assets'] = df[['Year', f"{metric_name} (M USD)"]]
                elif metric_name == "Total Liabilities":
                    macrotrends_data['total_liabilities'] = df[['Year', f"{metric_name} (M USD)"]]
                elif metric_name == "Long Term Debt":
                    macrotrends_data['long_term_debt'] = df[['Year', f"{metric_name} (M USD)"]]
                elif metric_name == "Retained Earnings Balance":
                    macrotrends_data['retained_earnings_balance'] = df[['Year', f"{metric_name} (M USD)"]]
                
                print(f"   {metric_name} data fetched successfully")
            else:
                print(f"       {metric_name} data fetched failed")
            
            time.sleep(1)  # 防止請求過快
        
        print("balance sheet metrics fetched successfully")
        
        # =============== 新增：现金流指标（基于 test.py 的成功经验）===============
        print("fetching cash flow metrics...")
        cash_flow_metrics = {
            "Free Cash Flow": "free-cash-flow",
            "Cash Flow from Investing": "cash-flow-from-investing-activities", 
            "Cash Flow from Financing": "cash-flow-from-financial-activities",
            "Cash and Cash Equivalents": "cash-on-hand"
        }

        for metric_name, metric_url in cash_flow_metrics.items():
            print(f"     fetching {metric_name}...")
            # 使用 test.py 中成功的 URL 格式：使用統一的 company_name_slug
            df = self.fetch_macrotrends_table_simple(ticker, company_name_slug, metric_url, metric_name)
            if df is not None:
                # 根據指標類型存儲到對應的鍵中
                if metric_name == "Free Cash Flow":
                    macrotrends_data['free_cash_flow'] = df
                elif metric_name == "Cash Flow from Investing":
                    macrotrends_data['cash_flow_investing'] = df
                elif metric_name == "Cash Flow from Financing":
                    macrotrends_data['cash_flow_financing'] = df
                elif metric_name == "Cash and Cash Equivalents":
                    macrotrends_data['cash_and_cash_equivalents'] = df
                
                print(f"   {metric_name} data fetched successfully")
            else:
                print(f"       {metric_name} data fetched failed")
            
            time.sleep(1)  # 防止請求過快
        
        print("cash flow metrics fetched successfully")
        # ==================================================================================
        
        # =============== 注意：Macrotrends 沒有獨立的流動資產/流動負債頁面 ===============
        # 流動資產和流動負債數據將由 Yahoo Finance 提供
        print("balance sheet items: using Yahoo Finance for current assets/liabilities")
        # ==================================================================================
        
        return macrotrends_data
    
    def get_company_slug_for_macrotrends(self, ticker, company_name):
        """為不同股票獲取正確的 Macrotrends company slug"""
        # 已知的常見股票 slug 對應表
        slug_mapping = {
            'AAPL': 'apple',
            'GOOGL': 'alphabet', 
            'GOOG': 'alphabet',
            'TSLA': 'tesla',
            'MSFT': 'microsoft',
            'AMZN': 'amazon',
            'META': 'meta-platforms',
            'NVDA': 'nvidia',
            'NFLX': 'netflix',
            'CRM': 'salesforce',
            'ORCL': 'oracle',
            'IBM': 'ibm',
            'AMD': 'amd',
            'INTC': 'intel',
            'PYPL': 'paypal',
            'DIS': 'disney',
            'BA': 'boeing',
            'JPM': 'jpmorgan-chase',
            'V': 'visa',
            'WMT': 'walmart',
            'JNJ': 'johnson-johnson',
            'PG': 'procter-gamble',
            'KO': 'coca-cola',
            'PFE': 'pfizer',
            'XOM': 'exxon-mobil',
            'CVX': 'chevron',
            'HD': 'home-depot',
            'VZ': 'verizon',
            'T': 'at-t',
            'CSCO': 'cisco',
            'ADBE': 'adobe',
            'CRM': 'salesforce',
            'NKE': 'nike',
            'MRK': 'merck',
            'UNH': 'unitedhealth-group',
            'LLY': 'eli-lilly',
            'ABBV': 'abbvie',
            'TMO': 'thermo-fisher-scientific',
            'DHR': 'danaher',
            'PEP': 'pepsico',
            'COST': 'costco',
            'AVGO': 'broadcom',
            'ACN': 'accenture',
            'TXN': 'texas-instruments',
            'LIN': 'linde',
            'MDT': 'medtronic',
            'PM': 'philip-morris',
            'QCOM': 'qualcomm',
            'HON': 'honeywell',
            'UPS': 'ups',
            'LOW': 'lowes',
            'SPGI': 's-p-global',
            'GS': 'goldman-sachs',
            'BLK': 'blackrock',
            'C': 'citigroup',
            'MS': 'morgan-stanley',
            'AXP': 'american-express',
            'CAT': 'caterpillar',
            'DE': 'deere',
            'MMM': '3m',
            'GE': 'general-electric',
            'F': 'ford-motor',
            'GM': 'general-motors'
        }
        
        # 先檢查已知的對應表
        if ticker.upper() in slug_mapping:
            return slug_mapping[ticker.upper()]
        
        # 如果沒有已知的對應，嘗試根據公司名稱生成 slug
        if company_name:
            # 將公司名稱轉換為 slug 格式
            import re
            slug = company_name.lower()
            slug = re.sub(r'[^a-z0-9\s-]', '', slug)  # 移除特殊字符
            slug = re.sub(r'\s+', '-', slug)  # 將空格轉換為連字符
            slug = re.sub(r'-+', '-', slug)  # 合併多個連字符
            slug = slug.strip('-')  # 移除首尾的連字符
            
            # 移除常見的公司後綴
            suffixes_to_remove = [
                'inc', 'corp', 'corporation', 'company', 'co', 'ltd', 'limited',
                'llc', 'plc', 'technologies', 'technology', 'systems', 'group'
            ]
            for suffix in suffixes_to_remove:
                if slug.endswith('-' + suffix):
                    slug = slug[:-len('-' + suffix)]
            
            return slug
        
        # 最後的備用方案：使用小寫的股票代號
        return ticker.lower()
    
    def fetch_macrotrends_table_simple(self, ticker, company_slug, page_slug, metric_name, max_years=10):
        """simplified data fetching method using the correct company slug (enhanced retry for cash flow metrics)"""
        url = f"https://www.macrotrends.net/stocks/charts/{ticker}/{company_slug}/{page_slug}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # 對現金流指標使用更強的重試機制
        cash_flow_metrics = ['free-cash-flow', 'cash-flow-from-investing-activities', 
                           'cash-flow-from-financial-activities', 'cash-on-hand']
        is_cash_flow_metric = page_slug in cash_flow_metrics
        
        max_retries = 5 if is_cash_flow_metric else 3  # 現金流指標用更多重試
        base_delay = 3 if is_cash_flow_metric else 2   # 現金流指標用更長延遲
        
        for attempt in range(max_retries):
            try:
                print(f"        fetching from: {url} (attempt {attempt + 1}/{max_retries})")
                
                # 增加延遲以避免429錯誤
                if attempt > 0:
                    delay = base_delay * (2 ** attempt)  # 指數退避
                    print(f"        waiting {delay} seconds before retry...")
                    time.sleep(delay)
                
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()  # 檢查 HTTP 錯誤
                soup = BeautifulSoup(response.text, "html.parser")
                
                table = soup.find("table", class_="historical_data_table")
                if not table:
                    print(f"        historical_data_table not found: {url}")
                    if attempt < max_retries - 1:
                        continue
                    else:
                        return None
                        
                rows = table.find_all("tr")
                if len(rows) < 2:
                    print(f"        insufficient data rows: {url}")
                    if attempt < max_retries - 1:
                        continue
                    else:
                        return None
                
                data = {}
                for row in rows[1:]:  # 跳過標題行
                    cols = row.find_all("td")
                    if len(cols) >= 2:
                        year_text = cols[0].text.strip()
                        value_text = cols[1].text.strip().replace("$", "").replace(",", "").replace("B", "")
                        try:
                            # 提取年份（處理可能的日期格式）
                            if year_text.isdigit():
                                year = int(year_text)
                            else:
                                # 嘗試從日期中提取年份
                                import re
                                year_match = re.search(r'(\d{4})', year_text)
                                if year_match:
                                    year = int(year_match.group(1))
                                else:
                                    continue
                            
                            value = float(value_text)
                            
                            # 轉換單位：十億 → 百萬
                            if 'B' in cols[1].text or value < 1000:  # 如果是十億單位或數值較小
                                value = value * 1000  # 十億 → 百萬
                            
                            # 只保留合理年份範圍的數據
                            if 2005 <= year <= 2025:
                                data[year] = value
                                print(f"        parsed: {year} = ${value:,.0f}M")
                        except (ValueError, TypeError) as e:
                            print(f"        skipping invalid data: {year_text} = {value_text} ({e})")
                            continue
                
                if not data:
                    print(f"        no valid data parsed: {url}")
                    if attempt < max_retries - 1:
                        continue
                    else:
                        return None
                        
                # 僅保留最近 N 年資料，轉換為 DataFrame 格式
                recent_data = {year: data[year] for year in sorted(data.keys(), reverse=True)[:max_years]}
                
                # 轉換為 DataFrame 格式（與其他方法保持一致）
                df_data = []
                for year, value in recent_data.items():
                    df_data.append([year, value])
                
                df = pd.DataFrame(df_data, columns=["Year", f"{metric_name} (M USD)"])
                print(f"        [SUCCESS] successfully parsed {len(df)} years of {metric_name} data")
                return df
                
            except requests.exceptions.RequestException as e:
                if "429" in str(e):
                    print(f"        rate limited (429), attempt {attempt + 1}/{max_retries}")
                    if attempt < max_retries - 1:
                        continue
                    else:
                        print(f"        [ERROR] max retries reached for {metric_name}, will try alternative sources")
                        return None
                else:
                    print(f"        error fetching {metric_name}: {e}")
                    if attempt < max_retries - 1:
                        continue
                    else:
                        return None
                        
        return None
    
    def fetch_macrotrends_balance_sheet_item(self, ticker, company_slug, page_slug, metric_name, max_years=15):
        """fetch balance sheet items from Macrotrends (current assets, current liabilities, etc.)"""
        url = f"https://www.macrotrends.net/stocks/charts/{ticker}/{company_slug}/{page_slug}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        try:
            print(f"        fetching from: {url}")
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 查找歷史數據表格
            table = soup.find("table", class_="historical_data_table")
            if not table:
                print(f"        historical_data_table not found for {metric_name}")
                return None
                
            rows = table.find_all("tr")
            if len(rows) < 2:
                print(f"        insufficient data rows for {metric_name}")
                return None
            
            data = []
            for row in rows[1:]:  # 跳過標題行
                cols = row.find_all("td")
                if len(cols) >= 2:
                    year_text = cols[0].text.strip()
                    value_text = cols[1].text.strip().replace("$", "").replace(",", "").replace("B", "")
                    
                    try:
                        # 提取年份
                        year_match = re.search(r'(\d{4})', year_text)
                        if year_match:
                            year = int(year_match.group(1))
                            value = float(value_text)
                            
                            # 轉換單位：如果是億美元，轉換為百萬美元
                            if 'B' in cols[1].text or value > 1000:  # 可能是億美元單位
                                value = value * 1000  # 億 → 百萬
                            
                            # 只保留合理年份範圍的數據
                            if 2005 <= year <= 2025:
                                data.append({
                                    "Year": year,
                                    f"{metric_name} (M USD)": round(value, 0)
                                })
                                print(f"        parsed: {year} = ${value:,.0f}M")
                    except (ValueError, TypeError) as e:
                        print(f"        skipping invalid data: {year_text} = {value_text} ({e})")
                        continue
            
            if not data:
                print(f"        no valid data parsed for {metric_name}")
                return None
            
            # 轉換為 DataFrame 並按年份降序排列
            df = pd.DataFrame(data)
            df = df.sort_values('Year', ascending=False).head(max_years)
            
            print(f"        successfully parsed {len(df)} years of {metric_name} data")
            return df
            
        except Exception as e:
            print(f"        error fetching {metric_name} from Macrotrends: {e}")
            return None

    def fetch_free_cash_flow_macrotrends(self, ticker, company_slug):
        """fetch free cash flow data from Macrotrends (recommended method)"""
        try:
            url = f"https://www.macrotrends.net/stocks/charts/{ticker}/{company_slug}/free-cash-flow"
            print(f"    Macrotrends Free Cash Flow: {url}")
            
            res = requests.get(url, headers=self.headers, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # 使用與新方法一致的表格查找邏輯
            tables = soup.find_all("table", class_="historical_data_table")
            
            if not tables:
                print("      historical_data_table not found")
                return None
                
            # 通常第一個表格就是我們要的主數據表
            table = tables[0]
            rows = table.find_all("tr")
            
            if len(rows) < 2:  # 至少要有標題行和一行數據
                print("      table row is not enough")
                return None
            
            # 手動解析表格數據（更可靠）
            data = []
            for row in rows[1:]:  # 跳過標題行
                cols = row.find_all("td")
                if len(cols) >= 2:
                    year_text = cols[0].text.strip()
                    value_text = cols[1].text.strip().replace("$", "").replace(",", "").replace("B", "")
                    
                    try:
                        # 提取年份
                        year_match = re.search(r'(\d{4})', year_text)
                        if year_match:
                            year = int(year_match.group(1))
                            value = float(value_text)
                            
                            # 只保留近15年的數據
                            if 2010 <= year <= 2024:
                                data.append((year, value))
                    except (ValueError, TypeError):
                        continue
            
            if not data:
                print("      no valid cash flow data parsed")
                return None
            
            # 轉換為 DataFrame
            df = pd.DataFrame(data, columns=["Year", "Operating Cash Flow (M USD)"])
            df = df.sort_values('Year', ascending=False)  # 按年份降序排列
            
            print(f" successfully parsed {len(df)} years of cash flow data")
            return df
            
        except Exception as e:
            print(f"     Macrotrends free cash flow error: {e}")
            return None
    
    def get_shareholder_equity(self, ticker, company_slug):
        """fetch shareholder equity data from Macrotrends (based on the actual success logic of test_simple_equity.py)"""
        try:
            # 使用與 test_simple_equity.py 相同的 URL 格式
            url = f"https://www.macrotrends.net/stocks/charts/{ticker}/{company_slug}/total-share-holder-equity"
            print(f"    Macrotrends Shareholder Equity: {url}")
            
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            print(f" webpage fetched successfully, size: {len(response.text):,} characters")
            
            # 使用與 test_simple_equity.py 相同的 BeautifulSoup 解析方法
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(response.text, "html.parser")
            tables = soup.find_all("table", class_="historical_data_table")
            
            if not tables:
                print("      no historical_data_table found")
                return None
            
            print(f" found {len(tables)} tables")
            
            # 取得主資料表（通常是第一個）
            table = tables[0]
            rows = table.find_all("tr")
            
            print(f"     table contains {len(rows)} rows of data")
            
            data = []
            for i, row in enumerate(rows[1:]):  # 跳過標題行
                cols = row.find_all("td")
                if len(cols) >= 2:
                    year_text = cols[0].text.strip()
                    equity_text = cols[1].text.strip().replace("$", "").replace(",", "")
                    
                    try:
                        year = int(year_text)
                        equity_value = float(equity_text)
                        
                        # 只保留近15年的數據
                        if 2010 <= year <= 2024:
                            data.append({
                                "Year": year,
                                "Shareholders Equity (M USD)": equity_value  # MacroTrends 已經是百萬美元單位
                            })
                            print(f"      parsed: {year} year = ${equity_value:,.0f}M")
                    except (ValueError, TypeError) as e:
                        print(f"      skipping invalid data: {year_text} = {equity_text} ({e})")
                        continue
            
            if not data:
                print("      no valid shareholder equity data parsed")
                return None
            
            # 轉換為 DataFrame
            df = pd.DataFrame(data)
            df = df.sort_values('Year', ascending=False)  # 按年份降序排列
            
            print(f" successfully parsed {len(df)} years of shareholder equity data")
            print(f"     year range: {df['Year'].min()} - {df['Year'].max()}")
            
            # 顯示最近5年的數據預覽
            recent_years = df.head(5)
            print("     recent data preview:")
            for _, row in recent_years.iterrows():
                print(f"      {int(row['Year'])}: ${row['Shareholders Equity (M USD)']:,.0f}M")
            
            return df
            
        except Exception as e:
            print(f"     Macrotrends shareholder equity error: {e}")
            return None
    
    # ============= YAHOO FINANCE 數據抓取 =============
    
    def get_yahoo_finance_data(self, ticker):
        """get financial data from Yahoo Finance (enhanced version with missing metrics)"""
        print("fetching data from Yahoo Finance...")
        
        try:
            stock = yf.Ticker(ticker)
            
            # 獲取財務報表
            financials = stock.financials
            balance_sheet = stock.balance_sheet
            cash_flow = stock.cashflow
            
            yahoo_data = {}
            
            # 營收 (Total Revenue)
            print("processing revenue data...")
            if 'Total Revenue' in financials.index:
                revenue_data = financials.loc['Total Revenue'].dropna()
                revenue_df = pd.DataFrame({
                    'Year': [date.year for date in revenue_data.index],
                    'Revenue (M USD)': pd.to_numeric(revenue_data.values, errors='coerce') / 1e6
                }).sort_values('Year', ascending=False)
                revenue_df['Revenue (M USD)'] = revenue_df['Revenue (M USD)'].round(0)
                yahoo_data['revenue'] = revenue_df
                print("revenue data fetched successfully")
            else:
                print("revenue data not available")
            
            # 淨利 (Net Income)
            print("processing net income data...")
            if 'Net Income' in financials.index:
                income_data = financials.loc['Net Income'].dropna()
                income_df = pd.DataFrame({
                    'Year': [date.year for date in income_data.index],
                    'Net Income (M USD)': pd.to_numeric(income_data.values, errors='coerce') / 1e6
                }).sort_values('Year', ascending=False)
                income_df['Net Income (M USD)'] = income_df['Net Income (M USD)'].round(0)
                yahoo_data['income'] = income_df
                print("net income data fetched successfully")
            else:
                print("net income data not available")
            
            # 營運現金流 (Operating Cash Flow)
            print("processing operating cash flow data...")
            if 'Operating Cash Flow' in cash_flow.index:
                cf_data = cash_flow.loc['Operating Cash Flow'].dropna()
                cf_df = pd.DataFrame({
                    'Year': [date.year for date in cf_data.index],
                    'Operating Cash Flow (M USD)': pd.to_numeric(cf_data.values, errors='coerce') / 1e6
                }).sort_values('Year', ascending=False)
                cf_df['Operating Cash Flow (M USD)'] = cf_df['Operating Cash Flow (M USD)'].round(0)
                yahoo_data['cash_flow'] = cf_df
                print("operating cash flow data fetched successfully")
            else:
                print("operating cash flow data not available")
            
            # =============== 新增：缺失的現金流指標 ===============
            print("processing additional cash flow metrics...")
            
            # 自由現金流 (Free Cash Flow)
            if 'Free Cash Flow' in cash_flow.index:
                fcf_data = cash_flow.loc['Free Cash Flow'].dropna()
                fcf_df = pd.DataFrame({
                    'Year': [date.year for date in fcf_data.index],
                    'Free Cash Flow (M USD)': pd.to_numeric(fcf_data.values, errors='coerce') / 1e6
                }).sort_values('Year', ascending=False)
                fcf_df['Free Cash Flow (M USD)'] = fcf_df['Free Cash Flow (M USD)'].round(0)
                yahoo_data['free_cash_flow'] = fcf_df
                print("free cash flow data fetched successfully")
            else:
                print("free cash flow data not available")
            
            # 投資現金流 (Investing Cash Flow)
            investing_labels = ['Cash Flow from Investing', 'Cash Flow From Investing Activities']
            for label in investing_labels:
                if label in cash_flow.index:
                    icf_data = cash_flow.loc[label].dropna()
                    icf_df = pd.DataFrame({
                        'Year': [date.year for date in icf_data.index],
                        'Cash Flow from Investing (M USD)': pd.to_numeric(icf_data.values, errors='coerce') / 1e6
                    }).sort_values('Year', ascending=False)
                    icf_df['Cash Flow from Investing (M USD)'] = icf_df['Cash Flow from Investing (M USD)'].round(0)
                    yahoo_data['cash_flow_investing'] = icf_df
                    print(f"investing cash flow data fetched successfully (using: {label})")
                    break
            else:
                print("investing cash flow data not available")
            
            # 融資現金流 (Financing Cash Flow)
            financing_labels = ['Cash Flow from Financing', 'Cash Flow From Financial Activities', 'Cash Flow From Financing Activities']
            for label in financing_labels:
                if label in cash_flow.index:
                    fcf_data = cash_flow.loc[label].dropna()
                    fcf_df = pd.DataFrame({
                        'Year': [date.year for date in fcf_data.index],
                        'Cash Flow from Financing (M USD)': pd.to_numeric(fcf_data.values, errors='coerce') / 1e6
                    }).sort_values('Year', ascending=False)
                    fcf_df['Cash Flow from Financing (M USD)'] = fcf_df['Cash Flow from Financing (M USD)'].round(0)
                    yahoo_data['cash_flow_financing'] = fcf_df
                    print(f"financing cash flow data fetched successfully (using: {label})")
                    break
            else:
                print("financing cash flow data not available")
            
            # 現金及約當現金 (Cash and Cash Equivalents)
            cash_labels = ['Cash', 'Cash And Cash Equivalents', 'Cash Cash Equivalents And Short Term Investments']
            for label in cash_labels:
                if label in balance_sheet.index:
                    cash_data = balance_sheet.loc[label].dropna()
                    cash_df = pd.DataFrame({
                        'Year': [date.year for date in cash_data.index],
                        'Cash and Cash Equivalents (M USD)': pd.to_numeric(cash_data.values, errors='coerce') / 1e6
                    }).sort_values('Year', ascending=False)
                    cash_df['Cash and Cash Equivalents (M USD)'] = cash_df['Cash and Cash Equivalents (M USD)'].round(0)
                    yahoo_data['cash_and_cash_equivalents'] = cash_df
                    print(f"cash and cash equivalents data fetched successfully (using: {label})")
                    break
            else:
                print("cash and cash equivalents data not available")
            
            # 股東權益 (Stockholders' Equity)
            print("processing shareholder equity data...")
            equity_labels = ['Stockholders Equity', 'Total Stockholder Equity', 'Shareholders Equity']
            equity_found = False
            
            for label in equity_labels:
                if label in balance_sheet.index:
                    equity_data = balance_sheet.loc[label].dropna()
                    equity_df = pd.DataFrame({
                        'Year': [date.year for date in equity_data.index],
                        'Shareholders Equity (M USD)': pd.to_numeric(equity_data.values, errors='coerce') / 1e6
                    }).sort_values('Year', ascending=False)
                    equity_df['Shareholders Equity (M USD)'] = equity_df['Shareholders Equity (M USD)'].round(0)
                    yahoo_data['equity'] = equity_df
                    print(f"shareholder equity data fetched successfully (using: {label})")
                    equity_found = True
                    break
            
            if not equity_found:
                print("shareholder equity data not available")
            
            # =============== 擴展：資產負債表指標 ===============
            print("processing enhanced balance sheet metrics...")
            
            # 总资产 (Total Assets)
            if 'Total Assets' in balance_sheet.index:
                total_assets_data = balance_sheet.loc['Total Assets'].dropna()
                assets_df = pd.DataFrame({
                    'Year': [date.year for date in total_assets_data.index],
                    'Total Assets (M USD)': pd.to_numeric(total_assets_data.values, errors='coerce') / 1e6
                }).sort_values('Year', ascending=False)
                assets_df['Total Assets (M USD)'] = assets_df['Total Assets (M USD)'].round(0)
                yahoo_data['total_assets'] = assets_df
                print("total assets data fetched successfully")
            else:
                print("total assets data not available")
            
            # 总负债 (Total Liabilities) - 擴展搜索標籤
            total_liab_labels = ['Total Liab', 'Total Liabilities', 'Total Liabilities Net Minority Interest']
            liab_found = False
            for label in total_liab_labels:
                if label in balance_sheet.index:
                    total_liab_data = balance_sheet.loc[label].dropna()
                    liab_df = pd.DataFrame({
                        'Year': [date.year for date in total_liab_data.index],
                        'Total Liabilities (M USD)': pd.to_numeric(total_liab_data.values, errors='coerce') / 1e6
                    }).sort_values('Year', ascending=False)
                    liab_df['Total Liabilities (M USD)'] = liab_df['Total Liabilities (M USD)'].round(0)
                    yahoo_data['total_liabilities'] = liab_df
                    print(f"total liabilities data fetched successfully (using: {label})")
                    liab_found = True
                    break
            
            if not liab_found:
                print("total liabilities data not available")
                # 嘗試通過計算獲得：總資產 - 股東權益 = 總負債
                if 'total_assets' in yahoo_data and 'equity' in yahoo_data:
                    assets_df = yahoo_data['total_assets']
                    equity_df = yahoo_data['equity']
                    
                    # 合併數據計算總負債
                    merged_df = pd.merge(
                        assets_df[['Year', 'Total Assets (M USD)']],
                        equity_df[['Year', 'Shareholders Equity (M USD)']],
                        on='Year',
                        how='inner'
                    )
                    
                    if not merged_df.empty:
                        calculated_liab_df = pd.DataFrame()
                        calculated_liab_df['Year'] = merged_df['Year']
                        calculated_liab_df['Total Liabilities (M USD)'] = (
                            merged_df['Total Assets (M USD)'] - merged_df['Shareholders Equity (M USD)']
                        ).round(0)
                        yahoo_data['total_liabilities'] = calculated_liab_df
                        print(f"total liabilities calculated successfully: {len(calculated_liab_df)} years")
            
            # 长期负债 (Long Term Debt)
            if 'Long Term Debt' in balance_sheet.index:
                long_debt_data = balance_sheet.loc['Long Term Debt'].dropna()
                long_debt_df = pd.DataFrame({
                    'Year': [date.year for date in long_debt_data.index],
                    'Long Term Debt (M USD)': pd.to_numeric(long_debt_data.values, errors='coerce') / 1e6
                }).sort_values('Year', ascending=False)
                long_debt_df['Long Term Debt (M USD)'] = long_debt_df['Long Term Debt (M USD)'].round(0)
                yahoo_data['long_term_debt'] = long_debt_df
                print("long term debt data fetched successfully")
            else:
                print("long term debt data not available")
            
            # 保留盈餘 (Retained Earnings) - 擴展搜索標籤
            retained_earnings_labels = ['Retained Earnings', 'Retained Earnings Accumulated Deficit', 'Accumulated Deficit']
            re_found = False
            for label in retained_earnings_labels:
                if label in balance_sheet.index:
                    re_data = balance_sheet.loc[label].dropna()
                    re_df = pd.DataFrame({
                        'Year': [date.year for date in re_data.index],
                        'Retained Earnings (M USD)': pd.to_numeric(re_data.values, errors='coerce') / 1e6
                    }).sort_values('Year', ascending=False)
                    re_df['Retained Earnings (M USD)'] = re_df['Retained Earnings (M USD)'].round(0)
                    yahoo_data['retained_earnings_balance'] = re_df
                    print(f"retained earnings data fetched successfully (using: {label})")
                    re_found = True
                    break
            
            if not re_found:
                print("retained earnings data not available")
            
            # 流动资产 (Current Assets)
            print("checking Current Assets in balance sheet...")
            if 'Current Assets' in balance_sheet.index:
                current_assets_data = balance_sheet.loc['Current Assets'].dropna()
                print(f" Current Assets raw data shape: {current_assets_data.shape}")
                print(f" Current Assets dates: {[date.year for date in current_assets_data.index]}")
                
                current_assets_df = pd.DataFrame({
                    'Year': [date.year for date in current_assets_data.index],
                    'Current Assets (M USD)': pd.to_numeric(current_assets_data.values, errors='coerce') / 1e6
                }).sort_values('Year', ascending=False)
                current_assets_df['Current Assets (M USD)'] = current_assets_df['Current Assets (M USD)'].round(0)
                yahoo_data['current_assets'] = current_assets_df
                print(f"current assets data fetched successfully: {len(current_assets_df)} years")
                print(f" sample data: {current_assets_df.head(2).to_dict('records')}")
            else:
                print("current assets data not available in balance sheet index")
                print(f" available balance sheet items: {list(balance_sheet.index[:10])}")
            
            # 流动负债 (Current Liabilities)
            print("checking Current Liabilities in balance sheet...")
            if 'Current Liabilities' in balance_sheet.index:
                current_liab_data = balance_sheet.loc['Current Liabilities'].dropna()
                print(f" Current Liabilities raw data shape: {current_liab_data.shape}")
                print(f" Current Liabilities dates: {[date.year for date in current_liab_data.index]}")
                
                current_liab_df = pd.DataFrame({
                    'Year': [date.year for date in current_liab_data.index],
                    'Current Liabilities (M USD)': pd.to_numeric(current_liab_data.values, errors='coerce') / 1e6
                }).sort_values('Year', ascending=False)
                current_liab_df['Current Liabilities (M USD)'] = current_liab_df['Current Liabilities (M USD)'].round(0)
                yahoo_data['current_liabilities'] = current_liab_df
                print(f"current liabilities data fetched successfully: {len(current_liab_df)} years")
                print(f" sample data: {current_liab_df.head(2).to_dict('records')}")
            else:
                print("current liabilities data not available in balance sheet index")
            
            # 计算流动比率 (Current Ratio)
            if 'current_assets' in yahoo_data and 'current_liabilities' in yahoo_data:
                ca_df = yahoo_data['current_assets']
                cl_df = yahoo_data['current_liabilities']
                
                # 合并数据并计算流动比率
                merged_df = pd.merge(ca_df, cl_df, on='Year', how='inner')
                if not merged_df.empty:
                    current_ratio_df = pd.DataFrame()
                    current_ratio_df['Year'] = merged_df['Year']
                    current_ratio_df['Current Ratio'] = (merged_df['Current Assets (M USD)'] / merged_df['Current Liabilities (M USD)']).round(4)
                    yahoo_data['current_ratio'] = current_ratio_df
                    print("current ratio calculation successful")
            
            # =============== 新增：如果自由現金流缺失，嘗試計算 ===============
            if 'free_cash_flow' not in yahoo_data and 'cash_flow' in yahoo_data:
                print("attempting to calculate free cash flow...")
                
                # 方法1：嘗試從現金流表獲取資本支出
                capex_labels = ['Capital Expenditure', 'Capital Expenditures', 'Capex']
                capex_found = False
                
                for label in capex_labels:
                    if label in cash_flow.index:
                        capex_data = cash_flow.loc[label].dropna()
                        ocf_df = yahoo_data['cash_flow']
                        
                        capex_df = pd.DataFrame({
                            'Year': [date.year for date in capex_data.index],
                            'Capex': pd.to_numeric(capex_data.values, errors='coerce') / 1e6
                        })
                        
                        # 合併營運現金流和資本支出
                        merged_fcf = pd.merge(
                            ocf_df[['Year', 'Operating Cash Flow (M USD)']],
                            capex_df,
                            on='Year',
                            how='inner'
                        )
                        
                        if not merged_fcf.empty:
                            fcf_calculated_df = pd.DataFrame()
                            fcf_calculated_df['Year'] = merged_fcf['Year']
                            # 自由現金流 = 營運現金流 - 資本支出（絕對值）
                            fcf_calculated_df['Free Cash Flow (M USD)'] = (
                                merged_fcf['Operating Cash Flow (M USD)'] - abs(merged_fcf['Capex'])
                            ).round(0)
                            yahoo_data['free_cash_flow'] = fcf_calculated_df
                            print(f"free cash flow calculated successfully: {len(fcf_calculated_df)} years")
                            capex_found = True
                            break
                
                if not capex_found:
                    print("cannot calculate free cash flow - capex data not available")
            
            # =============== 歷史數據補充（三重數據源：SEC + Alpha Vantage）===============
            print("checking and supplementing historical data from multiple sources...")
            
            # 1. 首先嘗試 SEC API
            sec_historical_data = self.get_sec_historical_data(ticker)
            
            # 2. 然後嘗試 Alpha Vantage（特別是針對缺失的現金流數據）
            alpha_vantage_data = None
            missing_cash_flow_metrics = []
            for metric in ['free_cash_flow', 'cash_flow_financing', 'cash_flow_investing']:
                if metric not in yahoo_data or yahoo_data[metric].empty:
                    missing_cash_flow_metrics.append(metric)
            
            if missing_cash_flow_metrics:
                print(f"     缺失現金流指標: {missing_cash_flow_metrics}")
                alpha_vantage_data = self.get_alpha_vantage_cash_flow(ticker)
            
            # 3. 合併所有數據源
            cash_flow_metrics = [
                'current_assets', 'current_liabilities', 'current_ratio',
                'free_cash_flow', 'cash_flow_investing', 'cash_flow_financing', 
                'cash_and_cash_equivalents', 'operating_cash_flow'
            ]
            
            data_source_summary = {}
            
            # 合併 SEC 數據
            if sec_historical_data:
                for data_type, sec_df in sec_historical_data.items():
                    if data_type in cash_flow_metrics:
                        if data_type not in yahoo_data or yahoo_data[data_type].empty:
                            yahoo_data[data_type] = sec_df
                            data_source_summary[data_type] = f"SEC ({len(sec_df)} years)"
                            print(f" [SEC] historical data supplement: {data_type} ({len(sec_df)} years)")
                        else:
                            existing_df = yahoo_data[data_type]
                            combined_df = pd.concat([existing_df, sec_df]).drop_duplicates(subset=['Year'], keep='first').sort_values('Year', ascending=False)
                            yahoo_data[data_type] = combined_df
                            total_years = len(combined_df)
                            yahoo_years = len(existing_df)
                            sec_years = len(sec_df)
                            data_source_summary[data_type] = f"Yahoo+SEC ({total_years} years: {yahoo_years}+{sec_years})"
                            print(f" [SEC] historical data merged: {data_type} (Total: {total_years} years)")
            
            # 合併 Alpha Vantage 數據（優先補充缺失的現金流指標）
            if alpha_vantage_data:
                for data_type, av_df in alpha_vantage_data.items():
                    if data_type in cash_flow_metrics:
                        if data_type not in yahoo_data or yahoo_data[data_type].empty:
                            yahoo_data[data_type] = av_df
                            data_source_summary[data_type] = f"Alpha Vantage ({len(av_df)} years)"
                            print(f" [ALPHA] data supplement: {data_type} ({len(av_df)} years)")
                        else:
                            existing_df = yahoo_data[data_type]
                            combined_df = pd.concat([existing_df, av_df]).drop_duplicates(subset=['Year'], keep='first').sort_values('Year', ascending=False)
                            yahoo_data[data_type] = combined_df
                            total_years = len(combined_df)
                            existing_years = len(existing_df)
                            av_years = len(av_df)
                            current_source = data_source_summary.get(data_type, "Yahoo")
                            data_source_summary[data_type] = f"{current_source}+AV ({total_years} years)"
                            print(f" [ALPHA] data merged: {data_type} (Total: {total_years} years)")
            
            # 顯示多重數據源整合摘要
            print(f"\n[SUMMARY] Multi-Source Historical Data Enhancement Summary:")
            for metric in cash_flow_metrics:
                if metric in yahoo_data and not yahoo_data[metric].empty:
                    years_count = len(yahoo_data[metric])
                    year_range = f"{yahoo_data[metric]['Year'].min()}-{yahoo_data[metric]['Year'].max()}"
                    source_info = data_source_summary.get(metric, f"Yahoo ({years_count} years)")
                    print(f"   • {metric}: {years_count} years ({year_range}) - {source_info}")
                else:
                    print(f"   [MISSING] {metric}: no data available from any source")
            
            # 特別檢查關鍵現金流指標的可用性
            key_metrics = ['free_cash_flow', 'cash_flow_financing', 'cash_and_cash_equivalents']
            available_key_metrics = 0
            for metric in key_metrics:
                if metric in yahoo_data and not yahoo_data[metric].empty:
                    available_key_metrics += 1
            
            completion_rate = available_key_metrics / len(key_metrics) * 100
            print(f"\n[METRICS] Key Cash Flow Metrics Availability: {available_key_metrics}/{len(key_metrics)} ({completion_rate:.0f}%)")
            
            print("enhanced balance sheet metrics processing completed")
            
            # =============== 數據完整性報告 ===============
            print("\n[REPORT] Yahoo Finance Data Completeness Report:")
            print("=" * 60)
            
            complete_metrics = []
            missing_metrics = []
            
            expected_metrics = [
                'revenue', 'income', 'cash_flow', 'equity',
                'total_assets', 'total_liabilities', 'long_term_debt',
                'current_assets', 'current_liabilities', 'current_ratio',
                'free_cash_flow', 'cash_flow_investing', 'cash_flow_financing',
                'cash_and_cash_equivalents', 'retained_earnings_balance'
            ]
            
            for metric in expected_metrics:
                if metric in yahoo_data and not yahoo_data[metric].empty:
                    years_count = len(yahoo_data[metric])
                    complete_metrics.append(f"[OK] {metric}: {years_count} years")
                else:
                    missing_metrics.append(f"[MISSING] {metric}: not available")
            
            print("Complete metrics:")
            for metric in complete_metrics:
                print(f"  {metric}")
            
            if missing_metrics:
                print("\nMissing metrics:")
                for metric in missing_metrics:
                    print(f"  {metric}")
            
            completion_rate = len(complete_metrics) / len(expected_metrics) * 100
            print(f"\n[TOTAL] Overall completion rate: {completion_rate:.1f}%")
            
            return yahoo_data
            
        except Exception as e:
            print(f" Yahoo Finance error: {e}")
            return {}
    
    def get_sec_historical_data(self, ticker):
        """extract historical current assets and current liabilities data from SEC API"""
        try:
            print(f"     嘗試從 SEC API 獲取 {ticker} 的歷史數據...")
            
            # 嘗試從 SEC API 獲取實際數據
            sec_data = self.fetch_sec_api_data(ticker)
            if sec_data:
                print(f"     成功從 SEC API 獲取 {ticker} 的數據")
                return sec_data
            
            print(f"     SEC API 無數據，嘗試從 Yahoo Finance 獲取更多歷史數據...")
            # 如果 SEC API 沒有數據，嘗試從 Yahoo Finance 獲取更多歷史年份
            yahoo_extended_data = self.fetch_yahoo_extended_historical_data(ticker)
            if yahoo_extended_data:
                print(f"     成功從 Yahoo Finance 獲取 {ticker} 的擴展歷史數據")
                return yahoo_extended_data
            
            print(f"     所有網路數據源都無法獲取 {ticker} 的歷史數據")
            print(f"     跳過歷史數據補充，僅使用 Yahoo Finance 的基礎數據")
            return {}
            
        except Exception as e:
            print(f"     SEC historical data extraction failed: {e}")
            return {}
    
    def fetch_sec_api_data(self, ticker):
        """從 SEC EDGAR API 獲取實際的歷史財務數據"""
        try:
            # SEC EDGAR API 的 Company Facts 端點
            cik = self.get_cik_from_ticker(ticker)
            if not cik:
                return None
                
            url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                return self.parse_sec_financial_data(data)
            else:
                print(f"     SEC API 請求失敗: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"     SEC API 錯誤: {e}")
            return None
    
    def get_cik_from_ticker(self, ticker):
        """從股票代號獲取 SEC CIK 號碼"""
        try:
            # 使用 SEC 的 ticker 到 CIK 對應表
            url = "https://www.sec.gov/files/company_tickers.json"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                for item in data.values():
                    if item.get('ticker', '').upper() == ticker.upper():
                        return item.get('cik_str')
            return None
        except Exception as e:
            print(f"     獲取 CIK 失敗: {e}")
            return None
    
    def parse_sec_financial_data(self, data):
        """解析 SEC API 返回的財務數據（擴展版 - 包含現金流數據）"""
        try:
            facts = data.get('facts', {})
            us_gaap = facts.get('us-gaap', {})
            
            # 提取各種財務指標
            result = {}
            
            # 現有的流動資產和流動負債
            current_assets_data = us_gaap.get('AssetsCurrent', {}).get('units', {}).get('USD', [])
            current_liabilities_data = us_gaap.get('LiabilitiesCurrent', {}).get('units', {}).get('USD', [])
            
            # =============== 新增：現金流相關指標 ===============
            
            # 自由現金流（通過營運現金流 - 資本支出計算）
            operating_cash_flow_data = us_gaap.get('NetCashProvidedByUsedInOperatingActivities', {}).get('units', {}).get('USD', [])
            capex_data = us_gaap.get('PaymentsToAcquirePropertyPlantAndEquipment', {}).get('units', {}).get('USD', [])
            
            # 融資現金流
            financing_cash_flow_data = us_gaap.get('NetCashProvidedByUsedInFinancingActivities', {}).get('units', {}).get('USD', [])
            
            # 投資現金流  
            investing_cash_flow_data = us_gaap.get('NetCashProvidedByUsedInInvestingActivities', {}).get('units', {}).get('USD', [])
            
            # 現金及約當現金
            cash_equivalents_data = us_gaap.get('CashAndCashEquivalentsAtCarryingValue', {}).get('units', {}).get('USD', [])
            if not cash_equivalents_data:
                # 備用欄位名稱
                cash_equivalents_data = us_gaap.get('CashCashEquivalentsAndShortTermInvestments', {}).get('units', {}).get('USD', [])
            
            # =============== 處理營運現金流數據 ===============
            if operating_cash_flow_data:
                ocf_df_data = []
                for item in operating_cash_flow_data:
                    if item.get('form') == '10-K':  # 只要年度報告
                        year = int(item.get('fy', 0))
                        if 2010 <= year <= 2025:  # 合理的年份範圍
                            ocf_df_data.append({
                                'Year': year,
                                'Operating Cash Flow (M USD)': item.get('val', 0) / 1000000  # 轉換為百萬
                            })
                
                if ocf_df_data:
                    result['operating_cash_flow'] = pd.DataFrame(ocf_df_data).drop_duplicates('Year').sort_values('Year', ascending=False)
                    print(f"     SEC營運現金流數據: {len(result['operating_cash_flow'])} 年")
            
            # =============== 處理資本支出數據並計算自由現金流 ===============
            if operating_cash_flow_data and capex_data:
                ocf_dict = {}
                capex_dict = {}
                
                # 組織營運現金流數據
                for item in operating_cash_flow_data:
                    if item.get('form') == '10-K':
                        year = int(item.get('fy', 0))
                        if 2010 <= year <= 2025:
                            ocf_dict[year] = item.get('val', 0) / 1000000
                
                # 組織資本支出數據
                for item in capex_data:
                    if item.get('form') == '10-K':
                        year = int(item.get('fy', 0))
                        if 2010 <= year <= 2025:
                            capex_dict[year] = abs(item.get('val', 0)) / 1000000  # 資本支出通常是負值，取絕對值
                
                # 計算自由現金流
                fcf_data = []
                for year in ocf_dict:
                    if year in capex_dict:
                        fcf = ocf_dict[year] - capex_dict[year]
                        fcf_data.append({
                            'Year': year,
                            'Free Cash Flow (M USD)': round(fcf, 0)
                        })
                
                if fcf_data:
                    result['free_cash_flow'] = pd.DataFrame(fcf_data).sort_values('Year', ascending=False)
                    print(f"     SEC自由現金流計算成功: {len(result['free_cash_flow'])} 年")
            
            # =============== 處理融資現金流數據 ===============
            if financing_cash_flow_data:
                fcf_df_data = []
                for item in financing_cash_flow_data:
                    if item.get('form') == '10-K':
                        year = int(item.get('fy', 0))
                        if 2010 <= year <= 2025:
                            fcf_df_data.append({
                                'Year': year,
                                'Cash Flow from Financing (M USD)': item.get('val', 0) / 1000000
                            })
                
                if fcf_df_data:
                    result['cash_flow_financing'] = pd.DataFrame(fcf_df_data).drop_duplicates('Year').sort_values('Year', ascending=False)
                    print(f"     SEC融資現金流數據: {len(result['cash_flow_financing'])} 年")
            
            # =============== 處理投資現金流數據 ===============
            if investing_cash_flow_data:
                icf_df_data = []
                for item in investing_cash_flow_data:
                    if item.get('form') == '10-K':
                        year = int(item.get('fy', 0))
                        if 2010 <= year <= 2025:
                            icf_df_data.append({
                                'Year': year,
                                'Cash Flow from Investing (M USD)': item.get('val', 0) / 1000000
                            })
                
                if icf_df_data:
                    result['cash_flow_investing'] = pd.DataFrame(icf_df_data).drop_duplicates('Year').sort_values('Year', ascending=False)
                    print(f"     SEC投資現金流數據: {len(result['cash_flow_investing'])} 年")
            
            # =============== 處理現金及約當現金數據 ===============
            if cash_equivalents_data:
                ce_df_data = []
                for item in cash_equivalents_data:
                    if item.get('form') == '10-K':
                        year = int(item.get('fy', 0))
                        if 2010 <= year <= 2025:
                            ce_df_data.append({
                                'Year': year,
                                'Cash and Cash Equivalents (M USD)': item.get('val', 0) / 1000000
                            })
                
                if ce_df_data:
                    result['cash_and_cash_equivalents'] = pd.DataFrame(ce_df_data).drop_duplicates('Year').sort_values('Year', ascending=False)
                    print(f"     SEC現金及約當現金數據: {len(result['cash_and_cash_equivalents'])} 年")
            
            # =============== 原有的流動資產和流動負債處理 ===============
            if current_assets_data:
                ca_df_data = []
                for item in current_assets_data:
                    if item.get('form') == '10-K':  # 只要年度報告
                        year = int(item.get('fy', 0))
                        if 2010 <= year <= 2025:  # 合理的年份範圍
                            ca_df_data.append({
                                'Year': year,
                                'Current Assets (M USD)': item.get('val', 0) / 1000000  # 轉換為百萬
                            })
                
                if ca_df_data:
                    result['current_assets'] = pd.DataFrame(ca_df_data).drop_duplicates('Year').sort_values('Year', ascending=False)
            
            if current_liabilities_data:
                cl_df_data = []
                for item in current_liabilities_data:
                    if item.get('form') == '10-K':
                        year = int(item.get('fy', 0))
                        if 2010 <= year <= 2025:
                            cl_df_data.append({
                                'Year': year,
                                'Current Liabilities (M USD)': item.get('val', 0) / 1000000
                            })
                
                if cl_df_data:
                    result['current_liabilities'] = pd.DataFrame(cl_df_data).drop_duplicates('Year').sort_values('Year', ascending=False)
            
            # 計算流動比率
            if 'current_assets' in result and 'current_liabilities' in result:
                ca_df = result['current_assets']
                cl_df = result['current_liabilities']
                merged_df = pd.merge(ca_df, cl_df, on='Year', how='inner')
                
                if not merged_df.empty:
                    cr_data = []
                    for _, row in merged_df.iterrows():
                        if row['Current Liabilities (M USD)'] != 0:
                            ratio = round(row['Current Assets (M USD)'] / row['Current Liabilities (M USD)'], 4)
                            cr_data.append({'Year': row['Year'], 'Current Ratio': ratio})
                    
                    if cr_data:
                        result['current_ratio'] = pd.DataFrame(cr_data).sort_values('Year', ascending=False)
            
            return result if result else None
            
        except Exception as e:
            print(f"     解析 SEC 數據失敗: {e}")
            return None
    
    def fetch_yahoo_extended_historical_data(self, ticker):
        """從 Yahoo Finance 獲取擴展的歷史數據（嘗試更多年份）"""
        try:
            import yfinance as yf
            
            stock = yf.Ticker(ticker)
            
            # 嘗試獲取更長時間的資產負債表數據
            balance_sheet = stock.balance_sheet
            
            if balance_sheet is not None and not balance_sheet.empty:
                result = {}
                
                # 提取流動資產
                if 'Current Assets' in balance_sheet.index:
                    ca_data = []
                    for col in balance_sheet.columns:
                        year = col.year
                        value = balance_sheet.loc['Current Assets', col]
                        if pd.notna(value) and value > 0:
                            ca_data.append({
                                'Year': year,
                                'Current Assets (M USD)': float(value / 1000000)
                            })
                    
                    if ca_data:
                        result['current_assets'] = pd.DataFrame(ca_data).sort_values('Year', ascending=False)
                
                # 提取流動負債
                if 'Current Liabilities' in balance_sheet.index:
                    cl_data = []
                    for col in balance_sheet.columns:
                        year = col.year
                        value = balance_sheet.loc['Current Liabilities', col]
                        if pd.notna(value) and value > 0:
                            cl_data.append({
                                'Year': year,
                                'Current Liabilities (M USD)': float(value / 1000000)
                            })
                    
                    if cl_data:
                        result['current_liabilities'] = pd.DataFrame(cl_data).sort_values('Year', ascending=False)
                
                # 計算流動比率
                if 'current_assets' in result and 'current_liabilities' in result:
                    ca_df = result['current_assets']
                    cl_df = result['current_liabilities']
                    merged_df = pd.merge(ca_df, cl_df, on='Year', how='inner')
                    
                    if not merged_df.empty:
                        cr_data = []
                        for _, row in merged_df.iterrows():
                            if row['Current Liabilities (M USD)'] != 0:
                                ratio = round(row['Current Assets (M USD)'] / row['Current Liabilities (M USD)'], 4)
                                cr_data.append({'Year': row['Year'], 'Current Ratio': ratio})
                        
                        if cr_data:
                            result['current_ratio'] = pd.DataFrame(cr_data).sort_values('Year', ascending=False)
                
                return result if result else None
            
            return None
            
        except Exception as e:
            print(f"     Yahoo Finance 擴展歷史數據獲取失敗: {e}")
            return None
    
    # ============= data comparison and analysis =============
    
    def compare_with_yahoo(self, macrotrends_data, yahoo_data, ticker):
        """automatically compare the difference between Macrotrends and Yahoo"""
        print(f"\n{ticker.upper()} dual data source precise comparison")
        print("=" * 70)
        
        comparison_summary = {}
        
        # compare each metric
        metrics = {
            'revenue': ('revenue', 'Revenue (M USD)'),
            'income': ('net income', 'Net Income (M USD)'),
            'cash_flow': ('cash flow', 'Operating Cash Flow (M USD)'),
            'equity': ('shareholders equity', 'Shareholders Equity (M USD)')
        }
        
        for metric_key, (metric_name, column_name) in metrics.items():
            print(f"\n{metric_name} comparison analysis:")
            print("-" * 50)
            
            macro_df = macrotrends_data.get(metric_key)
            yahoo_df = yahoo_data.get(metric_key)
            
            if macro_df is not None and yahoo_df is not None:
                # merge data for precise comparison
                merged = pd.merge(
                    macro_df[['Year', column_name]].rename(columns={column_name: 'Macrotrends'}),
                    yahoo_df[['Year', column_name]].rename(columns={column_name: 'Yahoo Finance'}),
                    on='Year',
                    how='inner'  # only compare common years
                )
                
                if not merged.empty:
                    # calculate difference
                    merged['absolute difference'] = abs(merged['Macrotrends'] - merged['Yahoo Finance'])
                    merged['difference percentage'] = (merged['absolute difference'] / merged['Yahoo Finance'] * 100).round(2)
                    
                    # sort and display
                    merged = merged.sort_values('Year', ascending=False)
                    print(merged[['Year', 'Macrotrends', 'Yahoo Finance', 'difference percentage']].to_string(index=False))
                    
                    # statistical analysis
                    avg_diff = merged['difference percentage'].mean()
                    max_diff = merged['difference percentage'].max()
                    min_diff = merged['difference percentage'].min()
                    
                    print(f"\n statistical summary:")
                    print(f"   • average difference: {avg_diff:.2f}%")
                    print(f"   • maximum difference: {max_diff:.2f}%")
                    print(f"   • minimum difference: {min_diff:.2f}%")
                    print(f"   • compared years: {len(merged)} years")
                    
                    # consistency rating
                    if avg_diff < 1:
                        consistency_rating = " extremely consistent"
                    elif avg_diff < 3:
                        consistency_rating = " highly consistent"
                    elif avg_diff < 10:
                        consistency_rating = " moderately consistent"
                    else:
                        consistency_rating = " large difference"
                    
                    print(f"   • consistency rating: {consistency_rating}")
                    
                    comparison_summary[metric_key] = {
                        'avg_diff': avg_diff,
                        'max_diff': max_diff,
                        'years_compared': len(merged),
                        'rating': consistency_rating
                    }
                else:
                    print("     no common years data to compare")
                    comparison_summary[metric_key] = {'status': 'no_common_years'}
                    
            elif macro_df is not None:
                years_count = len(macro_df)
                year_range = f"{macro_df['Year'].min()}-{macro_df['Year'].max()}"
                print(f"     only Macrotrends has data: {years_count} years ({year_range})")
                comparison_summary[metric_key] = {'status': 'macrotrends_only', 'years': years_count}
                
            elif yahoo_df is not None:
                years_count = len(yahoo_df)
                year_range = f"{yahoo_df['Year'].min()}-{yahoo_df['Year'].max()}"
                print(f"     only Yahoo Finance has data: {years_count} years ({year_range})")
                comparison_summary[metric_key] = {'status': 'yahoo_only', 'years': years_count}
                
            else:
                print("     both data sources have no data")
                comparison_summary[metric_key] = {'status': 'no_data'}
        
        return comparison_summary
    
    def compare_data_sources(self, macrotrends_data, yahoo_data, ticker, company_name):
        """compare the difference between two data sources"""
        print(f"\ndata source comparison analysis")
        print("=" * 80)
        
        comparison_results = {}
        
        # compare each metric
        metrics = {
            'revenue': ('revenue', 'Revenue (M USD)'),
            'income': ('net income', 'Net Income (M USD)'),
            'cash_flow': ('operating cash flow', 'Operating Cash Flow (M USD)'),
            'equity': ('shareholders equity', 'Shareholders Equity (M USD)')
        }
        
        for metric_key, (metric_name, column_name) in metrics.items():
            print(f"\n{metric_name} comparison:")
            print("-" * 40)
            
            macro_df = macrotrends_data.get(metric_key)
            yahoo_df = yahoo_data.get(metric_key)
            
            if macro_df is not None and yahoo_df is not None:
                # merge data for comparison
                merged = pd.merge(
                    macro_df[['Year', column_name]].rename(columns={column_name: 'Macrotrends'}),
                    yahoo_df[['Year', column_name]].rename(columns={column_name: 'Yahoo Finance'}),
                    on='Year',
                    how='outer'
                )
                
                # calculate difference
                merged['Difference'] = merged['Macrotrends'] - merged['Yahoo Finance']
                merged['Difference %'] = (merged['Difference'] / merged['Yahoo Finance'] * 100).round(2)
                
                merged = merged.sort_values('Year', ascending=False).head(5)  # only show the latest 5 years
                
                print(merged.to_string(index=False))
                
                # statistical summary
                avg_diff_pct = abs(merged['Difference %'].dropna()).mean()
                print(f"\n    average difference: {avg_diff_pct:.2f}%")
                
                if avg_diff_pct < 5:
                    print("    data highly consistent")
                elif avg_diff_pct < 15:
                    print("     data has slight differences")
                else:
                    print("    data has large differences, need further inspection")
                
                comparison_results[metric_key] = merged
                
            elif macro_df is not None:
                print("   only Macrotrends has data")
                comparison_results[metric_key] = macro_df
            elif yahoo_df is not None:
                print("   only Yahoo Finance has data")
                comparison_results[metric_key] = yahoo_df
            else:
                print("   both data sources have no data")
        
        return comparison_results
    
    def create_comprehensive_report(self, comparison_results, ticker, company_name):
        """create comprehensive report"""
        print(f"\n {company_name} ({ticker.upper()}) comprehensive financial report")
        print("=" * 80)
        
        # data availability summary
        print("\n data availability summary:")
        print("-" * 40)
        
        metrics = ['revenue', 'income', 'cash_flow', 'equity']
        metric_names = ['revenue', 'net income', 'operating cash flow', 'shareholders equity']
        
        for metric, name in zip(metrics, metric_names):
            if metric in comparison_results and not comparison_results[metric].empty:
                years = len(comparison_results[metric])
                latest_year = comparison_results[metric]['Year'].max()
                print(f"   {name}: {years} years of data, latest to {latest_year}")
            else:
                print(f"   {name}: no data")
        
        # integrate best data
        print(f"\n integrated analysis (use the data source with higher consistency):")
        print("-" * 60)
        
        final_data = {}
        
        for metric in metrics:
            if metric in comparison_results:
                df = comparison_results[metric]
                if not df.empty:
                    # if there are two data sources, choose Yahoo Finance (because it is usually more complete)
                    if 'Yahoo Finance' in df.columns:
                        final_data[metric] = df[['Year', 'Yahoo Finance']].rename(
                            columns={'Yahoo Finance': metric_names[metrics.index(metric)]}
                        )
                    elif 'Macrotrends' in df.columns:
                        final_data[metric] = df[['Year', 'Macrotrends']].rename(
                            columns={'Macrotrends': metric_names[metrics.index(metric)]}
                        )
                    else:
                        # single data source
                        final_data[metric] = df
        
        # merge all data
        if final_data:
            merged_final = None
            for metric, df in final_data.items():
                if merged_final is None:
                    merged_final = df.copy()
                else:
                    merged_final = pd.merge(merged_final, df, on='Year', how='outer')
            
            merged_final = merged_final.sort_values('Year', ascending=False).head(10)
            
            print(merged_final.to_string(index=False))
            
            return merged_final
        else:
            print("no financial data available")
            return pd.DataFrame()
    
    def save_comparison_results(self, comparison_results, final_data, ticker, company_name):
        """save comparison results to Excel"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{ticker.upper()}_{company_name.replace(' ', '_')}_dual_source_analysis_{timestamp}.xlsx"
        
        try:
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # final integrated data
                if not final_data.empty:
                    final_data.to_excel(writer, sheet_name='Final_Integrated_Data', index=False)
                
                # each comparison result
                metrics = {
                    'revenue': 'revenue comparison',
                    'income': 'net income comparison', 
                    'cash_flow': 'cash flow comparison',
                    'equity': 'shareholders equity comparison'
                }
                
                for metric_key, sheet_name in metrics.items():
                    if metric_key in comparison_results and not comparison_results[metric_key].empty:
                        comparison_results[metric_key].to_excel(writer, sheet_name=sheet_name, index=False)
                
                # metadata
                metadata = pd.DataFrame({
                    'item': ['company name', 'ticker', 'analysis time', 'data source', 'analysis type'],
                    'content': [
                        company_name,
                        ticker.upper(),
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'Macrotrends + Yahoo Finance',
                        'dual data source cross-comparison analysis'
                    ]
                })
                metadata.to_excel(writer, sheet_name='Metadata', index=False)
            
            print(f"\n analysis results saved to: {filename}")
            
        except Exception as e:
            print(f" save failed: {e}")
    
    def organize_data_by_year(self, macrotrends_data, yahoo_data):
        """organize data by year (improved version - dynamic field name processing)"""
        year_data = {}
        current_year = datetime.now().year
        target_years = list(range(current_year - 9, current_year + 1))  # last 10 years
        
        print(f" target year range: {target_years[0]} - {target_years[-1]}")
        
        for year in target_years:
            year_data[year] = {
                'macrotrends': {},
                'yahoo': {}
            }
            
            # process Macrotrends data (dynamic field name processing)
            for data_key, df in macrotrends_data.items():
                if df is not None and not df.empty and 'Year' in df.columns:
                    year_row = df[df['Year'] == year]
                    if not year_row.empty:
                        # 取得數值欄位（不是 Year 的欄位）
                        value_cols = [col for col in df.columns if col != 'Year']
                        if value_cols:
                            value_col = value_cols[0]  # 通常只有一個數值欄位
                            try:
                                value = float(year_row.iloc[0][value_col])
                                
                                # 映射到標準化的鍵名
                                if data_key == 'revenue':
                                    year_data[year]['macrotrends']['revenue'] = value
                                elif data_key == 'income':
                                    year_data[year]['macrotrends']['income'] = value
                                elif data_key == 'cash_flow':
                                    year_data[year]['macrotrends']['cash_flow'] = value
                                elif data_key == 'equity':
                                    year_data[year]['macrotrends']['equity'] = value
                                elif data_key == 'gross_profit':
                                    year_data[year]['macrotrends']['gross_profit'] = value
                                elif data_key == 'operating_expenses':
                                    year_data[year]['macrotrends']['operating_expenses'] = value
                                elif data_key == 'operating_income':
                                    year_data[year]['macrotrends']['operating_income'] = value
                                elif data_key == 'income_before_tax':
                                    year_data[year]['macrotrends']['income_before_tax'] = value
                                elif data_key == 'eps_basic':
                                    year_data[year]['macrotrends']['eps_basic'] = value
                                elif data_key == 'outstanding_shares':
                                    year_data[year]['macrotrends']['outstanding_shares'] = value
                                elif data_key == 'cogs':
                                    year_data[year]['macrotrends']['cogs'] = value
                                # 新增：资产负债表指标
                                elif data_key == 'total_assets':
                                    year_data[year]['macrotrends']['total_assets'] = value
                                elif data_key == 'total_liabilities':
                                    year_data[year]['macrotrends']['total_liabilities'] = value
                                elif data_key == 'long_term_debt':
                                    year_data[year]['macrotrends']['long_term_debt'] = value
                                elif data_key == 'retained_earnings_balance':
                                    year_data[year]['macrotrends']['retained_earnings_balance'] = value
                                # 新增：现金流指标
                                elif data_key == 'free_cash_flow':
                                    year_data[year]['macrotrends']['free_cash_flow'] = value
                                elif data_key == 'cash_flow_investing':
                                    year_data[year]['macrotrends']['cash_flow_investing'] = value
                                elif data_key == 'cash_flow_financing':
                                    year_data[year]['macrotrends']['cash_flow_financing'] = value
                                elif data_key == 'cash_and_cash_equivalents':
                                    year_data[year]['macrotrends']['cash_and_cash_equivalents'] = value
                                # 新增：流動資產和流動負債（Macrotrends）
                                elif data_key == 'current_assets':
                                    year_data[year]['macrotrends']['current_assets'] = value
                                elif data_key == 'current_liabilities':
                                    year_data[year]['macrotrends']['current_liabilities'] = value
                                elif data_key == 'current_ratio':
                                    year_data[year]['macrotrends']['current_ratio'] = value
                            except (ValueError, TypeError, IndexError):
                                continue
            
            # 處理 Yahoo Finance 數據（動態處理欄位名稱）
            for data_key, df in yahoo_data.items():
                if df is not None and not df.empty and 'Year' in df.columns:
                    year_row = df[df['Year'] == year]
                    if not year_row.empty:
                        # 取得數值欄位（不是 Year 的欄位）
                        value_cols = [col for col in df.columns if col != 'Year']
                        if value_cols:
                            value_col = value_cols[0]  # 通常只有一個數值欄位
                            try:
                                value = float(year_row.iloc[0][value_col])
                                
                                # 映射到標準化的鍵名
                                if data_key == 'revenue':
                                    year_data[year]['yahoo']['revenue'] = value
                                elif data_key == 'income':
                                    year_data[year]['yahoo']['income'] = value
                                elif data_key == 'cash_flow':
                                    year_data[year]['yahoo']['cash_flow'] = value
                                elif data_key == 'equity':
                                    year_data[year]['yahoo']['equity'] = value
                                # 新增：资产负债表指标（Yahoo Finance）
                                elif data_key == 'total_assets':
                                    year_data[year]['yahoo']['total_assets'] = value
                                elif data_key == 'total_liabilities':
                                    year_data[year]['yahoo']['total_liabilities'] = value
                                elif data_key == 'long_term_debt':
                                    year_data[year]['yahoo']['long_term_debt'] = value
                                elif data_key == 'current_assets':
                                    year_data[year]['yahoo']['current_assets'] = value
                                elif data_key == 'current_liabilities':
                                    year_data[year]['yahoo']['current_liabilities'] = value
                                elif data_key == 'current_ratio':
                                    year_data[year]['yahoo']['current_ratio'] = value
                                # 新增：擴展的Yahoo Finance指標
                                elif data_key == 'retained_earnings_balance':
                                    year_data[year]['yahoo']['retained_earnings_balance'] = value
                                elif data_key == 'free_cash_flow':
                                    year_data[year]['yahoo']['free_cash_flow'] = value
                                elif data_key == 'cash_flow_investing':
                                    year_data[year]['yahoo']['cash_flow_investing'] = value
                                elif data_key == 'cash_flow_financing':
                                    year_data[year]['yahoo']['cash_flow_financing'] = value
                                elif data_key == 'cash_and_cash_equivalents':
                                    year_data[year]['yahoo']['cash_and_cash_equivalents'] = value
                            except (ValueError, TypeError, IndexError):
                                continue
        
        return year_data
    
    def analyze_stock_with_database(self, ticker, company_name=None, save_to_db=True):
        """complete stock analysis process (including database storage)"""
        if not company_name:
            company_name = self.get_company_name_from_ticker(ticker)
        
        print(f"\n{'='*80}")
        print(f"10-Year Dual Source Stock Analysis: {company_name} ({ticker.upper()})")
        print(f"{'='*80}")
        
        # connect database
        if save_to_db:
            if not self.connect_database():
                print("WARNING: Database connection failed, will skip database storage")
                save_to_db = False
        
        try:
            # get data from two data sources
            macrotrends_data = self.get_macrotrends_data(ticker, company_name)
            yahoo_data = self.get_yahoo_finance_data(ticker)
            
            # new: precise cross-comparison
            comparison_summary = self.compare_with_yahoo(macrotrends_data, yahoo_data, ticker)
            
            # organize data by year
            year_data_dict = self.organize_data_by_year(macrotrends_data, yahoo_data)
            
            # compare data sources (original function)
            comparison_results = self.compare_data_sources(macrotrends_data, yahoo_data, ticker, company_name)
            
            # create comprehensive report
            final_data = self.create_comprehensive_report(comparison_results, ticker, company_name)
            
            # save to database
            if save_to_db and year_data_dict:
                print(f"\nSaving 10-year data to database...")
                if self.save_to_database(ticker, company_name, year_data_dict):
                    print("SUCCESS: Database storage completed")
                else:
                    print("ERROR: Database storage failed")
            
            return comparison_results, final_data, year_data_dict
            
        finally:
            # disconnect database
            if save_to_db:
                self.disconnect_database()
    
    def analyze_stock(self, ticker, company_name=None):
        """complete stock analysis process (backward compatibility)"""
        if not company_name:
            company_name = self.get_company_name_from_ticker(ticker)
        
        print(f"\n{'='*80}")
        print(f"Dual Source Stock Analysis: {company_name} ({ticker.upper()})")
        print(f"{'='*80}")
        
        # get data from two data sources
        macrotrends_data = self.get_macrotrends_data(ticker, company_name)
        yahoo_data = self.get_yahoo_finance_data(ticker)
        
        # new: precise cross-comparison
        comparison_summary = self.compare_with_yahoo(macrotrends_data, yahoo_data, ticker)
        
        # compare data sources (original function)
        comparison_results = self.compare_data_sources(macrotrends_data, yahoo_data, ticker, company_name)
        
        # create comprehensive report
        final_data = self.create_comprehensive_report(comparison_results, ticker, company_name)
        
        return comparison_results, final_data
    
    def get_alpha_vantage_cash_flow(self, ticker):
        """從 Alpha Vantage API 獲取現金流數據作為備用數據源"""
        try:
            # Alpha Vantage 免費API密鑰（你可以替換為自己的）
            # 注意：免費版有請求限制，每分鐘5次，每天500次
            api_key = "demo"  # 使用demo密鑰進行測試，實際使用請申請自己的密鑰
            
            url = f"https://www.alphavantage.co/query"
            params = {
                'function': 'CASH_FLOW',
                'symbol': ticker,
                'apikey': api_key
            }
            
            print(f"     嘗試從 Alpha Vantage 獲取 {ticker} 現金流數據...")
            
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                
                # 檢查API響應是否有效
                if 'Note' in data:
                    print(f"     Alpha Vantage API 頻率限制: {data['Note']}")
                    return None
                
                if 'Error Message' in data:
                    print(f"     Alpha Vantage API 錯誤: {data['Error Message']}")
                    return None
                
                if 'annualReports' not in data:
                    print(f"     Alpha Vantage API 無年度現金流數據")
                    return None
                
                annual_reports = data['annualReports']
                result = {}
                
                # 處理營運現金流
                operating_cf_data = []
                for report in annual_reports:
                    if 'fiscalDateEnding' in report and 'operatingCashflow' in report:
                        try:
                            year = int(report['fiscalDateEnding'][:4])
                            operating_cf = float(report['operatingCashflow']) / 1000000  # 轉換為百萬
                            if 2010 <= year <= 2025:
                                operating_cf_data.append({
                                    'Year': year,
                                    'Operating Cash Flow (M USD)': round(operating_cf, 0)
                                })
                        except (ValueError, TypeError):
                            continue
                
                if operating_cf_data:
                    result['operating_cash_flow'] = pd.DataFrame(operating_cf_data).sort_values('Year', ascending=False)
                    print(f"     Alpha Vantage 營運現金流: {len(result['operating_cash_flow'])} 年")
                
                # 處理投資現金流
                investing_cf_data = []
                for report in annual_reports:
                    if 'fiscalDateEnding' in report and 'cashflowFromInvestment' in report:
                        try:
                            year = int(report['fiscalDateEnding'][:4])
                            investing_cf = float(report['cashflowFromInvestment']) / 1000000
                            if 2010 <= year <= 2025:
                                investing_cf_data.append({
                                    'Year': year,
                                    'Cash Flow from Investing (M USD)': round(investing_cf, 0)
                                })
                        except (ValueError, TypeError):
                            continue
                
                if investing_cf_data:
                    result['cash_flow_investing'] = pd.DataFrame(investing_cf_data).sort_values('Year', ascending=False)
                    print(f"     Alpha Vantage 投資現金流: {len(result['cash_flow_investing'])} 年")
                
                # 處理融資現金流
                financing_cf_data = []
                for report in annual_reports:
                    if 'fiscalDateEnding' in report and 'cashflowFromFinancing' in report:
                        try:
                            year = int(report['fiscalDateEnding'][:4])
                            financing_cf = float(report['cashflowFromFinancing']) / 1000000
                            if 2010 <= year <= 2025:
                                financing_cf_data.append({
                                    'Year': year,
                                    'Cash Flow from Financing (M USD)': round(financing_cf, 0)
                                })
                        except (ValueError, TypeError):
                            continue
                
                if financing_cf_data:
                    result['cash_flow_financing'] = pd.DataFrame(financing_cf_data).sort_values('Year', ascending=False)
                    print(f"     [ALPHA] Financing Cash Flow: {len(result['cash_flow_financing'])} years")
                
                # 計算自由現金流（如果有營運現金流）
                if 'operating_cash_flow' in result:
                    # 嘗試獲取資本支出數據
                    capex_data = []
                    for report in annual_reports:
                        if 'fiscalDateEnding' in report and 'capitalExpenditures' in report:
                            try:
                                year = int(report['fiscalDateEnding'][:4])
                                capex = abs(float(report['capitalExpenditures'])) / 1000000  # 取絕對值並轉換為百萬
                                if 2010 <= year <= 2025:
                                    capex_data.append({'Year': year, 'Capex': capex})
                            except (ValueError, TypeError):
                                continue
                    
                    if capex_data:
                        capex_df = pd.DataFrame(capex_data)
                        ocf_df = result['operating_cash_flow']
                        
                        # 合併並計算自由現金流
                        merged_df = pd.merge(
                            ocf_df[['Year', 'Operating Cash Flow (M USD)']],
                            capex_df,
                            on='Year',
                            how='inner'
                        )
                        
                        if not merged_df.empty:
                            fcf_data = []
                            for _, row in merged_df.iterrows():
                                fcf = row['Operating Cash Flow (M USD)'] - row['Capex']
                                fcf_data.append({
                                    'Year': row['Year'],
                                    'Free Cash Flow (M USD)': round(fcf, 0)
                                })
                            
                            if fcf_data:
                                result['free_cash_flow'] = pd.DataFrame(fcf_data).sort_values('Year', ascending=False)
                                print(f"     [ALPHA] Free Cash Flow Calculated: {len(result['free_cash_flow'])} years")
                
                return result if result else None
            
            else:
                print(f"     Alpha Vantage API 請求失敗: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"     Alpha Vantage API 錯誤: {e}")
            return None

def main():
    """main program - support command line parameters and interactive mode"""
    # check command line parameters
    if len(sys.argv) == 3:
        # non-interactive mode: python dual_source_analyzer.py <mode> <ticker>
        mode = sys.argv[1]
        ticker = sys.argv[2].upper()
        
        print(f"FinBot Web Mode: Analyzing {ticker} with mode {mode}")
        
        if mode != "2":
            print("ERROR: Only mode 2 is supported in non-interactive mode")
            sys.exit(1)
        
        analyzer = DualSourceAnalyzer()
        company_name = analyzer.get_company_name_from_ticker(ticker)
        
        try:
            comparison_results, final_data, year_data = analyzer.analyze_stock_with_database(
                ticker, company_name, save_to_db=True
            )
            
            if year_data:
                print("SUCCESS: Analysis completed and data saved to database")
                sys.exit(0)
            else:
                print("ERROR: No data to save")
                sys.exit(1)
                
        except Exception as e:
            print(f"ERROR: Analysis failed: {e}")
            sys.exit(1)
    
    # interactive mode (original logic)
    print("FinBot Dual Source Stock Analyzer v2.0")
    print("=" * 70)
    print("Data Sources: Macrotrends.net + Yahoo Finance")
    print("Functions: Cross-validation, Analysis, Database Storage")
    print("New Feature: 10-year financial data extraction")
    print()
    
    # use default database configuration (based on config.php)
    print("Database: 13.114.174.139/finbot_db")
    
    analyzer = DualSourceAnalyzer()  # use default configuration, no extra parameters
    
    while True:
        try:
            print("\n" + "="*70)
            print("Analysis Mode Selection:")
            print("1. Standard Analysis (display results, optional Excel save)")
            print("2. Complete Analysis + Database Storage (10-year data)")
            print("3. Display Stored Data (database query)")
            print("4. Exit")
            
            mode_choice = input("\nSelect mode (1-4): ").strip()
            
            if mode_choice == "4":
                print("Thank you for using!")
                break
            elif mode_choice == "3":
                # database query function (under development)
                print("Database query function under development...")
                continue
            elif mode_choice not in ["1", "2"]:
                print("Please select a valid option (1-4)")
                continue
            
            # enter stock ticker
            ticker = input("\nEnter stock ticker (e.g. AAPL, TSLA, MSFT): ").strip().upper()
            
            if not ticker:
                print("Please enter a valid stock ticker")
                continue
            
            # optional
            company_input = input("Enter company name (optional, press Enter for default): ").strip()
            company_name = company_input if company_input else None
            
            # 根據選擇執行不同的分析
            if mode_choice == "1":
                # 標準分析
                comparison_results, final_data = analyzer.analyze_stock(ticker, company_name)
                
                # 詢問是否保存Excel
                if comparison_results:
                    save_choice = input("\nSave analysis results to Excel? (y/n): ").lower().strip()
                    if save_choice in ['y', 'yes']:
                        analyzer.save_comparison_results(
                            comparison_results, 
                            final_data, 
                            ticker, 
                            analyzer.get_company_name_from_ticker(ticker) if not company_name else company_name
                        )
            
            elif mode_choice == "2":
                # 完整分析 + 資料庫存儲
                save_db_choice = input("\nSave data to database? (y/n): ").lower().strip()
                save_to_db = save_db_choice in ['y', 'yes']
                
                comparison_results, final_data, year_data = analyzer.analyze_stock_with_database(
                    ticker, company_name, save_to_db
                )
                
                # 詢問是否額外保存Excel
                if comparison_results:
                    save_excel_choice = input("\nSave additional Excel file? (y/n): ").lower().strip()
                    if save_excel_choice in ['y', 'yes']:
                        analyzer.save_comparison_results(
                            comparison_results, 
                            final_data, 
                            ticker, 
                            analyzer.get_company_name_from_ticker(ticker) if not company_name else company_name
                        )
                
                # 顯示年度數據摘要
                if year_data:
                    print(f"\n10-Year Data Summary:")
                    print("-" * 60)
                    for year, data in sorted(year_data.items(), reverse=True):
                        macro_count = len([v for v in data['macrotrends'].values() if v is not None])
                        yahoo_count = len([v for v in data['yahoo'].values() if v is not None])
                        print(f"  {year}: Macrotrends({macro_count} items) | Yahoo Finance({yahoo_count} items)")
            
            # 詢問是否繼續
            continue_choice = input("\nAnalyze other stocks? (y/n): ").lower().strip()
            if continue_choice not in ['y', 'yes']:
                print("Thank you for using!")
                break
                
        except KeyboardInterrupt:
            print(f"\nThank you for using!")
            break
        except Exception as e:
            print(f"\nError occurred: {e}")
            print("Please check network connection, stock ticker or database connection")

if __name__ == "__main__":
    main() 