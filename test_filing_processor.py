#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試 FinBot 財報處理器
"""

import os
from pathlib import Path
from filing_processor import FilingProcessor

def test_amzn_processing():
    """測試AMZN財報處理"""
    print("🧪 開始測試 AMZN 財報處理...")
    
    processor = FilingProcessor()
    
    try:
        # 檢查AMZN目錄是否存在
        downloads_path = Path("./downloads")
        amzn_path = downloads_path / "AMZN"
        
        if not amzn_path.exists():
            print(f"❌ 測試失敗: AMZN目錄不存在 {amzn_path}")
            print("請確保有 downloads/AMZN 目錄及其子目錄 4/ 和 10-K/")
            return False
        
        # 檢查目標資料夾
        form4_path = amzn_path / "4"
        form10k_path = amzn_path / "10-K"
        
        print(f"📁 Form 4 資料夾: {form4_path} {'✅存在' if form4_path.exists() else '❌不存在'}")
        print(f"📁 10-K 資料夾: {form10k_path} {'✅存在' if form10k_path.exists() else '❌不存在'}")
        
        if form4_path.exists():
            form4_files = list(form4_path.glob("*.txt"))
            print(f"   📄 Form 4 文件數量: {len(form4_files)}")
            if form4_files:
                print(f"   📝 範例文件: {form4_files[0].name}")
        
        if form10k_path.exists():
            form10k_files = list(form10k_path.glob("*.txt"))
            print(f"   📄 10-K 文件數量: {len(form10k_files)}")
            if form10k_files:
                print(f"   📝 範例文件: {form10k_files[0].name}")
        
        # 執行處理
        print("\n🚀 開始處理財報...")
        processor.process_amzn_directory()
        
        print("✅ 測試完成!")
        return True
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        return False
        
    finally:
        processor.close()

def test_form4_extraction():
    """測試Form 4表格提取功能"""
    print("\n🧪 測試 Form 4 表格提取...")
    
    # 使用用戶提供的範例內容
    sample_content = """
    <nonDerivativeTable>
        <nonDerivativeTransaction>
            <securityTitle>
                <value>Common Stock, par value $.01 per share</value>
            </securityTitle>
            <transactionDate>
                <value>2019-02-08</value>
            </transactionDate>
            <transactionAmounts>
                <transactionShares>
                    <value>160</value>
                </transactionShares>
                <transactionPricePerShare>
                    <value>0.00</value>
                </transactionPricePerShare>
            </transactionAmounts>
        </nonDerivativeTransaction>
    </nonDerivativeTable>
    """
    
    processor = FilingProcessor()
    
    try:
        tables = processor.extract_form4_tables(sample_content)
        
        if 'non_derivative_table' in tables:
            print("✅ 成功提取 nonDerivativeTable")
            print(f"📊 內容長度: {len(tables['non_derivative_table'])} 字符")
            print(f"📄 內容預覽: {tables['non_derivative_table'][:200]}...")
        else:
            print("❌ 未能提取 nonDerivativeTable")
        
        if 'derivative_table' in tables:
            print("✅ 成功提取 derivativeTable")
        else:
            print("⚠️ 沒有找到 derivativeTable（正常，因為範例中沒有）")
            
    finally:
        processor.close()

def test_10k_extraction():
    """測試10K Items提取功能"""
    print("\n🧪 測試 10-K Items 提取...")
    
    # 模擬10K內容
    sample_content = """
    Item&#160;1. Business
    This is the business section content...
    
    Item&#160;1A. Risk Factors
    These are the risk factors...
    
    Item&#160;2. Properties
    Information about properties...
    
    Item&#160;7. Management's Discussion and Analysis
    MD&A content here...
    
    Item&#160;8. Financial Statements
    Financial statements and supplementary data...
    
    Item&#160;9. Controls and Procedures
    Controls information...
    """
    
    processor = FilingProcessor()
    
    try:
        items = processor.extract_10k_items(sample_content)
        
        expected_items = ['item_1_content', 'item_1a_content', 'item_2_content', 
                         'item_7_content', 'item_7a_content', 'item_8_content']
        
        for item in expected_items:
            if item in items:
                print(f"✅ 成功提取 {item}: {len(items[item])} 字符")
            else:
                print(f"❌ 未能提取 {item}")
                
    finally:
        processor.close()

if __name__ == "__main__":
    print("🧪 FinBot 財報處理器測試")
    print("=" * 50)
    
    # 測試Form 4提取
    test_form4_extraction()
    
    # 測試10K提取
    test_10k_extraction()
    
    # 測試實際處理
    test_amzn_processing()
    
    print("\n🎉 所有測試完成!") 