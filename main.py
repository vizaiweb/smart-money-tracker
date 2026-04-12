import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
import time
from datetime import datetime
import urllib.parse
import yfinance as yf
# --- 關鍵修正：避開命名空間衝突 ---
from google.genai import Client

def fetch_rss_data(source_name, url):
    print(f"📡 正在抓取 {source_name}...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
        items = [item.find('title').text for item in root.findall('.//item')[:8]]
        return items
    except:
        return []

def get_stock_details(tickers):
    stock_info_text = ""
    for symbol in tickers:
        try:
            print(f"📊 正在獲取 {symbol} 的即時數據...")
            s = yf.Ticker(symbol)
            fast = s.fast_info
            price = round(fast['last_price'], 2)
            stock_info_text += f"- {symbol}: 現價 ${price}\n"
        except:
            continue
    return stock_info_text

def send_telegram_msg(text):
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id: return
    clean_text = text.replace("**", "")
    params = urllib.parse.urlencode({"chat_id": chat_id, "text": clean_text})
    url = f"https://api.telegram.org/bot{token}/sendMessage?{params}"
    try:
        urllib.request.urlopen(url, timeout=15)
        print("📲 嚴謹版報告已發送！")
    except:
        print("❌ 推送失敗")

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key: sys.exit(1)
    
    # --- 初始化修正 ---
    client = Client(api_key=api_key)

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fed_titles = fetch_rss_data("Fed", "https://www.federalreserve.gov/feeds/press_all.xml")
    cnbc_titles = fetch_rss_data("CNBC", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147")
    yahoo_titles = fetch_rss_data("Yahoo", "https://finance.yahoo.com/news/rssindex")
    all_titles = "\n".join(fed_titles + cnbc_titles + yahoo_titles)
    
    # 提取 Ticker
    extract_prompt = f"從新聞標題提取 5 個美股代號，僅回傳代號用逗號隔開: {all_titles}"
    try:
        res = client.models.generate_content(model='gemini-flash-latest', contents=extract_prompt)
        ticker_list = [t.strip().upper() for t in res.text.split(",") if len(t.strip()) < 6][:5]
    except:
        ticker_list = ["PLTR", "NVDA", "TSLA"]

    real_market_data = get_stock_details(ticker_list)

    final_prompt = f"""
    你現在是首席分析師。請結合數據產出嚴謹報告。
    現價數據：{real_market_data}
    新聞摘要：{all_titles}
    請包含：🚨重磅警報、✨實戰標的(含支撐壓力價位)、🧠深度解析、🏁最終指南。
    時間：{current_time}
    """

    try:
        response = client.models.generate_content(model='gemini-flash-latest', contents=final_prompt)
        if response.text:
            send_telegram_msg(response.text)
    except Exception as e:
        print(f"❌ 最終生成失敗: {e}")

if __name__ == "__main__":
    main()
