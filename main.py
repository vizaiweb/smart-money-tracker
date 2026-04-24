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

HOT_KEYWORDS = ['Ising', 'Quantum', 'Superconductor', 'Photonics', 'CPO', 'Nuclear', 'Fusion', 'LLM Architecture']

def fetch_rss_data(source_name, url):
    print(f"📡 正在抓取 {source_name}...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
        items = []
        for item in root.findall('.//item'):
            title_elem = item.find('title')
            if title_elem is not None and title_elem.text:
                items.append(title_elem.text)
        return items[:10]
    except Exception as e:
        print(f"⚠️ {source_name} 抓取失敗: {e}")
        return []

def get_stock_details(tickers):
    stock_info_text = ""
    for symbol in tickers:
        try:
            s = yf.Ticker(symbol)
            price = s.history(period='1d')['Close'].iloc[-1]
            stock_info_text += f"- {symbol}: 現價 ${price:.2f}\n"
        except:
            try:
                price = s.fast_info['last_price']
                stock_info_text += f"- {symbol}: 現價 ${price:.2f}\n"
            except:
                continue
    return stock_info_text

def send_telegram_msg(text):
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return

    clean_text = text.replace("**", "")
    if len(clean_text) > 4000:
        clean_text = clean_text[:3900] + "\n\n...(訊息過長，已截斷)"

    params = urllib.parse.urlencode({"chat_id": chat_id, "text": clean_text})
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    for attempt in range(3):
        try:
            urllib.request.urlopen(url, data=params.encode(), timeout=15)
            print("📲 報告已發送！")
            return
        except Exception as e:
            print(f"❌ 發送失敗 ({attempt+1}/3): {e}")
            time.sleep(5 * (attempt + 1))

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        sys.exit(1)
    client = Client(api_key=api_key)

    tz_macau = timezone(timedelta(hours=8))
    current_time = datetime.now(tz_macau).strftime("%Y-%m-%d %H:%M:%S")

    arxiv = fetch_rss_data("arXiv", "https://rss.arxiv.org/rss/cs.AI")
    hacker_news = fetch_rss_data("HackerNews", "https://news.ycombinator.com/rss")
    market_news = fetch_rss_data("CNBC", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147")

    all_titles = "\n".join(arxiv + hacker_news + market_news)

    source_reference = "🔗 【資訊來源清單】\n"
    source_reference += "📌 arXiv AI: " + (", ".join(arxiv[:3]) if arxiv else "無更新") + "...\n"
    source_reference += "📌 HackerNews: " + (", ".join(hacker_news[:3]) if hacker_news else "無更新") + "...\n"
    source_reference += "📌 CNBC: " + (", ".join(market_news[:3]) if market_news else "無更新") + "..."

    if not all_titles.strip():
        print("📭 無新數據，停止執行。")
        return

    # 改進 hash: 只取前 5 條標題
    hash_input = "\n".join((arxiv + hacker_news + market_news)[:5])
    current_hash = hashlib.md5(hash_input.encode('utf-8')).hexdigest()
    hash_file = "last_news_hash.txt"
    if os.path.exists(hash_file):
        with open(hash_file, "r") as f:
            if f.read() == current_hash:
                print("😴 內容與上次相同，跳過發送。")
                return
    with open(hash_file, "w") as f:
        f.write(current_hash)

    is_emergency = any(word.lower() in all_titles.lower() for word in HOT_KEYWORDS)
    alert_prefix = "🚨 【高能技術預警】" if is_emergency else "🔍 【例行市場掃描】"

    # 更穩定的 Ticker 提取
    ticker_list = ["NVDA", "TSLA", "PLTR"]
    try:
        res = client.models.generate_content(
            model='gemini-flash-latest',
            contents=f"從以下新聞提取5個美股代號，只回傳代號用逗號隔開，不要多餘文字:\n{all_titles[:2000]}"
        )
        extracted = [t.strip().upper() for t in res.text.split(",") if 1 < len(t.strip()) < 6]
        if extracted:
            ticker_list = extracted[:5]
    except:
        pass

    real_market_data = get_stock_details(ticker_list)

    prompt = f"""
{alert_prefix}
你現在是精通硬核科技的首席分析師。請針對以下數據產出繁體中文報告。

【現價數據】: {real_market_data}
【新聞與科研摘要】: {all_titles[:3000]}

請絕對禁止使用表格，請完全依照以下格式排版：

🚨 【重磅警報：技術或總經動態】
(分析內容...)

✨ 【今日實戰標的對照】
━━━━━━━━━━━━━━━━
💰 股票代號 Ticker (參考現價: $XXX)
├─ 🚦 影響：🟢 看多 / 🔴 看空 / 🟡 觀望
├─ 📢 事實：(一句話新聞核心)
├─ 📈 操作建議：(給出建議買入位、止盈位與止損位)
└─ 💡 理由：(技術聯想與投資邏輯)
━━━━━━━━━━━━━━━━
(請列出 3-5 個)

🧠 【深度解析：產業趨勢】
(分析趨勢與邏輯推演)

🏁 【最終操作指南】
(建議行動/觀察名單)

---
{source_reference}
產出時間：{current_time} (澳門時間)
"""

    for i in range(3):
        try:
            print(f"🤖 AI 分析中 (嘗試 {i+1})...")
            response = client.models.generate_content(model='gemini-flash-latest', contents=prompt)
            if response.text:
                send_telegram_msg(response.text)
                break
        except Exception as e:
            print(f"❌ Gemini 錯誤: {e}")
            time.sleep(30 if "429" in str(e) else 10)

if __name__ == "__main__":
    main()
