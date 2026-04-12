import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
import time
from datetime import datetime
import urllib.parse
import yfinance as yf
from google import genai

def fetch_rss_data(source_name, url):
    """抓取 RSS 數據"""
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
    """抓取多個標的的即時財務數據"""
    stock_info_text = ""
    for symbol in tickers:
        try:
            print(f"📊 正在獲取 {symbol} 的即時數據...")
            s = yf.Ticker(symbol)
            fast = s.fast_info
            price = round(fast['last_price'], 2)
            change = round(fast['year_to_date_change'] * 100, 2) if 'year_to_date_change' in fast else "N/A"
            high_52 = round(fast['year_high'], 2)
            low_52 = round(fast['year_low'], 2)
            stock_info_text += f"- {symbol}: 現價 ${price}, YTD漲幅 {change}%, 52週高/低: ${high_52}/${low_52}\n"
        except:
            continue
    return stock_info_text

def send_telegram_msg(text):
    """發送到 Telegram"""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id: return

    clean_text = text.replace("**", "")
    if len(clean_text) > 4000: clean_text = clean_text[:4000] + "..."
    
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
    client = genai.Client(api_key=api_key)

    # 1. 第一階段：抓取新聞並讓 AI 提取關鍵 Ticker
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fed_titles = fetch_rss_data("Fed", "https://www.federalreserve.gov/feeds/press_all.xml")
    cnbc_titles = fetch_rss_data("CNBC", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147")
    yahoo_titles = fetch_rss_data("Yahoo", "https://finance.yahoo.com/news/rssindex")
    
    all_titles = "\n".join(fed_titles + cnbc_titles + yahoo_titles)
    
    # 讓 AI 從新聞中選出 5 個最重要的美股代號
    extract_prompt = f"請從以下新聞標題中，找出最受關注的 5 個美股個股代號(Ticker)，僅回傳代號並用逗號隔開，例如: AAPL,TSLA,NVDA:\n{all_titles}"
    try:
        res = client.models.generate_content(model='gemini-flash-latest', contents=extract_prompt)
        ticker_list = [t.strip().upper() for t in res.text.split(",") if len(t.strip()) < 6][:5]
    except:
        ticker_list = ["SPY", "QQQ"] # 備案

    # 2. 第二階段：抓取這些 Ticker 的真實股價
    real_market_data = get_stock_details(ticker_list)

    # 3. 第三階段：生成終極嚴謹報告
    final_prompt = f"""
    你現在是資深量化分析師。請結合「最新新聞」與「真實市價數據」產出報告。
    
    【當前真實市場數據】：
    {real_market_data}
    
    【最新新聞摘要】：
    {all_titles}
    
    【報告規範】：
    1. 🚨 【重磅警報】：分析 Fed 動態。
    2. ✨ 【今日實戰標的】：
       - 必須包含參考數據中的代號。
       - 📈 建議價位：必須基於提供的「現價」來給出合理的支撐位(Support)與壓力位(Resistance)。
       - 嚴禁提到與現價脫節的歷史價格。
    3. 🧠 【深度解析】：結合數據分析趨勢。
    4. 🏁 【最終指南】。
    
    產出時間：{current_time} (請確保邏輯符合此時間點)
    請用繁體中文。
    """

    for i in range(3):
        try:
            print(f"🤖 AI 嚴謹分析中 (模型: gemini-flash-latest)...")
            response = client.models.generate_content(model='gemini-flash-latest', contents=final_prompt)
            if response.text:
                send_telegram_msg(response.text)
                break
        except Exception as e:
            print(f"⚠️ 失敗: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()
