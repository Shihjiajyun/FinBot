import requests
from bs4 import BeautifulSoup

def fetch_macrotrends_table(ticker, page_slug, max_years=5):
    url = f"https://www.macrotrends.net/stocks/charts/{ticker}/alphabet/{page_slug}"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    
    table = soup.find("table", class_="historical_data_table")
    rows = table.find_all("tr")

    data = {}
    for row in rows[1:]:
        cols = row.find_all("td")
        if len(cols) >= 2:
            year = cols[0].text.strip()
            value = cols[1].text.strip().replace("$", "").replace(",", "").replace("B", "")
            try:
                if year.isdigit():
                    data[int(year)] = float(value) * 1000  # 十億 → 百萬
            except:
                continue

    # 僅保留最近 N 年資料
    return {year: data[year] for year in sorted(data.keys(), reverse=True)[:max_years]}

def print_cleaned(label, data):
    print(f"\n📘 {label}:")
    for year in sorted(data.keys(), reverse=True):
        print(f"  {year}: {data[year]:,.0f}")

if __name__ == "__main__":
    ticker = "GOOGL"

    free_cash_flow = fetch_macrotrends_table(ticker, "free-cash-flow")
    cash_flow_investing = fetch_macrotrends_table(ticker, "cash-flow-from-investing-activities")
    cash_flow_financing = fetch_macrotrends_table(ticker, "cash-flow-from-financial-activities")
    cash_and_cash_equivalents = fetch_macrotrends_table(ticker, "cash-on-hand")

    print_cleaned("Free Cash Flow", free_cash_flow)
    print_cleaned("Cash Flow from Investing", cash_flow_investing)
    print_cleaned("Cash Flow from Financing", cash_flow_financing)
    print_cleaned("Cash & Cash Equivalents", cash_and_cash_equivalents)
