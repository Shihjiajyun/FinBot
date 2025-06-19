import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

def get_macrotrends_table(symbol, metric_name):
    url = f"https://www.macrotrends.net/stocks/charts/{symbol}/apple/{metric_name}"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"❌ 請求失敗：{metric_name}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    tables = soup.find_all("table", class_="historical_data_table")

    if not tables:
        print(f"❌ 沒有找到表格：{metric_name}")
        return None

    table = tables[0]
    rows = table.find_all("tr")
    data = []
    for row in rows[1:]:  # skip header
        cols = row.find_all("td")
        if len(cols) >= 2:
            year = cols[0].text.strip()
            value = cols[1].text.strip().replace("$", "").replace(",", "").replace("B", "")
            try:
                data.append((year, float(value)))
            except ValueError:
                continue

    df = pd.DataFrame(data, columns=["Year", metric_name])
    df["Year"] = df["Year"].astype(str)
    return df.set_index("Year")

# 🟡 移除 COGS，之後用 Revenue - Gross Profit 計算
metrics = {
    "Revenue": "revenue",
    "Gross Profit": "gross-profit",
    "Operating Expenses": "operating-expenses",
    "Operating Income": "operating-income",
    "Income Before Taxes": "pre-tax-income",
    "Net Income": "net-income",
    "EPS Basic": "eps-earnings-per-share-diluted",
    "Outstanding Shares": "shares-outstanding"
}

# 合併所有資料
all_data = None
symbol = "AAPL"

for name, metric in metrics.items():
    df = get_macrotrends_table(symbol, metric)
    if df is not None:
        df.columns = [name]
        if all_data is None:
            all_data = df
        else:
            all_data = all_data.join(df, how='outer')
    time.sleep(1)  # 防止請求過快被封鎖

# 🔁 自動計算 COGS
if "Revenue" in all_data.columns and "Gross Profit" in all_data.columns:
    all_data["COGS (calculated)"] = all_data["Revenue"] - all_data["Gross Profit"]

# 🎯 重新排序欄位（可選）
ordered_columns = [
    "Revenue", "COGS (calculated)", "Gross Profit",
    "Operating Expenses", "Operating Income",
    "Income Before Taxes", "Net Income",
    "EPS Basic", "Outstanding Shares"
]
all_data = all_data[ordered_columns]

# 顯示最終結果
if all_data is not None:
    all_data = all_data.sort_index(ascending=False)
    pd.set_option('display.float_format', '{:,.2f}'.format)
    print(all_data)
