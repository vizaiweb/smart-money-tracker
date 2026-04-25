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

# 掃描門檻
MOMENTUM_THRESHOLD = 2.5  # 漲跌幅超過 2.5% 視為有動能

# ===== 五大賽道掃描清單 (共 70 支) =====
SECTOR_WATCHLIST = {
    "🚀 科技/AI": [
        "NVDA", "AMD", "INTC", "ARM", "MU", "SMCI",
        "AAPL", "MSFT", "META", "GOOGL", "AMZN",
        "AVGO", "QCOM", "TXN", "AMAT", "LRCX", "KLAC", "ASML",
        "PLTR", "CRM", "ADBE", "NOW", "SNOW", "PANW", "CRWD"
    ],
    "⚡ 能源/電網": [
        "ETR", "GEV", "WMB", "VRT", "SLB", "DVN",
        "NEE", "CEG", "SMR", "OKLO", "TLN", "VST"
    ],
    "🛡️ 國防/航太": [
        "BA", "LMT", "RTX", "NOC", "GD", "LHX",
        "SWMR", "AVEX", "ACHR", "JOBY", "RKLB"
    ],
    "💊 醫療保健": [
        "LLY", "TMO", "BSX", "CVS", "MANE", "KLRA",
        "JNJ", "PFE", "MRK", "ABBV", "UNH", "DHR"
    ],
    "💰 金融": [
        "C", "V", "SCHW", "CBRE", "ALL",
        "JPM", "BAC", "MS", "GS", "AXP", "COIN", "HOOD"
    ]
}

# 扁平化清單
ALL_TICKERS = []
for tickers in SECTOR_WATCHLIST.values():
    ALL_TICKERS.extend(tickers)
ALL_TICKERS = list(set(ALL_TICKERS))

print(f"📊 總掃描股票數: {len(ALL_TICKERS)} 支 (五大賽道)")

# ===== 1. 多元化新聞來源配置 =====
NEWS_SOURCES = {
    # 宏觀策略
    "ARK Invest": {
        "url": "https://ark-invest.com/feed/",
        "sector": "宏觀/策略",
        "weight": 0.9,
        "active": True
    },
    "Barron's": {
        "url": "http://feeds.barrons.com/barrons/tech",
        "sector": "宏觀/策略",
        "weight": 0.8,
        "active": True
    },
    # 科技/AI
    "Lobsters": {
        "url": "https://lobste.rs/rss",
        "sector": "科技/AI",
        "weight": 0.7,
        "active": True
    },
    "The Hacker News": {
        "url": "https://thehackernews.com/feeds/posts/default",
        "sector": "科技/AI",
        "weight": 0.6,
        "active": True
    },
    "MIT Technology Review": {
        "url": "https://www.technologyreview.com/feed",
        "sector": "科技/AI",
        "weight": 0.8,
        "active": True
    },
    # 能源/電網
    "Reuters Energy": {
        "url": "https://www.reuters.com/business/energy/feed/",
        "sector": "能源/電網",
        "weight": 0.8,
        "active": True
    },
    "Bloomberg Green": {
        "url": "https://feeds.bloomberg.com/green/news.rss",
        "sector": "能源/電網",
        "weight": 0.7,
        "active": True
    },
    # 國防/航太
    "Defense News": {
        "url": "https://www.defensenews.com/feed/",
        "sector": "國防/航太",
        "weight": 0.9,
        "active": True
    },
    "SpaceNews": {
        "url": "https://spacenews.com/feed/",
        "sector": "國防/航太",
        "weight": 0.8,
        "active": True
    },
    # 醫療保健
    "MedTech Dive": {
        "url": "https://www.medtechdive.com/feeds/news/",
        "sector": "醫療保健",
        "weight": 0.8,
        "active": True
    },
    "BioSpace": {
        "url": "https://www.biospace.com/feed",
        "sector": "醫療保健",
        "weight": 0.7,
        "active": True
    },
    "FiercePharma": {
        "url": "https://www.fiercepharma.com/feeds/news",
        "sector": "醫療保健",
        "weight": 0.7,
        "active": True
    },
    # 金融
    "WSJ Markets": {
        "url": "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml",
        "sector": "金融",
        "weight": 0.8,
        "active": True
    },
    "FT Markets": {
        "url": "https://www.ft.com/?format=rss",
        "sector": "金融",
        "weight": 0.8,
        "active": True
    },
    "Seeking Alpha": {
        "url": "https://seekingalpha.com/feed.xml",
        "sector": "金融",
        "weight": 0.7,
        "active": True
    },
    # 綜合補充
    "Yahoo Finance": {
        "url": "https://finance.yahoo.com/news/rss",
        "sector": "綜合",
        "weight": 0.5,
        "active": True
    }
}

# ===== 2. RSS 數據抓取 =====
def fetch_rss_data(source_name, url, max_items=8):
    """抓取 RSS 數據"""
    if not url:
        return []
    
    print(f"📡 抓取 {source_name}...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
        items = []
        for item in root.findall('.//item'):
            title_elem = item.find('title')
            if title_elem is not None and title_elem.text:
                items.append(title_elem.text)
        return items[:max_items]
    except Exception as e:
        print(f"⚠️ {source_name} 抓取失敗: {e}")
        return []

def fetch_all_news():
    """從所有配置的來源抓取新聞"""
    all_news = []
    
    for source_name, source_info in NEWS_SOURCES.items():
        if not source_info.get("active", True):
            continue
        feed_content = fetch_rss_data(source_name, source_info["url"], max_items=5)
        for item in feed_content:
            all_news.append({
                "title": item,
                "sector": source_info["sector"],
                "weight": source_info["weight"],
                "source": source_name
            })
        time.sleep(0.3)  # 避免請求過於密集
    
    return all_news

# ===== 3. 五大賽道動能掃描 =====
def scan_sector_momentum():
    """掃描五大賽道的動能股票"""
    print("🔍 正在掃描五大賽道動能...")
    
    momentum_stocks = []
    
    for ticker in ALL_TICKERS:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d")
            
            if len(hist) >= 2:
                current = hist['Close'].iloc[-1]
                prev_close = hist['Close'].iloc[-2]
                day_change = ((current - prev_close) / prev_close) * 100
                
                if len(hist) >= 5:
                    five_day_ago = hist['Close'].iloc[-5]
                    five_day_change = ((current - five_day_ago) / five_day_ago) * 100
                else:
                    five_day_change = day_change
                
                avg_volume = hist['Volume'].tail(3).mean()
                last_volume = hist['Volume'].iloc[-1]
                volume_surge = (last_volume / avg_volume) if avg_volume > 0 else 1
                
                if 0.5 < abs(day_change) < 5.0 and five_day_change > -3 and volume_surge > 1.2:
                    sector = "科技/AI"
                    for s, tickers in SECTOR_WATCHLIST.items():
                        if ticker in tickers:
                            sector = s
                            break
                    
                    momentum_stocks.append({
                        "ticker": ticker,
                        "sector": sector,
                        "price": round(current, 2),
                        "day_change": round(day_change, 2),
                        "five_day_change": round(five_day_change, 2),
                        "volume_surge": round(volume_surge, 1),
                        "signal": "蓄力上漲" if day_change > 0 else "底部放量"
                    })
        except Exception as e:
            continue
    
    momentum_stocks.sort(key=lambda x: x['five_day_change'], reverse=True)
    print(f"📈 發現 {len(momentum_stocks)} 支有動能的股票")
    
    return momentum_stocks[:15]

# ===== 4. 提取關鍵信號 =====
def extract_signals_from_news(news_items):
    """從新聞中提取關鍵信號"""
    signals = []
    
    signal_keywords = {
        # 科技/AI
        "CPU需求上升": ["CPU", "處理器", "x86", "ARM", "算力芯片"],
        "算力供不應求": ["算力緊張", "產能不足", "缺貨", "supply shortage"],
        "AI需求爆發": ["AI推理", "AI應用", "大模型", "generative AI"],
        "量子突破": ["quantum", "Ising", "superconductor"],
        
        # 能源/電網
        "電網投資加速": ["grid", "輸配電", "transformer", "infrastructure"],
        "核能復興": ["nuclear", "SMR", "small modular reactor"],
        
        # 國防/航太
        "國防預算增加": ["defense budget", "Pentagon", "military spending"],
        "太空競賽": ["space", "satellite", "launch", "SpaceX"],
        
        # 醫療保健
        "GLP-1爆發": ["GLP-1", "weight loss", "diabetes", "Lilly"],
        "AI藥物發現": ["AI drug", "clinical trial", "biotech"],
        
        # 金融
        "降息預期": ["rate cut", "Fed", "interest rate", "monetary policy"],
        "併購活躍": ["M&A", "acquisition", "merger", "deal"]
    }
    
    for news in news_items:
        title = news.get("title", "").lower()
        for signal_name, keywords in signal_keywords.items():
            if any(kw.lower() in title for kw in keywords):
                if signal_name not in signals:
                    signals.append(signal_name)
    
    return signals[:15]

# ===== 5. 生成賽道摘要 =====
def generate_sector_summary(momentum_stocks, news_items):
    """生成五大賽道的動能和信號摘要"""
    sector_summary = {}
    
    for stock in momentum_stocks:
        sector = stock['sector']
        if sector not in sector_summary:
            sector_summary[sector] = {"stocks": [], "signals": []}
        sector_summary[sector]["stocks"].append(stock)
    
    # 按賽道歸類新聞信號
    for news in news_items:
        sector = news.get("sector", "綜合")
        for s in sector_summary.keys():
            if s.replace("🚀 ", "").replace("⚡ ", "").replace("🛡️ ", "").replace("💊 ", "").replace("💰 ", "") in sector:
                if len(sector_summary[s]["signals"]) < 3:
                    sector_summary[s]["signals"].append(news["title"][:80])
                break
    
    # 生成文字摘要
    summary_text = ""
    for sector, data in sector_summary.items():
        if data["stocks"]:
            summary_text += f"\n**【{sector}】**\n"
            for s in data["stocks"][:3]:
                summary_text += f"  - {s['ticker']}: {s['day_change']:+.1f}% (5日{s['five_day_change']:+.1f}%) 放量{s['volume_surge']}x\n"
            if data["signals"]:
                summary_text += f"  📡 賽道信號: {data['signals'][0][:60]}...\n"
    
    return summary_text

# ===== 6. Telegram 發送 =====
def send_telegram_msg(text):
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("⚠️ 未設定 Telegram 憑證")
        return
    
    clean_text = text.replace("**", "")
    if len(clean_text) > 4000:
        clean_text = clean_text[:3900] + "\n\n...(訊息過長，已截斷)"
    
    params = urllib.parse.urlencode({"chat_id": chat_id, "text": clean_text})
    url = f"https://api.telegram.org/bot{token}/sendMessage?{params}"
    
    try:
        urllib.request.urlopen(url, timeout=15)
        print("📲 訊息已發送！")
    except Exception as e:
        print(f"❌ 發送失敗: {e}")

# ===== 7. 主函數 =====
def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ 未設定 GEMINI_API_KEY")
        sys.exit(1)
    client = Client(api_key=api_key)

    tz_macau = timezone(timedelta(hours=8))
    current_time = datetime.now(tz_macau).strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. 抓取多元化新聞
    print("\n📰 開始抓取新聞...")
    all_news = fetch_all_news()
    print(f"✅ 共抓取 {len(all_news)} 條新聞")
    
    # 2. 掃描五大賽道動能
    momentum_stocks = scan_sector_momentum()
    
    # 3. 提取關鍵信號
    detected_signals = extract_signals_from_news(all_news)
    
    # 4. 生成賽道摘要
    sector_summary = generate_sector_summary(momentum_stocks, all_news)
    
    # 5. 去重檢查
    news_hashes = hashlib.md5(str(all_news[:20]).encode()).hexdigest()
    hash_file = "last_news_hash.txt"
    if os.path.exists(hash_file):
        with open(hash_file, "r") as f:
            if f.read() == news_hashes and not momentum_stocks:
                print("😴 內容與上次相同且無動能股，跳過發送。")
                return
    with open(hash_file, "w") as f:
        f.write(news_hashes)
    
    # 6. 關鍵字預警
    all_titles = " ".join([n["title"] for n in all_news])
    is_emergency = any(word.lower() in all_titles.lower() for word in HOT_KEYWORDS)
    alert_prefix = "🚨 【高能技術預警】" if is_emergency else "🔍 【五大賽道前瞻掃描】"
    
    # 7. 構建新聞摘要供 Gemini 分析
    news_by_sector = {}
    for news in all_news[:40]:
        sector = news.get("sector", "綜合")
        if sector not in news_by_sector:
            news_by_sector[sector] = []
        if len(news_by_sector[sector]) < 5:
            news_by_sector[sector].append(f"[{news['source']}] {news['title'][:100]}")
    
    news_summary = ""
    for sector, items in news_by_sector.items():
        if items:
            news_summary += f"\n**{sector}**\n" + "\n".join(items) + "\n"
    
    # 8. Prompt
    prompt = f"""
{alert_prefix}
你是頂尖的宏觀策略分析師，擅長從碎片化資訊中發現**還未被市場充分定價**的投資機會。

請從**五大賽道**中找出 5-8 支**近期可能爆發**的股票。

五大賽道：🚀 科技/AI | ⚡ 能源/電網 | 🛡️ 國防/航太 | 💊 醫療保健 | 💰 金融

==== 資訊來源 ====

📰 多元化新聞與機構報告：
{news_summary}

📊 五大賽道動能掃描（蓄力/放量）：
{sector_summary if sector_summary else "無明顯動能股"}

🔔 關鍵信號：
{', '.join(detected_signals) if detected_signals else "無明確信號"}

==== 輸出格式 ====

請為每支推薦股票輸出以下卡片：

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 **{股票代號}** - {公司名稱}
📂 **所屬賽道**: (科技/AI/能源/國防/醫療/金融)

📌 **爆發邏輯鏈**
(趨勢 → 受益原因 → 市場尚未反應的理由)

📊 **關鍵數據**
├─ 現價: $XX
├─ 市值: XXX億
├─ 本益比: XX
└─ 機構評級: 買入/持有/賣出

🎯 **預期爆發窗口**: (1-2週/1個月/1-3個月)
⚠️ **驗證信號**: (2-3個後續觀察事件)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

要求：
1. 每支股票獨立卡片
2. 五大賽道分散推薦
3. 避免已漲超50%的股票
4. 優先挖掘黑馬
"""
    
    # 9. 調用 Gemini
    for i in range(3):
        try:
            print(f"🤖 AI 分析中 (嘗試 {i+1})...")
            response = client.models.generate_content(
                model='gemini-flash-latest',
                contents=prompt
            )
            if response.text:
                footer = f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📎 **報告統計**
├─ 新聞來源: {len([n for n in all_news if n['sector'] != '綜合'])} 條
├─ 動能掃描: {len(momentum_stocks)} 支蓄力股
├─ 分析模型: Gemini Flash
└─ 五大賽道全覆蓋

⏰ 產出時間: {current_time} (澳門時間)
⚡ 免責聲明: AI 分析僅供參考
"""
                send_telegram_msg(response.text + footer)
                break
        except Exception as e:
            print(f"❌ Gemini 錯誤: {e}")
            time.sleep(30 if "429" in str(e) else 10)

if __name__ == "__main__":
    main()
