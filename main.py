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
    """
    判定當前市場階段：
    1. 手動執行 (workflow_dispatch) -> 強制進入實戰指令模式
    2. 特定時間點 -> 進入 T-30/T-5/T+0/T+3 模式
    3. 其他時間 -> 例行掃描模式
    """
    hm = now.strftime("%H:%M")
    
    # 精準戰鬥時段字典
    phases = {
        "21:00": ("🚨 T-30 策略部署", "關注 arXiv 科研源頭與總經背景。"),
        "21:25": ("🎯 T-5 狙擊模式", "監控盤前跳空 (Gap) 與極端情緒。"),
        "21:30": ("⚡ T+0 子彈時間", "分析瞬時量能，判斷算法觸發點。"),
        "21:33": ("🏁 T+3 收穫驗證", "區分真假突破，驗證邏輯鏈。")
    }
    
    # 1. 如果是手動執行，優先給予實戰模式
    if is_manual:
        return ("🎯 手動實戰演習", "啟動即時指令格式分析當前盤面。")
    
    # 2. 如果剛好在精準戰鬥分鐘內
    if hm in phases:
        return phases[hm]
    
    # 3. 判定是否處於美股開盤活躍時段 (澳門時間 21:00 - 04:00)
    # 如果在這個區間手動觸發，也給予實戰格式
    current_hour = now.hour
    if current_hour >= 21 or current_hour < 4:
        return ("🔥 盤中實戰監控", "即時追蹤資金流向與獲利機會。")
        
    # 4. 預設：例行掃描
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
    if not token or not chat_id: 
        print("Telegram Token 或 Chat ID 未設定")
        return
    
    # 移除 Markdown 粗體避免 TG 解析出錯，並確保編碼正確
    clean_text = text.replace("**", "")
    params = urllib.parse.urlencode({"chat_id": chat_id, "text": clean_text})
    url = f"https://api.telegram.org/bot{token}/sendMessage?{params}"
    try: 
        urllib.request.urlopen(url, timeout=15)
    except Exception as e: 
        print(f"Telegram 發送失敗: {e}")

def main():
    # 1. 初始化與環境檢查
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key: 
        print("缺少 GEMINI_API_KEY")
        sys.exit(1)
    
    client = Client(api_key=api_key)
    tz_macau = timezone(timedelta(hours=8))
    now = datetime.now(tz_macau)
    current_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # 確保 build 目錄存在，防止部署插件報錯
    os.makedirs("build", exist_ok=True)
    
    # 2. 判定模式
    is_manual = os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch"
    phase_name, phase_desc = get_market_phase(now, is_manual)
    
    # 只要標題不含「例行」，就啟動戰鬥指令格式
    use_battle_format = "例行" not in phase_name

    # 3. 獲取資訊源
    arxiv = fetch_rss("https://rss.arxiv.org/rss/cs.AI")
    hacker_news = fetch_rss("https://news.ycombinator.com/rss")
    market_news = fetch_rss("https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147")
    all_titles = "\n".join(arxiv + hacker_news + market_news)

    # 4. 去重機制 (僅針對例行掃描)
    current_hash = hashlib.md5(all_titles.encode('utf-8')).hexdigest()
    hash_file = "last_news_hash.txt"
    if not use_battle_format and os.path.exists(hash_file):
        with open(hash_file, "r") as f:
            if f.read() == current_hash:
                print("內容未變動，跳過發送以節省資源。")
                # 仍產出一個基本 JSON 確保部署不報錯
                with open("build/latest_data.json", "w", encoding="utf-8") as f:
                    json.dump({"time": current_time_str, "status": "no_change"}, f)
                return 
    
    with open(hash_file, "w") as f: 
        f.write(current_hash)

    # 5. 獲取實時股價
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

    # 6. 根據模式設定 Prompt
    if not use_battle_format:
        # --- 模式 A：例行分析 ---
        prompt = f"""
        現在是【{phase_name}】。任務：{phase_desc}
        你是一位對沖基金首席分析師，請產出「深度產業趨勢與科研掃描」報告。
        行情數據：{market_data}
        底層資訊：{all_titles}
        報告結構：
        🚨 【重磅警報：技術或總經動態】
        ✨ 【今日實戰標的對照】(分析 3-5 個標的)
        🧠 【深度解析：產業趨勢】(結合 arXiv/HN 內容)
        🏁 【最終操作指南】
        產出時間：{current_time_str} (澳門時間)
        """
    else:
        # --- 模式 B：實戰指令 (咭片格式) ---
        prompt = f"""
        現在是【{phase_name}】。你是對沖基金交易主管，請立即產出「超短線交易指令」。
        即時行情：{market_data}
        最新資訊：{all_titles}

        請嚴格遵守以下「咭片格式」排版，嚴禁使用表格：

        🚨 【{phase_name}：戰鬥邏輯】
        (用兩句話直擊當前市場定價錯誤與獲利核心)

        🔥 【超短線：即時交易指令】
        ━━━━━━━━━━━━━━━━
        💰 標的：[Ticker] (現價: $XXX)
        ├─ 🚦 策略：【 🟢 強力買入 / 🔴 立即做空 / 🟡 觀望 】
        ├─ ⚡ 亞微秒信心值：[ 90%以上 ]
        ├─ 🎯 目標點位：
        │  🚀 最佳進場：$XXX.XX
        │  💰 止盈目標：$XXX.XX
        │  🛑 嚴格止損：$XXX.XX
        └─ 💡 賺錢邏輯：(精煉解釋為何此點位能獲利，結合技術面與今日資訊)
        ━━━━━━━━━━━━━━━━
        (請針對 3-5 個最具爆發力標的產出咭片)

        🧠 【產業降維打擊：深度推演】
        (分析科研動態如 Lean 4、量子算法等如何長期影響相關標的估值)

        ⚡ 【亞微秒級推文】
        (撰寫一段極具速度感與金錢味道的短文，吸引資金情緒。)

        🏁 【最終執行清單】
        (1. 必須鎖定的動作 2. 避開的陷阱 3. 預備觸發點)

        產出時間：{current_time_str} (澳門時間)
        """

    # 7. 生成並發送報告
    try:
        response = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
        if response.text:
            full_report = response.text
            # 發送至 Telegram
            send_telegram(full_report)
            
            # 存儲為 JSON 供網頁前端讀取
            with open("build/latest_data.json", "w", encoding="utf-8") as f:
                json.dump({
                    "time": current_time_str, 
                    "phase": phase_name, 
                    "report": full_report, 
                    "stocks": stock_dict
                }, f, ensure_ascii=False, indent=2)
            print(f"成功產出報告：{phase_name}")
    except Exception as e: 
        print(f"AI 生成失敗: {e}")

if __name__ == "__main__":
    main()
