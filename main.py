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

def get_market_phase(now, is_manual=False):
    """判定階段：手動觸發優先進入實戰模式"""
    if is_manual:
        return ("🎯 手動實戰演習", "啟動最高規格即時交易指令格式。")
    
    # 轉成分鐘數進行區間判定 (增加容錯)
    mm = now.hour * 60 + now.minute
    
    # 夏令時間判定 (澳門 21:00 = 1260分鐘)
    if 1260 <= mm < 1285:   return ("🚨 T-30 策略部署", "關注 arXiv 科研源頭與總經背景。")
    elif 1285 <= mm < 1290: return ("🎯 T-5 狙擊模式", "監控盤前跳空 (Gap) 與極端情緒。")
    elif 1290 <= mm <= 1292: return ("⚡ T+0 子彈時間", "分析瞬時量能，判斷算法觸發點。")
    elif 1293 <= mm < 1310: return ("🏁 T+3 收穫驗證", "區分真假突破，驗證邏輯鏈。")
    else:
        return ("🔍 例行市場掃描", "掃描產業趨勢與技術進展。")

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

    # 1. 時間與觸發模式判定
    tz_macau = timezone(timedelta(hours=8))
    now = datetime.now(tz_macau)
    current_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # 偵測是否為手動執行
    is_manual = os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch"
    phase_name, phase_desc = get_market_phase(now, is_manual)
    
    # 2. 抓取數據
    arxiv = fetch_rss("https://rss.arxiv.org/rss/cs.AI")
    hacker_news = fetch_rss("https://news.ycombinator.com/rss")
    market_news = fetch_rss("https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147")
    all_titles = "\n".join(arxiv + hacker_news + market_news)

    # 3. 去重機制 (手動執行或實戰時段跳過)
    current_hash = hashlib.md5(all_titles.encode('utf-8')).hexdigest()
    hash_file = "last_news_hash.txt"
    if not is_manual and "例行" in phase_name and os.path.exists(hash_file):
        with open(hash_file, "r") as f:
            if f.read() == current_hash: return
    with open(hash_file, "w") as f: f.write(current_hash)

    # 4. 股價獲取
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

    # 5. 核心 Prompt 分流 (修正原本代碼的語法錯誤)
    if "例行" in phase_name:
        prompt = f"""
        現在是【{phase_name}】。任務：{phase_desc}
        請以首席分析師身份產出「產業趨勢掃描」報告。
        數據：{market_data}
        新聞：{all_titles}
        (格式要求：重磅警報、標對照、深度解析、操作指南)
        產出時間：{current_time_str} (澳門時間)
        """
    else:
        prompt = f"""
        【重要指令：現在是 {phase_name} 關鍵時段】
        你現在是對沖基金交易主管。請立即產出極具「超短線賺錢指令感」的戰報。
        
        數據：{market_data}
        資訊：{all_titles}

        請嚴格執行以下【實戰咭片格式】，禁止任何廢話：
        
        🚨 【{phase_name}：戰術大腦】
        (一句話鎖定當前定價錯誤與套利機會)

        🔥 【超短線：即時交易指令】
        ━━━━━━━━━━━━━━━━
        💰 標的：[Ticker] (現價: $XXX)
        ├─ 🚦 策略：【 🟢 強力買入 / 🔴 立即做空 】
        ├─ ⚡ 亞微秒信心值：[ 90%以上 ]
        ├─ 🎯 目標點位：
        │  🚀 最佳進場：$XXX.XX
        │  💰 止盈：$XXX.XX
        │  🛑 止損：$XXX.XX
        └─ 💡 賺錢邏輯：(為什麼這個點位能賺錢？)
        ━━━━━━━━━━━━━━━━
        (請列出 3-5 個標的)

        ⚡ 【亞微秒級推文】
        (充滿金錢感與技術硬核感的短文)

        🏁 【最終執行清單】
        (1. 必須鎖定 2. 避開陷阱 3. 預備觸發點)

        ---
        🔗 來源: arXiv, HN, CNBC | 產出時間：{current_time_str}
        """

    # 6. 生成與發送
    try:
        response = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
        if response.text:
            send_telegram(response.text)
            os.makedirs("build", exist_ok=True)
            with open("build/latest_data.json", "w", encoding="utf-8") as f:
                json.dump({
                    "time": current_time_str, 
                    "phase": phase_name, 
                    "report": response.text, 
                    "stocks": stock_dict
                }, f, ensure_ascii=False, indent=2)
    except Exception as e: print(f"Error: {e}")

if __name__ == "__main__":
    main()
