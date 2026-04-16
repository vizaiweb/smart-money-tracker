import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
import time
import hashlib
from datetime import datetime, timedelta, timezone
import urllib.parse
import yfinance as yf
from google.genai import Client

# --- 科技狩獵設定 ---
HOT_KEYWORDS = ['Ising', 'Quantum', 'Superconductor', 'Photonics', 'CPO', 'Nuclear', 'Fusion', 'LLM Architecture']

def fetch_rss_data(source_name, url):
    print(f"📡 正在抓取 {source_name}...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
        items = [item.find('title').text for item in root.findall('.//item')[:10]]
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

    # --- 修改：設定澳門時間 (UTC+8) ---
    tz_macau = timezone(timedelta(hours=8))
    current_time = datetime.now(tz_macau).strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. 切換為硬核來源：arXiv (AI/科技論文) + Hacker News (矽谷熱點) + CNBC
    tech_news = fetch_rss_data("arXiv", "https://rss.arxiv.org/rss/cs.AI")
    hacker_news = fetch_rss_data("HackerNews", "https://news.ycombinator.com/rss")
    market_news = fetch_rss_data("CNBC", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147")
    
    all_titles_list = tech_news + hacker_news + market_news
    all_titles = "\n".join(all_titles_list)

    if not all_titles.strip():
        print("📭 無新數據，停止執行。")
        return

    # 2. 去重機制：防止高頻執行時重複推送
    # 這裡使用簡單的 hash 比對，如果新聞內容與上次一致則跳過
    current_hash = hashlib.md5(all_titles.encode('utf-8')).hexdigest()
    hash_file = "last_news_hash.txt"
    if os.path.exists(hash_file):
        with open(hash_file, "r") as f:
            if f.read() == current_hash:
                print("😴 內容與上次相同，跳過發送。")
                return
    with open(hash_file, "w") as f:
        f.write(current_hash)

    # 3. 科技關鍵字偵測
    is_emergency = any(word.lower() in all_titles.lower() for word in HOT_KEYWORDS)
    alert_prefix = "🚨 【高能技術預警】偵測到底層技術突破！" if is_emergency else "🔍 【例行市場掃描】"

    # 4. 提取 Ticker (模型維持 gemini-flash-latest)
    ticker_list = ["NVDA", "TSLA", "PLTR"]
    try:
        res = client.models.generate_content(model='gemini-flash-latest', 
                                            contents=f"請從以下標題中提取 5 個最相關的美股代號，僅回傳代號用逗號隔開: {all_titles}")
        ticker_list = [t.strip().upper() for t in res.text.split(",") if 1 < len(t.strip()) < 6][:5]
    except: pass

    real_market_data = get_stock_details(ticker_list)

    # 5. 強化後的 Prompt (強調技術聯想)
    prompt = f"""
    {alert_prefix}
    你現在是精通硬核科技的首席分析師。請針對以下數據產出繁體中文報告。
    
    【現價數據】:
    {real_market_data}
    【新聞與科研摘要】:
    {all_titles}

    請特別留意標題中是否包含 {HOT_KEYWORDS} 等關鍵字。如果有，請深入推演其對底層供應鏈的影響。
    「絕對禁止」使用表格，請完全依照以下格式排版：

    🚨 【重磅警報：技術或總經動態】
    (如果是技術突破，請簡述其原理並指出誰會是第一個受益者)

    ✨ 【今日實戰標的對照】
    ━━━━━━━━━━━━━━━━
    💰 股票代號 Ticker (參考現價: $XXX)
    ├─ 🚦 影響：🟢 看多 / 🔴 看空 / 🟡 觀望
    ├─ 📢 事實：(一句話解釋技術或新聞核心)
    ├─ 📈 操作建議：(結合現價，給出買入位、止盈與止損)
    └─ 💡 理由：(白話投資邏輯，強調技術領先性)
    ━━━━━━━━━━━━━━━━
    (列出 3-5 個)

    🧠 【深度解析：產業趨勢】
    (📌 觀察點 / • 📝 事實 / • 🧪 產業聯想 / • ⚖️ 邏輯推演)

    🏁 【最終操作指南】
    (建議行動 / 核心觀察名單)

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
