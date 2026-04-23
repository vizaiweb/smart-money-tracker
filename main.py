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
    hm = now.strftime("%H:%M")
    
    # 戰鬥時段字典
    phases = {
        "21:00": ("🚨 T-30 策略部署", "關注 arXiv 科研源頭與總經背景。"),
        "21:25": ("🎯 T-5 狙擊模式", "監控盤前跳空 (Gap) 與極端情緒。"),
        "21:30": ("⚡ T+0 子彈時間", "分析瞬時量能，判斷算法觸發點。"),
        "21:33": ("🏁 T+3 收穫驗證", "區分真假突破，驗證邏輯鏈。")
    }
    
    # 1. 如果是手動執行，優先給予實戰模式
    if is_manual:
        return ("🎯 手動實戰演習", "啟動即時指令格式。")
    
    # 2. 如果剛好在戰鬥分鐘內
    if hm in phases:
        return phases[hm]
        
    # 3. 預設：例行掃描
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
    clean_text = text.replace("**", "") # 移除粗體，避免 TG 解析錯誤
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
    current_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    is_manual = os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch"
    phase_name, phase_desc = get_market_phase(now, is_manual)
    
    # 判定是否使用「戰鬥格式」（只要不是例行掃描，或者手動執行，就用戰鬥格式）
    use_battle_format = "例行" not in phase_name or is_manual

    arxiv = fetch_rss("https://rss.arxiv.org/rss/cs.AI")
    hacker_news = fetch_rss("https://news.ycombinator.com/rss")
    market_news = fetch_rss("https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147")
    all_titles = "\n".join(arxiv + hacker_news + market_news)

    # 去重機制
    current_hash = hashlib.md5(all_titles.encode('utf-8')).hexdigest()
    hash_file = "last_news_hash.txt"
    if not use_battle_format and os.path.exists(hash_file):
        with open(hash_file, "r") as f:
            if f.read() == current_hash: return
    with open(hash_file, "w") as f: f.write(current_hash)

    # 獲取熱門標的股價
    tickers = ["NVDA", "TSLA", "PLTR", "QBTS", "IONQ", "AAPL", "LULU", "WBD", "AAL"]
    market_data = ""
    stock_dict = {}
    for t in tickers:
        try:
            s = yf.Ticker(t).fast_info
            price = round(s['last_price'], 2)
            market_data += f"- {t}: ${price}\n"
            stock_dict[t] = price
        except: continue

    if not use_battle_format:
        # --- 模式 A：例行分析 ---
        prompt = f"""
        現在是【{phase_name}】。任務：{phase_desc}
        請以首席分析師身份產出「深度產業趨勢掃描」報告。
        行情：{market_data}
        資訊源：{all_titles}
        報告必須包含：🚨 重磅警報、✨ 今日實戰標的、🧠 深度解析、🏁 最終操作指南。
        """
    else:
        # --- 模式 B：實戰指令 (咭片格式) ---
        prompt = f"""
        現在是【{phase_name}】。你是對沖基金交易主管，請立即產出「超短線交易指令」。
        即時行情：{market_data}
        最新資訊：{all_titles}

        請嚴格遵守以下格式，嚴禁省略符號：

        🚨 【{phase_name}：戰鬥邏輯】
        (一句話直擊當前獲利核心)

        🔥 【超短線：即時交易指令】
        ━━━━━━━━━━━━━━━━
        💰 標的：[Ticker] (現價: $XXX)
        ├─ 🚦 策略：【 🟢 強力買入 / 🔴 立即做空 / 🟡 觀望 】
        ├─ ⚡ 亞微秒信心值：[ 90%以上 ]
        ├─ 🎯 目標點位：
        │  🚀 最佳進場：$XXX.XX
        │  💰 止盈目標：$XXX.XX
        │  🛑 嚴格止損：$XXX.XX
        └─ 💡 賺錢邏輯：(解釋點位背後的消息或技術面偏差)
        ━━━━━━━━━━━━━━━━
        (請列出 3-5 個最具爆發力標的)

        ⚡ 【亞微秒級推文】
        (金錢味道十足的市場喊單短文)

        🏁 【最終執行清單】
        (精簡的 Action Items)

        產出時間：{current_time_str} (澳門時間)
        """

    try:
        response = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
        if response.text:
            full_report = response.text
            send_telegram(full_report)
            os.makedirs("build", exist_ok=True)
            with open("build/latest_data.json", "w", encoding="utf-8") as f:
                json.dump({"time": current_time_str, "phase": phase_name, "report": full_report, "stocks": stock_dict}, f, ensure_ascii=False, indent=2)
    except Exception as e: print(f"Error: {e}")

if __name__ == "__main__":
    main()
