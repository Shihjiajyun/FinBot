#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_all.py - 一鍵執行股票下載和ITEM拆解
==========================================
自動執行完整流程：
1. 檢查並下載新股票的10-K財報 (ALL.py)
2. 拆解新下載股票的ITEM內容 (ALL_2.py)
"""

import sys
import os
import time
import subprocess
from pathlib import Path

class FinBotProcessor:
    def __init__(self):
        """初始化FinBot處理器"""
        self.start_time = time.time()
        
        print("🚀 FinBot 一鍵式股票處理器")
        print("=" * 50)
        print("📝 本程式會依序執行:")
        print("   1. 檢查並下載新股票的10-K財報")
        print("   2. 拆解新下載股票的ITEM內容")
        print("   3. 存入資料庫供FinBot查詢")
        print("=" * 50)

    def run_script(self, script_name, description):
        """執行Python腳本"""
        print(f"\n🔧 開始執行: {description}")
        print(f"⚡ 腳本: {script_name}")
        print("-" * 60)
        
        try:
            python_path = sys.executable
            result = subprocess.run(
                [python_path, script_name],
                cwd=Path(__file__).parent,
                capture_output=False,  # 讓輸出直接顯示
                text=True
            )
            
            if result.returncode == 0:
                print(f"\n✅ {description} 完成!")
                return True
            else:
                print(f"\n❌ {description} 失敗 (錯誤碼: {result.returncode})")
                return False
                
        except Exception as e:
            print(f"\n💥 執行 {script_name} 時發生錯誤: {e}")
            return False

    def run_complete_process(self):
        """執行完整處理流程"""
        success_count = 0
        total_steps = 2
        
        # 步驟1: 下載新股票的10-K財報
        print(f"\n{'='*70}")
        print(f"📥 步驟 1/2: 下載新股票的10-K財報")
        print(f"{'='*70}")
        
        if self.run_script("ALL.py", "股票10-K財報下載"):
            success_count += 1
            print("🎉 步驟1完成: 新股票下載成功!")
        else:
            print("⚠️ 步驟1警告: 下載過程可能有問題，但繼續執行拆解")
        
        # 短暫休息
        print("\n⏸️ 休息3秒後繼續...")
        time.sleep(3)
        
        # 步驟2: 拆解ITEM內容
        print(f"\n{'='*70}")
        print(f"🔍 步驟 2/2: 拆解股票ITEM內容")
        print(f"{'='*70}")
        
        if self.run_script("ALL_2.py", "股票ITEM拆解"):
            success_count += 1
            print("🎉 步驟2完成: ITEM拆解成功!")
        else:
            print("❌ 步驟2失敗: ITEM拆解過程出現問題")
        
        # 輸出最終結果
        total_time = time.time() - self.start_time
        
        print(f"\n{'='*70}")
        print(f"🏁 FinBot 處理流程完成!")
        print(f"{'='*70}")
        print(f"📊 執行結果:")
        print(f"   ✅ 成功步驟: {success_count}/{total_steps}")
        print(f"   ⏱️ 總耗時: {total_time/60:.1f} 分鐘")
        
        if success_count == total_steps:
            print(f"\n🎯 所有步驟都成功完成!")
            print(f"💡 現在可以在FinBot系統中查詢新增的股票資料!")
            return True
        elif success_count > 0:
            print(f"\n⚠️ 部分步驟完成，請檢查日誌")
            return True
        else:
            print(f"\n❌ 所有步驟都失敗，請檢查設定")
            return False

def main():
    """主函數"""
    processor = FinBotProcessor()
    
    # 檢查必要的腳本文件
    required_files = ["ALL.py", "ALL_2.py"]
    missing_files = []
    
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"\n❌ 缺少必要文件: {', '.join(missing_files)}")
        print("請確保在正確的目錄中運行此腳本")
        sys.exit(1)
    
    # 確認是否執行
    try:
        response = input(f"\n❓ 確認要執行完整的FinBot處理流程嗎? (y/N): ")
        if response.lower() != 'y':
            print("❌ 已取消處理")
            sys.exit(0)
    except KeyboardInterrupt:
        print(f"\n❌ 已取消處理")
        sys.exit(0)
    
    # 執行完整流程
    success = processor.run_complete_process()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main() 