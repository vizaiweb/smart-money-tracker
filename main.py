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
from google.genai import Client, types

# --- 科技狩獵設定 ---
HOT_KEYWORDS = ['Ising', 'Quantum', 'Superconductor', 'Photonics', 'CPO', 'Nuclear', 'Fusion', 'LLM Architecture']

def get_market_phase(now, is_manual=False):
    hm = now.strftime("%H:%M")
    phases = {
        "21:00": ("🚨 T-30 策略部署", "關注 arXiv 科研源頭與總經背景。"),
        "21:25": ("🎯 T-5 狙擊模式", "監控盤前跳空與情緒。"),
        "21:30": ("⚡ T+0 子彈時間", "分析瞬時量能。"),
        "21:33": ("🏁 T+3 收穫驗證", "驗證邏輯真實性。")
    }
    if is_manual: return ("🎯 手動實戰演習", "啟動即時戰報格式。")
    if hm in phases: return phases[hm]
    # 盤中時段判定 (21:00 - 04:00)
    if now.hour >= 21 or now.hour < 4:
        return ("🔥 盤中實戰監控", "即時追蹤資金流向。")
    return ("🔍 例行市場掃描", "掃描產業趨勢與技術進展。")

def fetch_rss_data(source_name, url):
    print(f"📡 正在抓取 {source_name}...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
        return [item.find('title').text for item in root.findall('.//item')[:10]]
    except: return []

def get_stock_details(tickers):
    stock_info_text = ""
    stock_dict = {}
    for symbol in tickers:
        try:
            s = yf.Ticker(symbol)
            price = round(s.fast_info['last_price'], 2)
            stock_info_text += f"- {symbol}: 現價 ${price}\n"
            stock_dict[symbol] = price
        except: continue
    return stock_info_text, stock_dict

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
    except: print("❌ Telegram 發送失敗")

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key: sys.exit(1)
    client = Client(api_key=api_key)

    # 確保部署目錄存在
    os.makedirs("build", exist_ok=True)

    tz_macau = timezone(timedelta(hours=8))
    now = datetime.now(tz_macau)
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")
    
    is_manual = os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch"
    phase_name, phase_desc = get_market_phase(now, is_manual)
    use_battle_format = "例行" not in phase_name

    # 1. 抓取數據
    arxiv = fetch_rss_data("arXiv", "https://rss.arxiv.org/rss/cs.AI")
    hacker_news = fetch_rss_data("HackerNews", "https://news.ycombinator.com/rss")
    market_news = fetch_rss_data("CNBC", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147")
    all_titles = "\n".join(arxiv + hacker_news + market_news)

    # 2. 去重 (僅限例行模式)
    current_hash = hashlib.md5(all_titles.encode('utf-8')).hexdigest()
    hash_file = "last_news_hash.txt"
    if not use_battle_format and os.path.exists(hash_file):
        with open(hash_file, "r") as f:
            if f.read() == current_hash:
                print("😴 內容重複，跳過。")
                return
    with open(hash_file, "w") as f: f.write(current_hash)

    # 3. 獲取股價
    ticker_list = ["NVDA", "TSLA", "PLTR", "AAPL", "AAL", "WBD", "LULU"]
    real_market_data, stock_dict = get_stock_details(ticker_list)

    # 4. Prompt 設定
    if not use_battle_format:
        prompt = f"現在是【{phase_name}】。任務：{phase_desc}\n行情：{real_market_data}\n新聞：{all_titles}\n請產出深度產業掃描報告，包含重磅警報、實戰標的、深度解析。"
    else:
        prompt = f"""
        現在是【{phase_name}】。你是交易主管，產出超短線指令。
        行情：{real_market_data}
        資訊：{all_titles}
        格式要求：
        🚨 【{phase_name}：戰鬥邏輯】
        🔥 【超短線：即時交易指令】
        ━━━━━━━━━━━━━━━━
        💰 標的：Ticker (現價: $XXX)
        ├─ 🚦 策略：【 🟢 強力買入 / 🔴 立即做空 / 🟡 觀望 】
        ├─ ⚡ 亞微秒信心值：95%
        ├─ 🎯 目標點位：🚀進場 $X / 💰止盈 $X / 🛑止損 $X
        └─ 💡 賺錢邏輯：簡述理由
        ━━━━━━━━━━━━━━━━
        (列出 3-5 個)
        🏁 【最終執行清單】
        產出時間：{current_time}
        """

    # 5. AI 生成 (加入安全設定避免拒答)
    safety = [types.SafetySetting(category=c, threshold="BLOCK_NONE") for c in ["HATE_SPEECH", "HARASSMENT", "DANGEROUS_CONTENT", "SEXUALLY_EXPLICIT"]]
    
    for i in range(3):
        try:
            print(f"🤖 AI 分析中 (嘗試 {i+1})...")
            # 使用更穩定的模型名稱
            response = client.models.generate_content(
                model='gemini-2.0-flash', 
                contents=prompt,
                config=types.GenerateContentConfig(safety_settings=safety)
            )
            if response.text:
                full_report = response.text
                send_telegram_msg(full_report)
                # 寫入 JSON 供網頁讀取
                with open("build/latest_data.json", "w", encoding="utf-8") as f:
                    json.dump({"time": current_time, "phase": phase_name, "report": full_report, "stocks": stock_dict}, f, ensure_ascii=False)
                break
        except Exception as e:
            print(f"❌ 錯誤: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
