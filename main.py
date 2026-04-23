Import os
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
    # 移除 ** 避免 Telegram 解析錯誤，保持純文字美感
    clean_text = text.replace("**", "")
    params = urllib.parse.urlencode({"chat_id": chat_id, "text": clean_text})
    url = f"https://api.telegram.org/bot{token}/sendMessage?{params}"
    try:
        urllib.request.urlopen(url, timeout=15)
        print("📲 報告已發送！")
    except:
        print("❌ 發送失敗")

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key: sys.exit(1)
    client = Client(api_key=api_key)

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fed = fetch_rss_data("Fed", "https://www.federalreserve.gov/feeds/press_all.xml")
    cnbc = fetch_rss_data("CNBC", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147")
    yahoo = fetch_rss_data("Yahoo", "https://finance.yahoo.com/news/rssindex")
    all_titles = "\n".join(fed + cnbc + yahoo)
    
    # 提取 Ticker
    ticker_list = ["NVDA", "TSLA", "PLTR"]
    try:
        res = client.models.generate_content(model='gemini-flash-latest', contents=f"從新聞提取5個美股代號，僅回傳代號用逗號隔開: {all_titles}")
        ticker_list = [t.strip().upper() for t in res.text.split(",") if 1 < len(t.strip()) < 6][:5]
    except: pass

    real_market_data = get_stock_details(ticker_list)

    # 🚨 這裡就是你要的卡片結構 Prompt 鎖定
    prompt = f"""
    你現在是首席分析師。請結合以下數據產出繁體中文報告。
    【現價數據】: {real_market_data}
    【新聞摘要】: {all_titles}

    請「絕對禁止」使用表格，請完全依照以下格式排版：

    🚨 【重磅警報：總經動態】
    (分析內容...)

    ✨ 【今日實戰標的對照】
    ━━━━━━━━━━━━━━━━
    💰 股票代號 Ticker (參考現價: $XXX)
    ├─ 🚦 影響：🟢 看多 / 🔴 看空 / 🟡 觀望
    ├─ 📢 事實：(一句話新聞核心)
    ├─ 📈 操作建議：(結合現價，給出建議買入位、止盈位與止損位)
    └─ 💡 理由：(白話投資邏輯)
    ━━━━━━━━━━━━━━━━
    (請列出 3-5 個，重複上方格式)

    🧠 【深度解析：產業趨勢】
    (觀察點/事實紀錄/產業聯想/邏輯推演)

    🏁 【最終操作指南】
    (建議行動/觀察名單)

    產出時間：{current_time}
    """

    for i in range(3):
        try:
            print(f"🤖 AI 分析中 (嘗試 {i+1})...")
            response = client.models.generate_content(model='gemini-flash-latest', contents=prompt)
            if response.text:
                send_telegram_msg(response.text)
                break
        except Exception as e:
            time.sleep(30 if "429" in str(e) else 10)

if __name__ == "__main__":
    main()
