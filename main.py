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

# ===== 运行模式设置 =====
# RUN_MODE = "full" (完整模式，重新计算所有数据，用于每日总结)
# RUN_MODE = "quick" (快速模式，使用缓存的技术指标，用于盘中检查)
RUN_MODE = os.getenv("RUN_MODE", "full")

if RUN_MODE == "quick":
    print("⚡ 运行模式: 快速模式 (使用缓存数据)")
else:
    print("🔧 运行模式: 完整模式 (重新计算所有数据)")

# ===== 設定 =====
HOT_KEYWORDS = ['Ising', 'Quantum', 'Superconductor', 'Photonics', 'CPO', 'Nuclear', 'Fusion', 'LLM Architecture']
MOMENTUM_THRESHOLD = 2.5

# ===== 股票代號與全稱對照表（AI 相關重點股）=====
STOCK_FULL_NAMES = {
    "NVDA": {"ch": "輝達", "en": "NVIDIA Corporation"},
    "AMD": {"ch": "超微半導體", "en": "Advanced Micro Devices Inc."},
    "INTC": {"ch": "英特爾", "en": "Intel Corporation"},
    "ARM": {"ch": "安謀", "en": "Arm Holdings plc"},
    "MU": {"ch": "美光科技", "en": "Micron Technology Inc."},
    "SMCI": {"ch": "美超微電腦", "en": "Super Micro Computer Inc."},
    "AAPL": {"ch": "蘋果", "en": "Apple Inc."},
    "MSFT": {"ch": "微軟", "en": "Microsoft Corporation"},
    "META": {"ch": "臉書母公司 Meta", "en": "Meta Platforms Inc."},
    "GOOGL": {"ch": "谷歌母公司 Alphabet", "en": "Alphabet Inc."},
    "AMZN": {"ch": "亞馬遜", "en": "Amazon.com Inc."},
    "AVGO": {"ch": "博通", "en": "Broadcom Inc."},
    "QCOM": {"ch": "高通", "en": "Qualcomm Inc."},
    "TXN": {"ch": "德州儀器", "en": "Texas Instruments Inc."},
    "AMAT": {"ch": "應用材料", "en": "Applied Materials Inc."},
    "LRCX": {"ch": "科林研發", "en": "Lam Research Corporation"},
    "KLAC": {"ch": "科磊", "en": "KLA Corporation"},
    "ASML": {"ch": "艾司摩爾", "en": "ASML Holding NV"},
    "PLTR": {"ch": "帕蘭泰爾", "en": "Palantir Technologies Inc."},
    "CRM": {"ch": "賽富時", "en": "Salesforce Inc."},
    "ADBE": {"ch": "奧多比", "en": "Adobe Inc."},
    "NOW": {"ch": "服務現在", "en": "ServiceNow Inc."},
    "SNOW": {"ch": "雪花", "en": "Snowflake Inc."},
    "PANW": {"ch": "帕洛阿爾托網絡", "en": "Palo Alto Networks Inc."},
    "CRWD": {"ch": " crowdstrike", "en": "CrowdStrike Holdings Inc."}
}

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

# ===== 新聞來源 =====
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
    """獲取所有關注股票的即時價格和基本面"""
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
                target_price = info.get('targetMeanPrice')
                sector = next((s for s, lst in SECTOR_WATCHLIST.items() if ticker in lst), "其他")
                
                stock_data[ticker] = {
                    "price": current_price,
                    "day_change": day_change,
                    "market_cap": round(market_cap/1e9, 1) if market_cap else "N/A",
                    "pe": round(pe, 1) if pe else "N/A",
                    "target_price": round(target_price, 2) if target_price else "N/A",
                    "sector": sector
                }
        except Exception as e:
            print(f"⚠️ {ticker} 數據獲取失敗: {e}")
        time.sleep(0.1)
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

def scan_momentum_quick(stock_prices):
    """快速模式下的动能扫描 - 只获取必要数据"""
    momentum = []
    print("📈 快速扫描动能股...")
    for ticker, data in stock_prices.items():
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="2d")
            if len(hist) >= 2:
                current = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2]
                day_change = ((current - prev) / prev) * 100
                
                if 0.5 < abs(day_change) < 5.0:
                    momentum.append({
                        "ticker": ticker,
                        "sector": data.get("sector", "其他"),
                        "price": round(current, 2),
                        "day_change": round(day_change, 2),
                        "signal": "蓄力上漲" if day_change > 0 else "底部放量"
                    })
        except:
            pass
        time.sleep(0.05)
    momentum.sort(key=lambda x: abs(x['day_change']), reverse=True)
    print(f"✅ 发现 {len(momentum)} 支动能股")
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
        print("⚠️ 未配置 Telegram 凭证，跳过发送")
        return
    # 移除所有 * 號（粗體標記）
    text = text.replace("*", "")
    if len(text) > 4000:
        text = text[:3900] + "\n...(訊息過長截斷)"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    try:
        urllib.request.urlopen(url, data=data, timeout=15)
        print("📲 已發送 Telegram")
    except Exception as e:
        print(f"❌ 發送失敗: {e}")

def get_stock_full_name(ticker):
    """根據代號返回中文及英文全稱"""
    if ticker in STOCK_FULL_NAMES:
        return f"{STOCK_FULL_NAMES[ticker]['ch']}, {STOCK_FULL_NAMES[ticker]['en']}"
    return "待查詢"

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

    # 2. 獲取即時股價 (根据模式选择)
    if RUN_MODE == "quick":
        # 快速模式：加载缓存的技术指标
        import json
        try:
            with open("technical_data_quick.json", "r") as f:
                cached_tech = json.load(f)
            print(f"✅ 加载缓存技术指标，共 {len(cached_tech)} 只股票")
            
            # 转换为 stock_prices 格式
            stock_prices = {}
            for ticker, data in cached_tech.items():
                stock_prices[ticker] = {
                    "price": data["price"],
                    "day_change": 0,
                    "market_cap": "N/A",
                    "pe": "N/A",
                    "target_price": "N/A",
                    "sector": data.get("sector", "其他")
                }
        except Exception as e:
            print(f"⚠️ 加载缓存失败，回退到完整模式: {e}")
            stock_prices = get_all_stock_prices()
    else:
        stock_prices = get_all_stock_prices()
    
    # 3. 掃描動能股 (根据模式选择)
    if RUN_MODE == "quick":
        momentum_stocks = scan_momentum_quick(stock_prices)
    else:
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

    # ==================== 核心：只保留 AI 相關內容 ====================
    
    # 6. 構建價格摘要 (只保留科技/AI赛道)
    price_summary = "【AI 相關股即時市場數據】(來源: yfinance, 更新於 {})\n".format(current_time)
    ai_stocks_count = 0
    for ticker, data in list(stock_prices.items()):
        # 只保留科技/AI赛道的股票
        if data.get('sector') == "🚀 科技/AI":
            target = f"目標價 ${data['target_price']}" if data.get('target_price', 'N/A') != "N/A" else "無機構目標價"
            full_name = get_stock_full_name(ticker)
            price_summary += f"- {ticker} ({full_name}): ${data['price']} ({data.get('day_change', 0):+.1f}%) | {target}\n"
            ai_stocks_count += 1
    price_summary += f"\n**共篩選出 {ai_stocks_count} 支 AI 重點股**\n"

    # 7. 新聞摘要 (只保留科技/AI相关新闻)
    news_summary = "【AI 相關最新新聞】\n"
    ai_news_count = 0
    for n in all_news[:50]:
        # 检查新闻的 sector 是否为科技/AI，或者标题是否包含常见AI关键词
        if n["sector"] == "科技/AI" or any(kw in n["title"].lower() for kw in ['ai', 'gpu', 'nvidia', 'amd', 'intel', 'llm', 'artificial', 'intelligence']):
            news_summary += f"- [{n['source']}] {n['title'][:120]}\n"
            ai_news_count += 1
    news_summary += f"\n**共篩選出 {ai_news_count} 條 AI 相關新聞**\n"

    # 8. 提取 AI 相關的動能股信號
    ai_momentum_signals = []
    for s in momentum_stocks:
        if s['ticker'] in [t for t, d in stock_prices.items() if d.get('sector') == "🚀 科技/AI"]:
            full_name = get_stock_full_name(s['ticker'])
            ai_momentum_signals.append(f"{s['ticker']} ({full_name}) - {s['signal']}")
    
    ai_signals = ', '.join([s for s in signals if s in ['CPU需求', '算力不足', 'AI爆發']]) if signals else "無"

    # 9. Prompt：聚焦 AI 股涨跌原因分析与次日走势预告（含公司全稱）
    prompt = f"""
你的身份：一位專注於美股科技板塊的資深分析師。

任務：
1. **复盘**：分析昨日（或最近一個交易日）美股市場中，**AI 相關重點股票** 出現顯著上漲或下跌的 **具體原因**。
2. **预告**：基於當前數據和趨勢，對 **下一個交易日** 的 AI 板塊走勢給出明確預告。

**重要規則：**
- 嚴格禁止使用任何 * 號（不要用粗體）。
- 分析必須 **緊扣下面提供的真實數據**，不要憑空猜測。
- 原因分析要具體（例如：受某公司財報、行業政策、技術突破、或大盤情緒帶動）。
- 走勢預告要清晰（看多 / 看空 / 震蕩），並給出最核心的一個理由。
- **輸出股票代號時，必須同時附上中文全稱和英文全稱，格式為：NVDA (輝達, NVIDIA Corporation)**

以下是系統篩選過的 **AI 重點股即時數據**（僅包含「科技/AI」賽道）：

{price_summary}

以下是最新 **AI 相關新聞摘要**：

{news_summary}

以下是系統掃描到、與 AI 股相關的 **動能信號**：

{', '.join(ai_momentum_signals) if ai_momentum_signals else "無特定動能信號"}

檢測到的 **關鍵信號**（與 AI 相關）：{ai_signals}

**請嚴格按照以下格式輸出分析報告（不要用 * 號）：**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【昨日 AI 重點股漲跌復盤】

1. **股票代號: NVDA (輝達, NVIDIA Corporation)**
   - 昨日表現: (上漲/下跌 X.X%)
   - 核心原因: (1-2句話，具體說明)
   - 驅動邏輯鏈條: (簡要說明事件如何影響股價)

2. **股票代號: AMD (超微半導體, Advanced Micro Devices Inc.)**
   - 昨日表現: ...
   ... (請分析 2-4 隻最具代表性的 AI 股)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【下一交易日走勢預告】

- **AI 板塊整體判斷**: (看多 / 看空 / 震蕩)
- **核心關注點**: (下個交易日需要關注的關鍵事件或數據)
- **重點個股預判**:
  - NVDA (輝達, NVIDIA Corporation): 預計 (偏多/偏空)，理由 (一句話)
  - MSFT (微軟, Microsoft Corporation): 預計 (偏多/偏空)，理由 (一句話)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【需要警惕的風險】
(列出 1-2 個可能影響 AI 板塊的下行風險)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    # 10. 调用 Gemini
    for attempt in range(3):
        try:
            print(f"🤖 AI 分析中 ({attempt+1}/3)...")
            resp = client.models.generate_content(model='gemini-flash-latest', contents=prompt)
            if resp.text:
                # 添加精简的免责声明和报告信息
                footer = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📎 報告時間: {current_time} (澳門時間)
📌 數據來源: Fed, CNBC, Yahoo Finance (RSS) & yfinance
⚡ 免責聲明: 以上分析僅供參考，不構成投資建議。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
                send_telegram(resp.text + footer)
                break
        except Exception as e:
            print(f"❌ Gemini 錯誤: {e}")
            time.sleep(30 if "429" in str(e) else 10)

if __name__ == "__main__":
    main()
