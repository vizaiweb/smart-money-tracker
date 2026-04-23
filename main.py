import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
import time
import hashlib
import json
from datetime import datetime, timedelta, timezone
import urllib.parse
import yfinance as yf
from google.genai import Client

def get_market_phase(now):
    hm = now.strftime("%H:%M")
    phases = {
        "21:00": ("🚨 T-30 策略部署", "關注 arXiv 科研源頭與總經背景。"),
        "21:25": ("🎯 T-5 狙擊模式", "監控盤前跳空 (Gap) 與極端情緒。"),
        "21:30": ("⚡ T+0 子彈時間", "分析瞬時成交量，判斷算法觸發點。"),
        "21:33": ("🏁 T+3 收穫驗證", "區分真假突破，驗證邏輯鏈真實性。")
    }
    return phases.get(hm, ("🔍 例行市場掃描", "掃描產業趨勢與技術進展。"))

def fetch_rss(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            root = ET.fromstring(response.read())
        return [item.find('title').text for item in root.findall('.//item')[:10]]
    except: return []

def send_telegram(text):
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id: return
    clean_text = text.replace("**", "")
    params = urllib.parse.urlencode({"chat_id": chat_id, "text": clean_text})
    url = f"https://api.telegram.org/bot{token}/sendMessage?{params}"
    try: urllib.request.urlopen(url, timeout=15)
    except: print("Telegram 發送失敗")

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key: sys.exit(1)
    client = Client(api_key=api_key)

    tz_macau = timezone(timedelta(hours=8))
    now = datetime.now(tz_macau)
    phase_name, phase_desc = get_market_phase(now)
    
    arxiv = fetch_rss("https://rss.arxiv.org/rss/cs.AI")
    hacker_news = fetch_rss("https://news.ycombinator.com/rss")
    market_news = fetch_rss("https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147")
    all_titles = "\n".join(arxiv + hacker_news + market_news)

    # 關鍵時段跳過 Hash 去重
    current_hash = hashlib.md5(all_titles.encode('utf-8')).hexdigest()
    hash_file = "last_news_hash.txt"
    if phase_name == "🔍 例行市場掃描" and os.path.exists(hash_file):
        with open(hash_file, "r") as f:
            if f.read() == current_hash: return
    with open(hash_file, "w") as f: f.write(current_hash)

    # 股價與分析
    tickers = ["NVDA", "TSLA", "PLTR", "QBTS", "IONQ"]
    market_data = ""
    stock_dict = {}
    for t in tickers:
        try:
            s = yf.Ticker(t).fast_info
            price = round(s['last_price'], 2)
            market_data += f"- {t}: ${price}\n"
            stock_dict[t] = price
        except: continue

    prompt = f"""
    現在是【{phase_name}】階段。任務目標：{phase_desc}
    
    你現在是頂尖對沖基金的「極短線戰術指揮官」。請針對以下數據，產出極具投資賺錢導向的「買入賣出戰報」。
    
    【即時股價】: {real_market_text}
    【底層資訊】: {all_titles}

    請絕對禁止使用表格，嚴格執行以下「極速咭片格式」排版：

    🚨 【{phase_name}：亞微秒戰術大腦】
    (用三句話鎖定當前最強的獲利邏輯：例如技術套利、消息偏差或資金情緒擠壓。)

    🔥 【超短線：即時交易指令】
    ━━━━━━━━━━━━━━━━
    💰 標的：[Ticker] (現價: $XXX)
    ├─ 🚦 行動：【 🟢 強力買入 / 🔴 立即拋售 / 🟡 盤整伏擊 】
    ├─ ⚡ 亞微秒信心值：[ 90% - 邏輯已驗證 ]
    ├─ 🎯 目標操作：
    │  🚀 進場位：$XXX.XX (精確位點)
    │  💰 止盈點：$XXX.XX (+X% 獲利空間)
    │  🛑 止損線：$XXX.XX (嚴格執行)
    └─ 💡 獲利邏輯：(一句話說明為何能賺錢，例如：高層跳槽利好尚未出盡、開盤量能異動預判。)
    ━━━━━━━━━━━━━━━━
    (請列出 3-5 個最具爆發力的標的)

    🧠 【產業降維打擊：深度推演】
    (分析 AI 神經符號技術或總經政策如何造成當前的「定價錯誤」。)

    ⚡ 【亞微秒推文：極速傳播版】
    (撰寫一段極具煽動性、充滿金錢味道與技術硬核感的短文，吸引市場資金跟風。)

    🏁 【最終戰術清單】
    (1. 必須執行的動作 2. 絕對避開的陷阱 3. 觀察中的觸發點)

    ---
    🔗 來源: arXiv, HN, CNBC | 產出時間：{current_time_str}
    """

    try:
        response = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
        if response.text:
            send_telegram(response.text)
            # 產出網頁 JSON
            os.makedirs("build", exist_ok=True)
            with open("build/latest_data.json", "w", encoding="utf-8") as f:
                json.dump({"time": now.strftime("%Y-%m-%d %H:%M:%S"), "phase": phase_name, "report": response.text, "stocks": stock_dict}, f, ensure_ascii=False, indent=2)
    except Exception as e: print(f"Error: {e}")

if __name__ == "__main__":
    main()
