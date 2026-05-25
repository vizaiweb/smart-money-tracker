"""
美股AI七雄每日深度追蹤 - 蘋果、輝達、微軟、亞馬遜、特斯拉、Alphabet、Meta
每天 7:55 和 13:55 發送獨立分析報告（使用與 main.py 相同的 AI 風格）
"""

import os
import sys
import urllib.parse
import time
from datetime import datetime, timezone, timedelta
import yfinance as yf
from google.genai import Client

# ===== AI 七雄股票列表 (代號, 中文名, 英文名) =====
MAGNIFICENT_SEVEN = [
    {"ticker": "AAPL", "ch_name": "蘋果", "en_name": "Apple Inc."},
    {"ticker": "NVDA", "ch_name": "輝達", "en_name": "NVIDIA Corporation"},
    {"ticker": "MSFT", "ch_name": "微軟", "en_name": "Microsoft Corporation"},
    {"ticker": "AMZN", "ch_name": "亞馬遜", "en_name": "Amazon.com Inc."},
    {"ticker": "TSLA", "ch_name": "特斯拉", "en_name": "Tesla Inc."},
    {"ticker": "GOOGL", "ch_name": "谷歌母公司 Alphabet", "en_name": "Alphabet Inc."},
    {"ticker": "META", "ch_name": "臉書母公司 Meta", "en_name": "Meta Platforms Inc."}
]

# ===== 股票全稱對照（與 main.py 保持一致）=====
STOCK_FULL_NAMES = {
    "AAPL": {"ch": "蘋果", "en": "Apple Inc."},
    "NVDA": {"ch": "輝達", "en": "NVIDIA Corporation"},
    "MSFT": {"ch": "微軟", "en": "Microsoft Corporation"},
    "AMZN": {"ch": "亞馬遜", "en": "Amazon.com Inc."},
    "TSLA": {"ch": "特斯拉", "en": "Tesla Inc."},
    "GOOGL": {"ch": "谷歌母公司 Alphabet", "en": "Alphabet Inc."},
    "META": {"ch": "臉書母公司 Meta", "en": "Meta Platforms Inc."}
}

def get_m7_stock_data():
    """獲取七雄的即時數據和基本面（與 main.py 格式一致）"""
    results = {}
    print("📊 正在獲取 AI 七雄即時數據...")
    
    for stock in MAGNIFICENT_SEVEN:
        ticker = stock["ticker"]
        try:
            s = yf.Ticker(ticker)
            hist = s.history(period="2d")
            
            if len(hist) >= 1:
                current_price = round(hist['Close'].iloc[-1], 2)
                prev_close = round(hist['Close'].iloc[-2], 2) if len(hist) >= 2 else current_price
                day_change = round(((current_price - prev_close) / prev_close) * 100, 2)
                
                # 獲取基本面（與 main.py 一致）
                info = s.info
                market_cap = info.get('marketCap')
                pe = info.get('trailingPE')
                target_price = info.get('targetMeanPrice')
                
                results[ticker] = {
                    "price": current_price,
                    "day_change": day_change,
                    "market_cap": round(market_cap/1e9, 1) if market_cap else "N/A",
                    "pe": round(pe, 1) if pe else "N/A",
                    "target_price": round(target_price, 2) if target_price else "N/A",
                    "sector": "🚀 科技/AI",
                    "ch_name": stock["ch_name"],
                    "en_name": stock["en_name"]
                }
            else:
                results[ticker] = {
                    "price": "N/A",
                    "day_change": "N/A",
                    "market_cap": "N/A",
                    "pe": "N/A",
                    "target_price": "N/A",
                    "sector": "🚀 科技/AI",
                    "ch_name": stock["ch_name"],
                    "en_name": stock["en_name"]
                }
        except Exception as e:
            print(f"⚠️ {ticker} 獲取失敗: {e}")
            results[ticker] = {
                "price": "N/A",
                "day_change": "N/A",
                "market_cap": "N/A",
                "pe": "N/A",
                "target_price": "N/A",
                "sector": "🚀 科技/AI",
                "ch_name": stock["ch_name"],
                "en_name": stock["en_name"]
            }
    
    print(f"✅ 成功獲取 {len(results)} 支 AI 七雄數據")
    return results

def send_telegram(text):
    """發送 Telegram 消息"""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    
    if not token or not chat_id:
        print("⚠️ 未配置 Telegram 憑證，跳過發送")
        return
    
    text = text.replace("*", "")
    if len(text) > 4000:
        text = text[:3900] + "\n...(訊息過長截斷)"
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    
    try:
        urllib.request.urlopen(url, data=data, timeout=15)
        print("📲 AI 七雄分析報告已發送")
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
    now = datetime.now(tz)
    
    # 判斷是早上還是下午報告
    if now.hour < 12:
        session = "早盤"
    else:
        session = "午盤"
    
    print("=" * 50)
    print(f"🤖 AI 七雄深度追蹤 - {session}")
    print(f"運行時間: {current_time}")
    print("=" * 50)
    
    # 獲取七雄數據
    m7_data = get_m7_stock_data()
    
    # 構建價格摘要（與 main.py 格式完全一致）
    price_summary = f"【AI 七雄即時市場數據】(來源: yfinance, 更新於 {current_time})\n"
    for ticker, data in m7_data.items():
        if data['price'] != "N/A":
            target = f"目標價 ${data['target_price']}" if data['target_price'] != "N/A" else "無機構目標價"
            price_summary += f"- {ticker} ({data['ch_name']}, {data['en_name']}): ${data['price']} ({data['day_change']:+.1f}%) | {target} | {data['sector']}\n"
        else:
            price_summary += f"- {ticker} ({data['ch_name']}): 數據獲取失敗\n"
    
    # 構建 AI 提示詞（與 main.py 風格一致，但聚焦 M7）
    prompt = f"""
你的身份：一位專注於美股科技巨頭的資深分析師，專精於「Magnificent 7」（AI 七雄）研究。

任務：
1. **复盘**：分析昨日（或最近一個交易日）**AI 七雄**（蘋果、輝達、微軟、亞馬遜、特斯拉、Alphabet、Meta）這七支股票的漲跌表現，說明 **上漲或下跌的具體原因**。
2. **预告**：基於當前數據和趨勢，對 **下一個交易日** 這七支股票的走勢給出明確預告。

**重要規則：**
- 嚴格禁止使用任何 * 號（不要用粗體）。
- 分析必須 **緊扣下面提供的真實數據**，不要憑空猜測。
- 原因分析要具體（例如：受財報、產品發表、行業政策、或大盤情緒帶動）。
- 走勢預告要清晰（看多 / 看空 / 震蕩），並給出最核心的一個理由。
- 每支股票都要給出獨立的分析和預判。

以下是 **AI 七雄（Magnificent 7）的即時數據**：

{price_summary}

**請嚴格按照以下格式輸出分析報告（不要用 * 號）：**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【AI 七雄 - {session} 深度復盤】

📌 **整體表現摘要**
(用1-2句話總結七雄今日整體強弱)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**1. AAPL (蘋果, Apple Inc.)**
- 昨日表現: (上漲/下跌 X.X%)
- 核心原因: (1-2句話，具體說明)
- 驅動邏輯鏈條: (簡要說明事件如何影響股價)

**2. NVDA (輝達, NVIDIA Corporation)**
- 昨日表現: (上漲/下跌 X.X%)
- 核心原因: (1-2句話)
- 驅動邏輯鏈條: (簡要說明)

**3. MSFT (微軟, Microsoft Corporation)**
- 昨日表現: ...
- 核心原因: ...
- 驅動邏輯鏈條: ...

**4. AMZN (亞馬遜, Amazon.com Inc.)**
- 昨日表現: ...
- 核心原因: ...
- 驅動邏輯鏈條: ...

**5. TSLA (特斯拉, Tesla Inc.)**
- 昨日表現: ...
- 核心原因: ...
- 驅動邏輯鏈條: ...

**6. GOOGL (谷歌母公司 Alphabet, Alphabet Inc.)**
- 昨日表現: ...
- 核心原因: ...
- 驅動邏輯鏈條: ...

**7. META (臉書母公司 Meta, Meta Platforms Inc.)**
- 昨日表現: ...
- 核心原因: ...
- 驅動邏輯鏈條: ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【下一個交易日走勢預告】

- **七雄整體判斷**: (看多 / 看空 / 震蕩)
- **核心關注點**: (下個交易日需要關注的關鍵事件或數據)

**重點個股預判**:
- AAPL (蘋果): 預計 (偏多/偏空)，理由 (一句話)
- NVDA (輝達): 預計 (偏多/偏空)，理由 (一句話)
- MSFT (微軟): 預計 (偏多/偏空)，理由 (一句話)
- AMZN (亞馬遜): 預計 (偏多/偏空)，理由 (一句話)
- TSLA (特斯拉): 預計 (偏多/偏空)，理由 (一句話)
- GOOGL (Alphabet): 預計 (偏多/偏空)，理由 (一句話)
- META (Meta): 預計 (偏多/偏空)，理由 (一句話)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【需要警惕的風險】
(列出 1-2 個可能影響七雄的整體風險)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    # 調用 Gemini 生成分析（與 main.py 相同方式）
    for attempt in range(3):
        try:
            print(f"🤖 AI 分析七雄中 ({attempt+1}/3)...")
            resp = client.models.generate_content(model='gemini-flash-latest', contents=prompt)
            if resp.text:
                # 添加報告資訊（與 main.py 格式一致）
                footer = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📎 報告時間: {current_time} (澳門時間)
📌 數據來源: yfinance
⚡ 免責聲明: 以上分析僅供參考，不構成投資建議。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 短线交易纪律提醒
├─ 5日均线是生命线，跌破即止损
├─ 连续止损2次，当日停止交易
├─ 单只股票仓位 ≤ 10%
└─ 不满足3项技术信号 → 不开仓
"""
                send_telegram(resp.text + footer)
                break
        except Exception as e:
            print(f"❌ Gemini 錯誤: {e}")
            time.sleep(30 if "429" in str(e) else 10)

if __name__ == "__main__":
    main()
