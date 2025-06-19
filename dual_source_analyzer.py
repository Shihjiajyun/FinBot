#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
雙數據源股票財務分析工具
同時從 macrotrends.net 和 Yahoo Finance 抓取數據並進行交叉比對
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

class DualSourceAnalyzer:
    def __init__(self, db_config=None):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # 資料庫配置 (基於 config.php)
        self.db_config = db_config or {
            'host': '43.207.210.147',
            'database': 'finbot_db',
            'user': 'myuser',
            'password': '123456789',
            'charset': 'utf8mb4'
        }
        
        self.db_connection = None
    
    def get_company_name_from_ticker(self, ticker):
        """從股票代碼獲取公司名稱"""
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
            'ORCL': 'Oracle'
        }
        
        return company_names.get(ticker.upper(), ticker.capitalize())
    
    # ============= 資料庫操作方法 =============
    
    def connect_database(self):
        """連接資料庫"""
        try:
            self.db_connection = mysql.connector.connect(**self.db_config)
            if self.db_connection.is_connected():
                print("✅ 資料庫連接成功")
                return True
        except Error as e:
            print(f"❌ 資料庫連接失敗: {e}")
            return False
    
    def disconnect_database(self):
        """斷開資料庫連接"""
        if self.db_connection and self.db_connection.is_connected():
            self.db_connection.close()
            print("📤 資料庫連接已關閉")
    
    def calculate_data_quality(self, macrotrends_data, yahoo_data):
        """計算數據品質等級 (改進版 - 支援 Macrotrends 四項數據)"""
        score = 0
        
        # 基礎數據評分（營收和淨利）
        revenue_count = 0
        if macrotrends_data.get('revenue') is not None: revenue_count += 1
        if yahoo_data.get('revenue') is not None: revenue_count += 1
        
        income_count = 0
        if macrotrends_data.get('income') is not None: income_count += 1
        if yahoo_data.get('income') is not None: income_count += 1
        
        # 營運現金流計算（包含 Macrotrends）
        cash_flow_count = 0
        if macrotrends_data.get('cash_flow') is not None: cash_flow_count += 1
        if yahoo_data.get('cash_flow') is not None: cash_flow_count += 1
        
        # 股東權益計算（包含 Macrotrends）
        equity_count = 0
        if macrotrends_data.get('equity') is not None: equity_count += 1
        if yahoo_data.get('equity') is not None: equity_count += 1
        
        # 營收評分 (最高30分)
        if revenue_count == 2: score += 30  # 雙數據源
        elif revenue_count == 1: score += 20  # 單數據源
        
        # 淨利評分 (最高30分)
        if income_count == 2: score += 30  # 雙數據源
        elif income_count == 1: score += 20  # 單數據源
        
        # 營運現金流評分 (最高20分)
        if cash_flow_count == 2: score += 20  # 雙數據源 (Macrotrends + Yahoo)
        elif cash_flow_count == 1: score += 15  # 單數據源
        
        # 股東權益評分 (最高20分)
        if equity_count == 2: score += 20  # 雙數據源 (Macrotrends + Yahoo)
        elif equity_count == 1: score += 15  # 單數據源
        
        # 確保分數不超過100
        total_score = min(score, 100)
        
        # 評級標準
        if total_score >= 80:
            return total_score, 'excellent'
        elif total_score >= 60:
            return total_score, 'good'
        elif total_score >= 40:
            return total_score, 'fair'
        else:
            return total_score, 'poor'
    
    def calculate_variance(self, value1, value2):
        """計算兩個數值的差異百分比"""
        if value1 is None or value2 is None or value2 == 0:
            return None
        return abs((value1 - value2) / value2 * 100)
    
    def save_to_database(self, ticker, company_name, year_data_dict):
        """將近十年數據批量存入資料庫"""
        if not self.db_connection or not self.db_connection.is_connected():
            print("❌ 資料庫未連接")
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
                
                # 計算差異百分比
                revenue_variance = self.calculate_variance(macro_revenue, yahoo_revenue)
                income_variance = self.calculate_variance(macro_income, yahoo_income)
                
                # 選擇最佳數據（營收和淨利優先Yahoo，現金流和權益優先Macrotrends）
                final_revenue = yahoo_revenue if yahoo_revenue is not None else macro_revenue
                final_income = yahoo_income if yahoo_income is not None else macro_income
                final_cash_flow = macro_cash_flow if macro_cash_flow is not None else yahoo_cash_flow
                final_equity = macro_equity if macro_equity is not None else yahoo_equity
                
                # 檢查是否有足夠的基礎數據才存入資料庫
                if final_revenue is None and final_income is None:
                    print(f"  ⚠️  {year} 年度數據不足，跳過存儲")
                    continue
                
                # 插入或更新數據 (簡潔版資料表結構)
                sql = """
                INSERT INTO filings (
                    ticker, company_name, filing_year, filing_type,
                    annual_revenue, net_income, operating_cash_flow, shareholders_equity,
                    data_source, data_quality_score, data_quality_flag
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) ON DUPLICATE KEY UPDATE
                    company_name = VALUES(company_name),
                    annual_revenue = VALUES(annual_revenue),
                    net_income = VALUES(net_income),
                    operating_cash_flow = VALUES(operating_cash_flow),
                    shareholders_equity = VALUES(shareholders_equity),
                    data_source = VALUES(data_source),
                    data_quality_score = VALUES(data_quality_score),
                    data_quality_flag = VALUES(data_quality_flag),
                    last_updated = NOW()
                """
                
                values = (
                    ticker, company_name, year, 'ANNUAL_FINANCIAL',
                    final_revenue, final_income, final_cash_flow, final_equity,
                    'dual_source', quality_score, quality_flag
                )
                
                cursor.execute(sql, values)
                success_count += 1
                
                # 顯示存入的數據詳情
                data_summary = []
                if final_revenue: data_summary.append(f"營收: {final_revenue:,.0f}M")
                if final_income: data_summary.append(f"淨利: {final_income:,.0f}M")
                if final_cash_flow: data_summary.append(f"現金流: {final_cash_flow:,.0f}M")
                if final_equity: data_summary.append(f"權益: {final_equity:,.0f}M")
                
                print(f"  ✅ {year} 年度數據已存入: {', '.join(data_summary)} (品質: {quality_flag})")
            
            self.db_connection.commit()
            print(f"\n💾 成功存入 {success_count} 年度的財務數據到資料庫")
            return True
            
        except Error as e:
            print(f"❌ 資料庫操作失敗: {e}")
            if self.db_connection:
                self.db_connection.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
    
    # ============= MACROTRENDS 數據抓取 =============
    
    def get_macrotrends_table(self, url, title_keyword):
        """從 macrotrends.net 抓取指定表格數據"""
        try:
            print(f"    🔍 Macrotrends: {url}")
            res = requests.get(url, headers=self.headers, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, 'html.parser')

            tables = soup.find_all("table", class_="historical_data_table table")
            
            for table in tables:
                if title_keyword.lower() in table.text.lower():
                    df = pd.read_html(str(table))[0]
                    df.columns = [col.strip() for col in df.columns]
                    df = df.dropna()
                    return df
            
            return None
            
        except Exception as e:
            print(f"    ❌ Macrotrends 錯誤: {e}")
            return None
    
    def get_macrotrends_data(self, ticker, company_name):
        """從 macrotrends 獲取財務數據"""
        print("📊 從 Macrotrends 抓取數據...")
        
        company_name_slug = company_name.lower().replace(' ', '-').replace('.', '').replace(',', '')
        macrotrends_data = {}
        
        # 營收
        print("  💰 抓取營收數據...")
        revenue_url = f'https://www.macrotrends.net/stocks/charts/{ticker}/{company_name_slug}/revenue'
        revenue_df = self.get_macrotrends_table(revenue_url, "Annual Revenue")
        if revenue_df is not None and len(revenue_df.columns) >= 2:
            revenue_df.columns = ['Year', 'Revenue (M USD)']
            revenue_df['Revenue (M USD)'] = revenue_df['Revenue (M USD)'].replace(r'[\$,]', '', regex=True)
            revenue_df['Revenue (M USD)'] = pd.to_numeric(revenue_df['Revenue (M USD)'], errors='coerce')
            macrotrends_data['revenue'] = revenue_df
            print("    ✅ 營收數據獲取成功")
        else:
            print("    ❌ 營收數據獲取失敗")
        
        time.sleep(1)
        
        # 淨利
        print("  💵 抓取淨利數據...")
        income_url = f'https://www.macrotrends.net/stocks/charts/{ticker}/{company_name_slug}/net-income'
        income_df = self.get_macrotrends_table(income_url, "Annual Net Income")
        if income_df is not None and len(income_df.columns) >= 2:
            income_df.columns = ['Year', 'Net Income (M USD)']
            income_df['Net Income (M USD)'] = income_df['Net Income (M USD)'].replace(r'[\$,]', '', regex=True)
            income_df['Net Income (M USD)'] = pd.to_numeric(income_df['Net Income (M USD)'], errors='coerce')
            macrotrends_data['income'] = income_df
            print("    ✅ 淨利數據獲取成功")
        else:
            print("    ❌ 淨利數據獲取失敗")
        
        time.sleep(1)
        
        # 自由現金流 - 使用新的抓取方法
        print("  💳 抓取自由現金流數據...")
        cash_flow_df = self.fetch_free_cash_flow_macrotrends(ticker, company_name_slug)
        if cash_flow_df is not None:
            macrotrends_data['cash_flow'] = cash_flow_df
            print("    ✅ 自由現金流數據獲取成功")
        else:
            print("    ❌ 自由現金流數據獲取失敗")
        
        time.sleep(1)
        
        # 股東權益 - 使用改進的 JavaScript 解析方法（基於成功的 test_simple_equity.py）
        print("  🏛️ 抓取股東權益數據...")
        equity_df = self.get_shareholder_equity(ticker, company_name_slug)
        if equity_df is not None:
            macrotrends_data['equity'] = equity_df
            print("    ✅ 股東權益數據獲取成功")
        else:
            print("    ❌ 股東權益數據獲取失敗")
        
        return macrotrends_data
    
    def fetch_free_cash_flow_macrotrends(self, ticker, company_slug):
        """從 Macrotrends 抓取自由現金流數據（推薦方法）"""
        try:
            url = f"https://www.macrotrends.net/stocks/charts/{ticker}/{company_slug}/free-cash-flow"
            print(f"    🔍 Macrotrends Free Cash Flow: {url}")
            
            res = requests.get(url, headers=self.headers, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, 'html.parser')
            
            tables = soup.find_all("table", class_="historical_data_table table")
            
            for table in tables:
                if "Free Cash Flow" in table.text:
                    df = pd.read_html(str(table))[0]
                    df.columns = ['Year', 'Free Cash Flow (M USD)']
                    df = df.dropna()
                    
                    # 清理年份數據
                    df['Year'] = df['Year'].astype(str).str.extract(r'(\d{4})')[0]
                    df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
                    
                    # 清理現金流數據
                    df['Free Cash Flow (M USD)'] = df['Free Cash Flow (M USD)'].replace(r'[\$,]', '', regex=True)
                    df['Free Cash Flow (M USD)'] = pd.to_numeric(df['Free Cash Flow (M USD)'], errors='coerce')
                    
                    result_df = df.dropna()
                    if not result_df.empty:
                        # 重新命名為標準格式
                        result_df = result_df.rename(columns={'Free Cash Flow (M USD)': 'Operating Cash Flow (M USD)'})
                        return result_df
            
            print("    ❌ 找不到包含 'Free Cash Flow' 的表格")
            return None
            
        except Exception as e:
            print(f"    ❌ Macrotrends 自由現金流錯誤: {e}")
            return None
    
    def get_shareholder_equity(self, ticker, company_slug):
        """從 Macrotrends 抓取股東權益數據（基於實際成功的 test_simple_equity.py 邏輯）"""
        try:
            # 使用與 test_simple_equity.py 相同的 URL 格式
            url = f"https://www.macrotrends.net/stocks/charts/{ticker}/{company_slug}/total-share-holder-equity"
            print(f"    🔍 Macrotrends Shareholder Equity: {url}")
            
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            print(f"    ✅ 網頁抓取成功，大小: {len(response.text):,} 字符")
            
            # 使用與 test_simple_equity.py 相同的 BeautifulSoup 解析方法
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(response.text, "html.parser")
            tables = soup.find_all("table", class_="historical_data_table")
            
            if not tables:
                print("    ❌ 沒有找到任何 historical_data_table 表格")
                return None
            
            print(f"    ✅ 找到 {len(tables)} 個資料表")
            
            # 取得主資料表（通常是第一個）
            table = tables[0]
            rows = table.find_all("tr")
            
            print(f"    📊 表格包含 {len(rows)} 行數據")
            
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
                            print(f"      解析: {year} 年 = ${equity_value:,.0f}M")
                    except (ValueError, TypeError) as e:
                        print(f"      跳過無效數據: {year_text} = {equity_text} ({e})")
                        continue
            
            if not data:
                print("    ❌ 未能解析出任何有效的股東權益數據")
                return None
            
            # 轉換為 DataFrame
            df = pd.DataFrame(data)
            df = df.sort_values('Year', ascending=False)  # 按年份降序排列
            
            print(f"    ✅ 成功解析 {len(df)} 年的股東權益數據")
            print(f"    📈 年份範圍: {df['Year'].min()} - {df['Year'].max()}")
            
            # 顯示最近5年的數據預覽
            recent_years = df.head(5)
            print("    📋 最近數據預覽:")
            for _, row in recent_years.iterrows():
                print(f"      {int(row['Year'])}: ${row['Shareholders Equity (M USD)']:,.0f}M")
            
            return df
            
        except Exception as e:
            print(f"    ❌ Macrotrends 股東權益錯誤: {e}")
            return None
    
    # ============= YAHOO FINANCE 數據抓取 =============
    
    def get_yahoo_finance_data(self, ticker):
        """從 Yahoo Finance 獲取財務數據"""
        print("🌐 從 Yahoo Finance 抓取數據...")
        
        try:
            stock = yf.Ticker(ticker)
            
            # 獲取財務報表
            financials = stock.financials
            balance_sheet = stock.balance_sheet
            cash_flow = stock.cashflow
            
            yahoo_data = {}
            
            # 營收 (Total Revenue)
            print("  💰 處理營收數據...")
            if 'Total Revenue' in financials.index:
                revenue_data = financials.loc['Total Revenue'].dropna()
                revenue_df = pd.DataFrame({
                    'Year': [date.year for date in revenue_data.index],
                    'Revenue (M USD)': pd.to_numeric(revenue_data.values, errors='coerce') / 1e6
                }).sort_values('Year', ascending=False)
                revenue_df['Revenue (M USD)'] = revenue_df['Revenue (M USD)'].round(0)
                yahoo_data['revenue'] = revenue_df
                print("    ✅ 營收數據獲取成功")
            else:
                print("    ❌ 營收數據不可用")
            
            # 淨利 (Net Income)
            print("  💵 處理淨利數據...")
            if 'Net Income' in financials.index:
                income_data = financials.loc['Net Income'].dropna()
                income_df = pd.DataFrame({
                    'Year': [date.year for date in income_data.index],
                    'Net Income (M USD)': pd.to_numeric(income_data.values, errors='coerce') / 1e6
                }).sort_values('Year', ascending=False)
                income_df['Net Income (M USD)'] = income_df['Net Income (M USD)'].round(0)
                yahoo_data['income'] = income_df
                print("    ✅ 淨利數據獲取成功")
            else:
                print("    ❌ 淨利數據不可用")
            
            # 營運現金流 (Operating Cash Flow)
            print("  💳 處理營運現金流數據...")
            if 'Operating Cash Flow' in cash_flow.index:
                cf_data = cash_flow.loc['Operating Cash Flow'].dropna()
                cf_df = pd.DataFrame({
                    'Year': [date.year for date in cf_data.index],
                    'Operating Cash Flow (M USD)': pd.to_numeric(cf_data.values, errors='coerce') / 1e6
                }).sort_values('Year', ascending=False)
                cf_df['Operating Cash Flow (M USD)'] = cf_df['Operating Cash Flow (M USD)'].round(0)
                yahoo_data['cash_flow'] = cf_df
                print("    ✅ 營運現金流數據獲取成功")
            else:
                print("    ❌ 營運現金流數據不可用")
            
            # 股東權益 (Stockholders' Equity)
            print("  🏛️ 處理股東權益數據...")
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
                    print(f"    ✅ 股東權益數據獲取成功 (使用: {label})")
                    equity_found = True
                    break
            
            if not equity_found:
                print("    ❌ 股東權益數據不可用")
            
            return yahoo_data
            
        except Exception as e:
            print(f"❌ Yahoo Finance 錯誤: {e}")
            return {}
    
    # ============= 數據比較和分析 =============
    
    def compare_with_yahoo(self, macrotrends_data, yahoo_data, ticker):
        """自動比對 Macrotrends vs Yahoo 的數值落差"""
        print(f"\n🔍 {ticker.upper()} 雙數據源精確比對")
        print("=" * 70)
        
        comparison_summary = {}
        
        # 比較各項指標
        metrics = {
            'revenue': ('營收', 'Revenue (M USD)'),
            'income': ('淨利', 'Net Income (M USD)'),
            'cash_flow': ('現金流', 'Operating Cash Flow (M USD)'),
            'equity': ('股東權益', 'Shareholders Equity (M USD)')
        }
        
        for metric_key, (metric_name, column_name) in metrics.items():
            print(f"\n📊 {metric_name} 比對分析:")
            print("-" * 50)
            
            macro_df = macrotrends_data.get(metric_key)
            yahoo_df = yahoo_data.get(metric_key)
            
            if macro_df is not None and yahoo_df is not None:
                # 合併數據進行精確比對
                merged = pd.merge(
                    macro_df[['Year', column_name]].rename(columns={column_name: 'Macrotrends'}),
                    yahoo_df[['Year', column_name]].rename(columns={column_name: 'Yahoo Finance'}),
                    on='Year',
                    how='inner'  # 只比較共同年份
                )
                
                if not merged.empty:
                    # 計算差異
                    merged['絕對差異'] = abs(merged['Macrotrends'] - merged['Yahoo Finance'])
                    merged['差異百分比'] = (merged['絕對差異'] / merged['Yahoo Finance'] * 100).round(2)
                    
                    # 排序並顯示
                    merged = merged.sort_values('Year', ascending=False)
                    print(merged[['Year', 'Macrotrends', 'Yahoo Finance', '差異百分比']].to_string(index=False))
                    
                    # 統計分析
                    avg_diff = merged['差異百分比'].mean()
                    max_diff = merged['差異百分比'].max()
                    min_diff = merged['差異百分比'].min()
                    
                    print(f"\n📈 統計摘要:")
                    print(f"   • 平均差異: {avg_diff:.2f}%")
                    print(f"   • 最大差異: {max_diff:.2f}%")
                    print(f"   • 最小差異: {min_diff:.2f}%")
                    print(f"   • 比對年份: {len(merged)} 年")
                    
                    # 一致性評級
                    if avg_diff < 1:
                        consistency_rating = "🟢 極度一致"
                    elif avg_diff < 3:
                        consistency_rating = "🟡 高度一致"
                    elif avg_diff < 10:
                        consistency_rating = "🟠 中度一致"
                    else:
                        consistency_rating = "🔴 差異較大"
                    
                    print(f"   • 一致性評級: {consistency_rating}")
                    
                    comparison_summary[metric_key] = {
                        'avg_diff': avg_diff,
                        'max_diff': max_diff,
                        'years_compared': len(merged),
                        'rating': consistency_rating
                    }
                else:
                    print("   ❌ 沒有共同年份數據可比較")
                    comparison_summary[metric_key] = {'status': 'no_common_years'}
                    
            elif macro_df is not None:
                years_count = len(macro_df)
                year_range = f"{macro_df['Year'].min()}-{macro_df['Year'].max()}"
                print(f"   📍 僅 Macrotrends 有數據: {years_count} 年 ({year_range})")
                comparison_summary[metric_key] = {'status': 'macrotrends_only', 'years': years_count}
                
            elif yahoo_df is not None:
                years_count = len(yahoo_df)
                year_range = f"{yahoo_df['Year'].min()}-{yahoo_df['Year'].max()}"
                print(f"   📍 僅 Yahoo Finance 有數據: {years_count} 年 ({year_range})")
                comparison_summary[metric_key] = {'status': 'yahoo_only', 'years': years_count}
                
            else:
                print("   ❌ 兩個數據源都沒有數據")
                comparison_summary[metric_key] = {'status': 'no_data'}
        
        return comparison_summary
    
    def compare_data_sources(self, macrotrends_data, yahoo_data, ticker, company_name):
        """比較兩個數據源的差異"""
        print(f"\n🔍 數據源比較分析")
        print("=" * 80)
        
        comparison_results = {}
        
        # 比較各項指標
        metrics = {
            'revenue': ('營收', 'Revenue (M USD)'),
            'income': ('淨利', 'Net Income (M USD)'),
            'cash_flow': ('營運現金流', 'Operating Cash Flow (M USD)'),
            'equity': ('股東權益', 'Shareholders Equity (M USD)')
        }
        
        for metric_key, (metric_name, column_name) in metrics.items():
            print(f"\n📊 {metric_name} 比較:")
            print("-" * 40)
            
            macro_df = macrotrends_data.get(metric_key)
            yahoo_df = yahoo_data.get(metric_key)
            
            if macro_df is not None and yahoo_df is not None:
                # 合併數據進行比較
                merged = pd.merge(
                    macro_df[['Year', column_name]].rename(columns={column_name: 'Macrotrends'}),
                    yahoo_df[['Year', column_name]].rename(columns={column_name: 'Yahoo Finance'}),
                    on='Year',
                    how='outer'
                )
                
                # 計算差異
                merged['Difference'] = merged['Macrotrends'] - merged['Yahoo Finance']
                merged['Difference %'] = (merged['Difference'] / merged['Yahoo Finance'] * 100).round(2)
                
                merged = merged.sort_values('Year', ascending=False).head(5)  # 只顯示最近5年
                
                print(merged.to_string(index=False))
                
                # 統計摘要
                avg_diff_pct = abs(merged['Difference %'].dropna()).mean()
                print(f"\n  📈 平均差異: {avg_diff_pct:.2f}%")
                
                if avg_diff_pct < 5:
                    print("  ✅ 數據高度一致")
                elif avg_diff_pct < 15:
                    print("  ⚠️  數據存在輕微差異")
                else:
                    print("  ❌ 數據差異較大，需要進一步檢查")
                
                comparison_results[metric_key] = merged
                
            elif macro_df is not None:
                print("  只有 Macrotrends 有數據")
                comparison_results[metric_key] = macro_df
            elif yahoo_df is not None:
                print("  只有 Yahoo Finance 有數據")
                comparison_results[metric_key] = yahoo_df
            else:
                print("  兩個數據源都沒有數據")
        
        return comparison_results
    
    def create_comprehensive_report(self, comparison_results, ticker, company_name):
        """創建綜合報告"""
        print(f"\n📋 {company_name} ({ticker.upper()}) 綜合財務報告")
        print("=" * 80)
        
        # 數據可用性摘要
        print("\n📊 數據可用性摘要:")
        print("-" * 40)
        
        metrics = ['revenue', 'income', 'cash_flow', 'equity']
        metric_names = ['營收', '淨利', '營運現金流', '股東權益']
        
        for metric, name in zip(metrics, metric_names):
            if metric in comparison_results and not comparison_results[metric].empty:
                years = len(comparison_results[metric])
                latest_year = comparison_results[metric]['Year'].max()
                print(f"  ✅ {name}: {years} 年數據，最新到 {latest_year}")
            else:
                print(f"  ❌ {name}: 無數據")
        
        # 整合最佳數據
        print(f"\n📈 整合分析 (優先使用一致性較高的數據源):")
        print("-" * 60)
        
        final_data = {}
        
        for metric in metrics:
            if metric in comparison_results:
                df = comparison_results[metric]
                if not df.empty:
                    # 如果有兩個數據源，選擇 Yahoo Finance (因為通常更完整)
                    if 'Yahoo Finance' in df.columns:
                        final_data[metric] = df[['Year', 'Yahoo Finance']].rename(
                            columns={'Yahoo Finance': metric_names[metrics.index(metric)]}
                        )
                    elif 'Macrotrends' in df.columns:
                        final_data[metric] = df[['Year', 'Macrotrends']].rename(
                            columns={'Macrotrends': metric_names[metrics.index(metric)]}
                        )
                    else:
                        # 單一數據源
                        final_data[metric] = df
        
        # 合併所有數據
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
            print("沒有可用的財務數據")
            return pd.DataFrame()
    
    def save_comparison_results(self, comparison_results, final_data, ticker, company_name):
        """保存比較結果到 Excel"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{ticker.upper()}_{company_name.replace(' ', '_')}_dual_source_analysis_{timestamp}.xlsx"
        
        try:
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # 最終整合數據
                if not final_data.empty:
                    final_data.to_excel(writer, sheet_name='Final_Integrated_Data', index=False)
                
                # 各項比較結果
                metrics = {
                    'revenue': '營收比較',
                    'income': '淨利比較', 
                    'cash_flow': '現金流比較',
                    'equity': '股東權益比較'
                }
                
                for metric_key, sheet_name in metrics.items():
                    if metric_key in comparison_results and not comparison_results[metric_key].empty:
                        comparison_results[metric_key].to_excel(writer, sheet_name=sheet_name, index=False)
                
                # 元數據
                metadata = pd.DataFrame({
                    '項目': ['公司名稱', '股票代碼', '分析時間', '數據源', '分析類型'],
                    '內容': [
                        company_name,
                        ticker.upper(),
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'Macrotrends + Yahoo Finance',
                        '雙數據源交叉比對分析'
                    ]
                })
                metadata.to_excel(writer, sheet_name='Metadata', index=False)
            
            print(f"\n💾 分析結果已保存到：{filename}")
            
        except Exception as e:
            print(f"❌ 保存失敗：{e}")
    
    def organize_data_by_year(self, macrotrends_data, yahoo_data):
        """將數據按年份組織"""
        year_data = {}
        current_year = datetime.now().year
        target_years = list(range(current_year - 9, current_year + 1))  # 近十年
        
        print(f"📅 目標年份範圍: {target_years[0]} - {target_years[-1]}")
        
        for year in target_years:
            year_data[year] = {
                'macrotrends': {},
                'yahoo': {}
            }
            
            # 處理 Macrotrends 數據
            if 'revenue' in macrotrends_data:
                revenue_row = macrotrends_data['revenue'][macrotrends_data['revenue']['Year'] == year]
                if not revenue_row.empty:
                    year_data[year]['macrotrends']['revenue'] = float(revenue_row.iloc[0]['Revenue (M USD)'])
            
            if 'income' in macrotrends_data:
                income_row = macrotrends_data['income'][macrotrends_data['income']['Year'] == year]
                if not income_row.empty:
                    year_data[year]['macrotrends']['income'] = float(income_row.iloc[0]['Net Income (M USD)'])
            
            # 新增：Macrotrends 營運現金流
            if 'cash_flow' in macrotrends_data:
                cf_row = macrotrends_data['cash_flow'][macrotrends_data['cash_flow']['Year'] == year]
                if not cf_row.empty:
                    year_data[year]['macrotrends']['cash_flow'] = float(cf_row.iloc[0]['Operating Cash Flow (M USD)'])
            
            # 新增：Macrotrends 股東權益
            if 'equity' in macrotrends_data:
                equity_row = macrotrends_data['equity'][macrotrends_data['equity']['Year'] == year]
                if not equity_row.empty:
                    year_data[year]['macrotrends']['equity'] = float(equity_row.iloc[0]['Shareholders Equity (M USD)'])
            
            # 處理 Yahoo Finance 數據
            if 'revenue' in yahoo_data:
                revenue_row = yahoo_data['revenue'][yahoo_data['revenue']['Year'] == year]
                if not revenue_row.empty:
                    year_data[year]['yahoo']['revenue'] = float(revenue_row.iloc[0]['Revenue (M USD)'])
            
            if 'income' in yahoo_data:
                income_row = yahoo_data['income'][yahoo_data['income']['Year'] == year]
                if not income_row.empty:
                    year_data[year]['yahoo']['income'] = float(income_row.iloc[0]['Net Income (M USD)'])
            
            if 'cash_flow' in yahoo_data:
                cf_row = yahoo_data['cash_flow'][yahoo_data['cash_flow']['Year'] == year]
                if not cf_row.empty:
                    year_data[year]['yahoo']['cash_flow'] = float(cf_row.iloc[0]['Operating Cash Flow (M USD)'])
            
            if 'equity' in yahoo_data:
                equity_row = yahoo_data['equity'][yahoo_data['equity']['Year'] == year]
                if not equity_row.empty:
                    year_data[year]['yahoo']['equity'] = float(equity_row.iloc[0]['Shareholders Equity (M USD)'])
        
        return year_data
    
    def analyze_stock_with_database(self, ticker, company_name=None, save_to_db=True):
        """完整的股票分析流程（含資料庫存儲）"""
        if not company_name:
            company_name = self.get_company_name_from_ticker(ticker)
        
        print(f"\n{'='*80}")
        print(f"🚀 近十年雙數據源股票分析：{company_name} ({ticker.upper()})")
        print(f"{'='*80}")
        
        # 連接資料庫
        if save_to_db:
            if not self.connect_database():
                print("⚠️  資料庫連接失敗，將跳過資料庫存儲")
                save_to_db = False
        
        try:
            # 從兩個數據源抓取數據
            macrotrends_data = self.get_macrotrends_data(ticker, company_name)
            yahoo_data = self.get_yahoo_finance_data(ticker)
            
            # 新增：精確交叉比對
            comparison_summary = self.compare_with_yahoo(macrotrends_data, yahoo_data, ticker)
            
            # 按年份組織數據
            year_data_dict = self.organize_data_by_year(macrotrends_data, yahoo_data)
            
            # 比較數據源（原有功能）
            comparison_results = self.compare_data_sources(macrotrends_data, yahoo_data, ticker, company_name)
            
            # 創建綜合報告
            final_data = self.create_comprehensive_report(comparison_results, ticker, company_name)
            
            # 存入資料庫
            if save_to_db and year_data_dict:
                print(f"\n💾 正在將近十年數據存入資料庫...")
                if self.save_to_database(ticker, company_name, year_data_dict):
                    print("✅ 資料庫存儲完成")
                else:
                    print("❌ 資料庫存儲失敗")
            
            return comparison_results, final_data, year_data_dict
            
        finally:
            # 斷開資料庫連接
            if save_to_db:
                self.disconnect_database()
    
    def analyze_stock(self, ticker, company_name=None):
        """完整的股票分析流程（向後兼容）"""
        if not company_name:
            company_name = self.get_company_name_from_ticker(ticker)
        
        print(f"\n{'='*80}")
        print(f"🚀 雙數據源股票分析：{company_name} ({ticker.upper()})")
        print(f"{'='*80}")
        
        # 從兩個數據源抓取數據
        macrotrends_data = self.get_macrotrends_data(ticker, company_name)
        yahoo_data = self.get_yahoo_finance_data(ticker)
        
        # 新增：精確交叉比對
        comparison_summary = self.compare_with_yahoo(macrotrends_data, yahoo_data, ticker)
        
        # 比較數據源（原有功能）
        comparison_results = self.compare_data_sources(macrotrends_data, yahoo_data, ticker, company_name)
        
        # 創建綜合報告
        final_data = self.create_comprehensive_report(comparison_results, ticker, company_name)
        
        return comparison_results, final_data

def main():
    """主程序"""
    print("🚀 雙數據源股票財務分析工具 v2.0")
    print("=" * 70)
    print("數據源：Macrotrends.net + Yahoo Finance")
    print("功能：交叉比對、差異分析、數據整合、資料庫存儲")
    print("新功能：近十年財務數據自動抓取與儲存")
    print()
    
    # 使用預設的資料庫配置 (基於 config.php)
    print("📊 使用預設資料庫配置：43.207.210.147/finbot_db")
    
    analyzer = DualSourceAnalyzer()  # 使用預設配置，不傳入額外參數
    
    while True:
        try:
            print("\n" + "="*70)
            print("🎯 選擇分析模式:")
            print("1. 📊 標準分析 (顯示結果，可選保存 Excel)")
            print("2. 💾 完整分析 + 資料庫存儲 (近十年數據)")
            print("3. 🔍 僅顯示已存儲的數據 (從資料庫查詢)")
            print("4. 📤 退出程序")
            
            mode_choice = input("\n請選擇模式 (1-4): ").strip()
            
            if mode_choice == "4":
                print("👋 感謝使用！")
                break
            elif mode_choice == "3":
                # 查詢資料庫功能 (待實現)
                print("🔍 資料庫查詢功能開發中...")
                continue
            elif mode_choice not in ["1", "2"]:
                print("❌ 請選擇有效的選項 (1-4)")
                continue
            
            # 輸入股票代碼
            ticker = input("\n📝 請輸入股票代碼 (例如: AAPL, TSLA, MSFT): ").strip().upper()
            
            if not ticker:
                print("❌ 請輸入有效的股票代碼")
                continue
            
            # 可選：輸入公司名稱
            company_input = input("📝 請輸入公司英文名稱 (可選，直接按 Enter 使用預設): ").strip()
            company_name = company_input if company_input else None
            
            # 根據選擇執行不同的分析
            if mode_choice == "1":
                # 標準分析
                comparison_results, final_data = analyzer.analyze_stock(ticker, company_name)
                
                # 詢問是否保存Excel
                if comparison_results:
                    save_choice = input("\n💾 是否要保存分析結果到 Excel？(y/n): ").lower().strip()
                    if save_choice in ['y', 'yes', '是']:
                        analyzer.save_comparison_results(
                            comparison_results, 
                            final_data, 
                            ticker, 
                            analyzer.get_company_name_from_ticker(ticker) if not company_name else company_name
                        )
            
            elif mode_choice == "2":
                # 完整分析 + 資料庫存儲
                save_db_choice = input("\n💾 是否要將數據存入資料庫？(y/n): ").lower().strip()
                save_to_db = save_db_choice in ['y', 'yes', '是']
                
                comparison_results, final_data, year_data = analyzer.analyze_stock_with_database(
                    ticker, company_name, save_to_db
                )
                
                # 詢問是否額外保存Excel
                if comparison_results:
                    save_excel_choice = input("\n📄 是否額外保存 Excel 檔案？(y/n): ").lower().strip()
                    if save_excel_choice in ['y', 'yes', '是']:
                        analyzer.save_comparison_results(
                            comparison_results, 
                            final_data, 
                            ticker, 
                            analyzer.get_company_name_from_ticker(ticker) if not company_name else company_name
                        )
                
                # 顯示年度數據摘要
                if year_data:
                    print(f"\n📋 近十年數據摘要:")
                    print("-" * 60)
                    for year, data in sorted(year_data.items(), reverse=True):
                        macro_count = len([v for v in data['macrotrends'].values() if v is not None])
                        yahoo_count = len([v for v in data['yahoo'].values() if v is not None])
                        print(f"  {year}: Macrotrends({macro_count}項) | Yahoo Finance({yahoo_count}項)")
            
            # 詢問是否繼續
            continue_choice = input("\n🔄 是否要分析其他股票？(y/n): ").lower().strip()
            if continue_choice not in ['y', 'yes', '是']:
                print("👋 感謝使用！")
                break
                
        except KeyboardInterrupt:
            print(f"\n👋 感謝使用！")
            break
        except Exception as e:
            print(f"\n❌ 發生錯誤: {e}")
            print("請檢查網路連接、股票代碼或資料庫連接是否正確")

if __name__ == "__main__":
    main() 