import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
import time
from datetime import datetime
import urllib.parse
import yfinance as yf
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
            price = round(s.fast_info['last_price'], 2)
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
        print("📲 報告已發送！")
    except:
        print("❌ 推送失敗")

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key: sys.exit(1)
    client = Client(api_key=api_key)

    # 1. 抓取原始數據
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fed = fetch_rss_data("Fed", "https://www.federalreserve.gov/feeds/press_all.xml")
    cnbc = fetch_rss_data("CNBC", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147")
    yahoo = fetch_rss_data("Yahoo", "https://finance.yahoo.com/news/rssindex")
    all_titles = "\n".join(fed + cnbc + yahoo)
    
    # --- 強化區塊 A：提取 Ticker 並加入重試 ---
    ticker_list = ["NVDA", "TSLA", "PLTR"] # 預設值
    for i in range(3):
        try:
            print(f"🔍 正在識別標的 (嘗試 {i+1}/3)...")
            extract_res = client.models.generate_content(
                model='gemini-flash-latest', 
                contents=f"請從以下新聞標題中找出 5 個最相關的美股代號，僅回傳代號並用逗號隔開：\n{all_titles}"
            )
            if extract_res.text:
                ticker_list = [t.strip().upper() for t in extract_res.text.split(",") if 1 < len(t.strip()) < 6][:5]
                break
        except Exception as e:
            print(f"⏳ 提取失敗: {e}，休息 10 秒...")
            time.sleep(10)

    # 2. 獲取真實現價
    real_market_data = get_stock_details(ticker_list)

    # 3. 準備最終分析 Prompt
    prompt = f"""
你現在是華爾街頂尖首席投資官 (CIO)。請結合最新新聞與真實現價產出報告。
真實市價：{real_market_data}
新聞摘要：{all_titles}

排版規範：🚨重磅警報、✨實戰標的對照 (Ticker/影響/事實/📈操作建議/理由)、🧠深度解析、🏁最終指南。
產出時間：{current_time}，請用繁體中文。
"""

    # --- 強化區塊 B：生成最終報告並加入 429 處理 ---
    for i in range(3):
        try:
            print(f"🤖 AI 分析中 (嘗試 {i+1}/3)...")
            response = client.models.generate_content(model='gemini-flash-latest', contents=prompt)
            if response.text:
                send_telegram_msg(response.text)
                print("--- 報告預覽 ---")
                print(response.text)
                break
        except Exception as e:
            if "429" in str(e):
                print("⏳ 觸發 Quota 頻率限制，休息 30 秒後重試...")
                time.sleep(30) # 免費層級 429 建議休息久一點
            else:
                print(f"⚠️ 生成失敗: {e}")
                time.sleep(10)

if __name__ == "__main__":
    main()
