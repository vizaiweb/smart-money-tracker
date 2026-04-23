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

# --- 科技狩獵設定 ---
HOT_KEYWORDS = ['Ising', 'Quantum', 'Lean 4', 'Neuro-Symbolic', 'CPO', 'Sub-microsecond', 'Photonics']

def get_market_phase(now):
    """判定目前處於美股開盤的關鍵時刻 (澳門時間)"""
    hm = now.strftime("%H:%M")
    phases = {
        "21:00": ("🚨 T-30 策略部署", "關注 arXiv 科研源頭與總經背景，鎖定技術邏輯。"),
        "21:25": ("🎯 T-5 狙擊模式", "監控盤前跳空 (Gap) 與極端情緒，尋找邏輯偏差。"),
        "21:30": ("⚡ T+0 子彈時間", "瞬時成交量分析，判斷算法是否觸發形式驗證。"),
        "21:33": ("🏁 T+3 收穫驗證", "邏輯鏈真實性驗證，區分市場誘多與技術突破。")
    }
    return phases.get(hm, ("🔍 例行市場掃描", "掃描產業長期趨勢與亞微秒技術進展。"))

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
    stock_dict = {}
    for symbol in tickers:
        try:
            s = yf.Ticker(symbol)
            price = round(s.fast_info['last_price'], 2)
            stock_info_text += f"- {symbol}: 現價 ${price}\n"
            stock_dict[symbol] = price
        except:
            continue
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
    except:
        print("❌ 發送失敗")

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key: sys.exit(1)
    client = Client(api_key=api_key)

    # 1. 時間與階段判定
    tz_macau = timezone(timedelta(hours=8))
    now = datetime.now(tz_macau)
    current_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    phase_name, phase_desc = get_market_phase(now)
    
    # 2. 數據抓取
    arxiv = fetch_rss_data("arXiv", "https://rss.arxiv.org/rss/cs.AI")
    hacker_news = fetch_rss_data("HackerNews", "https://news.ycombinator.com/rss")
    market_news = fetch_rss_data("CNBC", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147")
    all_titles = "\n".join(arxiv + hacker_news + market_news)

    # 3. 去重機制 (衝刺時段跳過限制)
    current_hash = hashlib.md5(all_titles.encode('utf-8')).hexdigest()
    hash_file = "last_news_hash.txt"
    is_sprint = phase_name != "🔍 例行市場掃描" 
    
    if not is_sprint and os.path.exists(hash_file):
        with open(hash_file, "r") as f:
            if f.read() == current_hash:
                print("😴 內容相同且非衝刺時段，跳過。")
                return
    with open(hash_file, "w") as f:
        f.write(current_hash)

    # 4. Ticker 提取與股價
    ticker_list = ["NVDA", "TSLA", "PLTR", "QBTS", "IONQ"]
    try:
        res = client.models.generate_content(model='gemini-2.0-flash', 
                                            contents=f"從新聞提取5個美股代號: {all_titles}")
        ticker_list = [t.strip().upper() for t in res.text.split(",") if 1 < len(t.strip()) < 6][:5]
    except: pass
    real_market_text, real_market_dict = get_stock_details(ticker_list)

    # 5. 構建 Prompt
    source_reference = f"🔗 來源: arXiv({len(arxiv)}), HN({len(hacker_news)}), CNBC({len(market_news)})"
    
    prompt = f"""
    現在是【{phase_name}】階段。任務：{phase_desc}
    你現在是精通「神經符號 AI」與「亞微秒高頻交易」的首席分析師。
    
    【即時股價】: {real_market_text}
    【資訊摘要】: {all_titles}

    請完全依照以下格式產出繁體中文報告：

    🚨 【{phase_name}：邏輯核心】
    (分析內容...)

    ✨ 【今日實戰標的對照】
    ━━━━━━━━━━━━━━━━
    💰 Ticker (參考價: $XXX)
    ├─ 🚦 影響：🟢 看多 / 🔴 看空 / 🟡 觀望
    ├─ 📈 操作建議：(買入位/止盈/止損)
    └─ 💡 亞微秒理由：(技術聯結與邏輯推演)
    ━━━━━━━━━━━━━━━━
    (列出 3-5 個)

    ⚡ 【亞微秒級戰報：極短線推文】
    (撰寫一段具備爆發力的推文)

    🏁 【最終操作指南】
    (具體行動建議)

    ---
    {source_reference}
    產出時間：{current_time_str} (澳門時間)
    """

    # 6. 執行分析與數據持久化
    try:
        print(f"🤖 AI {phase_name} 分析中...")
        response = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
        if response.text:
            full_report = response.text
            send_telegram_msg(full_report)
            
            # 生成網頁數據檔案
            os.makedirs("build", exist_ok=True)
            with open("build/latest_data.json", "w", encoding="utf-8") as f:
                json.dump({
                    "time": current_time_str,
                    "phase": phase_name,
                    "report": full_report,
                    "stocks": real_market_dict
                }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"出錯: {e}")

if __name__ == "__main__":
    main()
