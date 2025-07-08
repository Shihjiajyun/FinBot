#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Limited Test - FMP API 少量股票測試
適合 Free Plan 用戶，只處理 10 隻知名股票
避免超過 API 限制
"""

import sys
import os

# 添加父目錄到路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 導入主要處理器
from data import FMPStockDataProcessor

def run_amzn_update():
    """執行 AMZN 股票數據強制更新"""
    
    print("🧪 AMZN 股票數據更新測試")
    print("="*50)
    print("專門處理 AMZN (Amazon) 股票數據")
    print("年份範圍: 2014-2024 (11年)")
    print("模式: 強制更新現有數據")
    print("="*50)
    
    # 使用您的 API Key
    api_key = "f1dtgv3q9ZlPAwMNWfxTnhsozQB26lKe"
    
    # 創建處理器
    processor = FMPStockDataProcessor(api_key)
    
    # 只處理 AMZN 股票
    processor.stock_list = ['AMZN']
    
    # 完整11年範圍（2014-2024）
    processor.target_years = list(range(2014, 2025))
    
    print(f"目標股票: {', '.join(processor.stock_list)}")
    print(f"目標年份: {processor.target_years}")
    print(f"預估 API 請求: {len(processor.stock_list) * len(processor.target_years) * 3} 次")
    print("(每隻股票每年需要 3 個請求：損益表 + 資產負債表 + 現金流量表)")
    print()
    
    # 修改處理器以強制更新現有數據
    def force_update_stock_year(self, ticker: str, year: int, company_name: str):
        """強制更新單一股票的單一年份數據（不檢查是否已存在）"""
        try:
            self.logger.info(f"強制更新 {ticker} {year} 年度數據...")
            
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
            
            # 強制存入資料庫（會自動更新現有記錄）
            if self.save_to_database(filing_data):
                return True, f"{year}年數據成功更新"
            else:
                return False, f"{year}年存入資料庫失敗"
                
        except Exception as e:
            self.logger.error(f"處理 {ticker} {year} 失敗: {e}")
            return False, f"{year}年處理錯誤: {str(e)}"
    
    # 綁定新方法到處理器
    import types
    processor.force_update_stock_year = types.MethodType(force_update_stock_year, processor)
    
    # 確認執行
    confirm = input("確定要開始強制更新 AMZN 數據嗎？(y/N): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("取消執行")
        return
    
    try:
        # 執行 AMZN 強制更新
        ticker = 'AMZN'
        
        # 獲取公司名稱
        company_name = processor.get_company_profile(ticker)
        print(f"\n開始處理 {ticker} - {company_name}")
        print("="*50)
        
        success_count = 0
        failure_count = 0
        results = []
        
        # 處理每個年份
        for year in processor.target_years:
            print(f"📅 處理 {year} 年...")
            
            try:
                success, message = processor.force_update_stock_year(ticker, year, company_name)
                
                if success:
                    success_count += 1
                    print(f"   ✅ {message}")
                    results.append(f"✅ {year}: {message}")
                else:
                    failure_count += 1
                    print(f"   ❌ {message}")
                    results.append(f"❌ {year}: {message}")
                
                # API 請求間隔
                import time
                time.sleep(0.5)
                
            except Exception as e:
                failure_count += 1
                error_msg = f"錯誤 - {str(e)}"
                print(f"   ❌ {error_msg}")
                results.append(f"❌ {year}: {error_msg}")
        
        print("\n" + "="*50)
        print("🎉 AMZN 數據更新完成！")
        print(f"成功年份: {success_count}")
        print(f"失敗年份: {failure_count}")
        print(f"總年份數: {success_count + failure_count}")
        success_rate = (success_count / (success_count + failure_count) * 100) if (success_count + failure_count) > 0 else 0
        print(f"成功率: {success_rate:.1f}%")
        print("="*50)
        
        if success_count > 0:
            print("\n🎯 處理結果：")
            for result in results:
                print(f"  {result}")
            
            print("\n💡 接下來您可以：")
            print("1. 檢查資料庫中的 AMZN 更新數據")
            print("2. 查詢成長率計算結果")
            print("3. 對其他股票執行類似更新")
        
    except KeyboardInterrupt:
        print("\n用戶中斷執行")
    except Exception as e:
        print(f"\n程式執行失敗: {e}")

if __name__ == "__main__":
    run_amzn_update() 