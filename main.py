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

# ===== 設定 =====
HOT_KEYWORDS = ['Ising', 'Quantum', 'Superconductor', 'Photonics', 'CPO', 'Nuclear', 'Fusion', 'LLM Architecture']
MOMENTUM_THRESHOLD = 2.5

# ===== 五大賽道股票池 =====
SECTOR_WATCHLIST = {
    "🚀 科技/AI": [
        "NVDA","AMD","INTC","ARM","MU","SMCI","AAPL","MSFT","META","GOOGL","AMZN",
        "AVGO","QCOM","TXN","AMAT","LRCX","KLAC","ASML","PLTR","CRM","ADBE","NOW","SNOW","PANW","CRWD"
    ],
    "⚡ 能源/電網": ["ETR","GEV","WMB","VRT","SLB","DVN","NEE","CEG","SMR","OKLO","TLN","VST"],
    "🛡️ 國防/航太": ["BA","LMT","RTX","NOC","GD","LHX","SWMR","AVEX","ACHR","JOBY","RKLB"],
    "💊 醫療保健": ["LLY","TMO","BSX","CVS","MANE","KLRA","JNJ","PFE","MRK","ABBV","UNH","DHR"],
    "💰 金融": ["C","V","SCHW","CBRE","ALL","JPM","BAC","MS","GS","AXP","COIN","HOOD"]
}
ALL_TICKERS = list({t for lst in SECTOR_WATCHLIST.values() for t in lst})

# ===== 新聞來源 (穩定可用) =====
NEWS_SOURCES = {
    "ARK Invest": {"url": "https://ark-invest.com/feed/", "sector": "宏觀/策略"},
    "Lobsters": {"url": "https://lobste.rs/rss", "sector": "科技/AI"},
    "The Hacker News": {"url": "https://thehackernews.com/feeds/posts/default", "sector": "科技/AI"},
    "MIT Technology Review": {"url": "https://www.technologyreview.com/feed", "sector": "科技/AI"},
    "Bloomberg Green": {"url": "https://feeds.bloomberg.com/green/news.rss", "sector": "能源/電網"},
    "MedTech Dive": {"url": "https://www.medtechdive.com/feeds/news/", "sector": "醫療保健"},
    "WSJ Markets": {"url": "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml", "sector": "金融"},
    "Yahoo Finance": {"url": "https://finance.yahoo.com/news/rss", "sector": "綜合"}
}

def fetch_rss(source_name, url, max_items=5):
    print(f"📡 抓取 {source_name}...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            root = ET.fromstring(resp.read())
        titles = []
        for item in root.findall('.//item'):
            title = item.find('title')
            if title is not None and title.text:
                titles.append(title.text.strip())
        return titles[:max_items]
    except Exception as e:
        print(f"⚠️ {source_name} 失敗: {e}")
        return []

def get_all_news():
    news_list = []
    for name, src in NEWS_SOURCES.items():
        items = fetch_rss(name, src["url"])
        for it in items:
            news_list.append({"title": it, "sector": src["sector"], "source": name})
        time.sleep(0.2)
    return news_list

def get_all_stock_prices():
    """獲取所有關注股票的即時價格和基本面 (核心修復)"""
    stock_data = {}
    print("💰 正在獲取即時股價...")
    for ticker in ALL_TICKERS:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="2d")
            if len(hist) >= 1:
                current_price = round(hist['Close'].iloc[-1], 2)
                prev_close = round(hist['Close'].iloc[-2], 2) if len(hist) >= 2 else current_price
                day_change = round(((current_price - prev_close) / prev_close) * 100, 2)
                
                info = stock.info
                market_cap = info.get('marketCap')
                pe = info.get('trailingPE')
                sector = next((s for s, lst in SECTOR_WATCHLIST.items() if ticker in lst), "其他")
                
                stock_data[ticker] = {
                    "price": current_price,
                    "day_change": day_change,
                    "market_cap": round(market_cap/1e9, 1) if market_cap else "N/A",
                    "pe": round(pe, 1) if pe else "N/A",
                    "sector": sector
                }
        except Exception as e:
            print(f"⚠️ {ticker} 數據獲取失敗: {e}")
        time.sleep(0.1)  # 避免限流
    print(f"✅ 成功獲取 {len(stock_data)} 支股票即時數據")
    return stock_data

def scan_momentum(stock_data):
    """從已獲取的數據中篩選動能股"""
    momentum = []
    for ticker, data in stock_data.items():
        day_chg = data.get("day_change", 0)
        if 0.5 < abs(day_chg) < 5.0:
            momentum.append({
                "ticker": ticker,
                "sector": data["sector"],
                "price": data["price"],
                "day_change": day_chg,
                "signal": "蓄力上漲" if day_chg > 0 else "底部放量"
            })
    momentum.sort(key=lambda x: abs(x['day_change']), reverse=True)
    return momentum[:15]

def extract_signals(news_items):
    keywords = {
        "CPU需求": ["CPU","x86","ARM","算力"],
        "算力不足": ["供不應求","產能不足","短缺"],
        "AI爆發": ["生成式AI","推理","大模型"],
        "電網更新": ["電網","變壓器","grid"],
        "核能復興": ["核能","SMR","小型堆"],
        "國防預算": ["國防部","五角大樓"],
        "GLP-1": ["減肥藥","糖尿病"],
        "降息預期": ["降息","聯準會"]
    }
    signals = set()
    for news in news_items:
        title = news["title"].lower()
        for sig, kw in keywords.items():
            if any(k.lower() in title for k in kw):
                signals.add(sig)
    return list(signals)[:12]

def send_telegram(text):
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return
    if len(text) > 4000:
        text = text[:3900] + "\n...(訊息過長截斷)"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    try:
        urllib.request.urlopen(url, data=data, timeout=15)
        print("📲 已發送")
    except Exception as e:
        print(f"❌ 發送失敗: {e}")

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ 缺少 GEMINI_API_KEY")
        sys.exit(1)
    client = Client(api_key=api_key)

    tz = timezone(timedelta(hours=8))
    current_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

    # 1. 抓取新聞
    print("\n📰 抓取新聞...")
    all_news = get_all_news()
    print(f"✅ 共 {len(all_news)} 條新聞")

    # 2. 獲取即時股價 (核心修復)
    stock_prices = get_all_stock_prices()
    
    # 3. 掃描動能股
    momentum_stocks = scan_momentum(stock_prices)
    print(f"📈 發現 {len(momentum_stocks)} 支動能股")

    # 4. 提取信號
    signals = extract_signals(all_news)

    # 5. 去重檢查
    news_hash = hashlib.md5(str([n["title"] for n in all_news[:20]]).encode()).hexdigest()
    hash_file = "last_news_hash.txt"
    if os.path.exists(hash_file):
        with open(hash_file, "r") as f:
            if f.read() == news_hash and not momentum_stocks:
                print("😴 無更新，跳過")
                return
    with open(hash_file, "w") as f:
        f.write(news_hash)

    # 6. 構建價格摘要 (供 AI 參考，不准編造)
    price_summary = "【即時市場數據】(來源: yfinance, 更新於 {})\n".format(current_time)
    for ticker, data in list(stock_prices.items())[:50]:  # 取前50支做參考
        price_summary += f"- {ticker}: ${data['price']} ({data['day_change']:+.1f}%) | {data['sector']}\n"

    # 7. 新聞摘要
    news_by_sector = {}
    for n in all_news[:50]:
        sec = n["sector"]
        news_by_sector.setdefault(sec, []).append(f"[{n['source']}] {n['title'][:100]}")
    news_summary = "\n".join([f"**{sec}**\n"+"\n".join(lst[:4]) for sec,lst in news_by_sector.items()])

    # 8. 高能預警
    all_titles = " ".join([n["title"] for n in all_news])
    is_emergency = any(kw.lower() in all_titles.lower() for kw in HOT_KEYWORDS)
    alert_flag = "🚨 高能技術預警" if is_emergency else "🔍 五大賽道前瞻掃描"

    # 9. Prompt (明確要求使用提供的即時價格)
    prompt = f"""
{alert_flag}

**重要**: 以下【即時市場數據】中的所有價格都是從交易所直接獲取的**真實當前價格**（更新於 {current_time} 澳門時間）。請**必須**基於這些真實價格進行分析，**嚴禁**自己編造或猜測任何股票的價格。

=== 即時市場數據 (真實價格) ===
{price_summary}

=== 新聞與機構報告 ===
{news_summary}

=== 技術面動能掃描 ===
{momentum_stocks[:10] if momentum_stocks else "無明顯動能股"}

=== 關鍵信號 ===
{', '.join(signals) if signals else "無"}

=== 輸出要求 ===
請挑選 **3-6 支** 最有可能爆發的股票，按以下格式輸出：

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 **股票代號** (參考即時價格: $XX.XX)
📂 **所屬賽道**

📌 **爆發邏輯鏈**
(趨勢 → 原因 → 市場為何尚未反應)

🎯 **預期爆發窗口**: (1-2週/1個月)
⚠️ **驗證信號**: (2個觀察事件)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**規則**:
- 價格必須引用上述【即時市場數據】中的真實數字
- 不要推薦月漲幅已超 30% 的股票
- 五大賽道盡量分散
"""

    # 10. 調用 Gemini
    for attempt in range(3):
        try:
            print(f"🤖 AI 分析中 ({attempt+1}/3)...")
            resp = client.models.generate_content(model='gemini-flash-latest', contents=prompt)
            if resp.text:
                footer = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📎 **數據時間戳**
├─ 股價數據: {current_time} (即時)
├─ 新聞數據: {current_time}
├─ 分析模型: Gemini Flash
└─ 報告時間: {current_time} (澳門時間)

⚡ 免責聲明: 以上分析僅供參考
"""
                send_telegram(resp.text + footer)
                break
        except Exception as e:
            print(f"❌ Gemini 錯誤: {e}")
            time.sleep(30 if "429" in str(e) else 10)

if __name__ == "__main__":
    main()
