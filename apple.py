from secedgar import filings, FilingType
from datetime import datetime
from pathlib import Path
import pandas as pd
import time

companies = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "GOOG", "META", "BRK.B", "AVGO", "TSLA",
             "JPM", "V", "LLY", "MA", "XOM", "COST", "UNH", "NFLX", "WMT", "PG", "JNJ"]

# 所有公司都嘗試抓取的財報類型（包括13F-HR）
filing_types = ["10-K", "10-Q", "8-K", "4", "13F-HR"]

FILING_TYPE_MAP = {
    "10-K": FilingType.FILING_10K,
    "10-Q": FilingType.FILING_10Q,
    "8-K": FilingType.FILING_8K,
    "4": FilingType.FILING_4,
    "13F-HR": FilingType.FILING_13FHR
}

USER_AGENT = "JIA-JYUN SHIH (shihjiajyun@gmail.com)"
START_DATE = datetime(2015, 6, 16)
END_DATE = datetime(2025, 6, 16)
base_dir = Path("./downloads")
base_dir.mkdir(parents=True, exist_ok=True)

for symbol in companies:
    print(f"\n🏢 Processing company: {symbol}")
    
    for ftype in filing_types:
        try:
            print(f"   📥 Downloading {ftype} for {symbol}...")
            filing = filings(
                cik_lookup=symbol,
                filing_type=FILING_TYPE_MAP[ftype],
                start_date=START_DATE,
                end_date=END_DATE,
                user_agent=USER_AGENT
            )
            # 直接使用base_dir，讓secedgar自動組織目錄結構
            filing.save(base_dir)
            time.sleep(0.5)
            print(f"   ✅ {ftype} downloaded successfully")
        except Exception as e:
            if ftype == "13F-HR":
                print(f"   ⚠️  {symbol} 沒有 {ftype} 財報（非機構投資者）")
            else:
                print(f"   ❌ Error for {symbol} - {ftype}: {e}")
