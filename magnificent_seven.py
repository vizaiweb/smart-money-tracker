"""
美股AI七雄每日追蹤 - 蘋果、輝達、微軟、亞馬遜、特斯拉、Alphabet、Meta
每天 7:55 和 13:55 發送獨立報告
"""

import os
import sys
import urllib.parse
from datetime import datetime, timezone, timedelta
import yfinance as yf

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

def get_stock_data():
    """獲取七雄的即時數據"""
    results = []
    print("📊 正在獲取 AI 七雄即時數據...")
    
    for stock in MAGNIFICENT_SEVEN:
        try:
            ticker = stock["ticker"]
            s = yf.Ticker(ticker)
            hist = s.history(period="2d")
            
            if len(hist) >= 1:
                current_price = round(hist['Close'].iloc[-1], 2)
                prev_close = round(hist['Close'].iloc[-2], 2) if len(hist) >= 2 else current_price
                day_change = round(((current_price - prev_close) / prev_close) * 100, 2)
                
                results.append({
                    "ticker": ticker,
                    "ch_name": stock["ch_name"],
                    "en_name": stock["en_name"],
                    "price": current_price,
                    "day_change": day_change
                })
            else:
                results.append({
                    "ticker": stock["ticker"],
                    "ch_name": stock["ch_name"],
                    "en_name": stock["en_name"],
                    "price": "N/A",
                    "day_change": "N/A"
                })
        except Exception as e:
            print(f"⚠️ {stock['ticker']} 獲取失敗: {e}")
            results.append({
                "ticker": stock["ticker"],
                "ch_name": stock["ch_name"],
                "en_name": stock["en_name"],
                "price": "N/A",
                "day_change": "N/A"
            })
    
    return results

def generate_report(stock_data, current_time):
    """生成報告內容"""
    tz = timezone(timedelta(hours=8))
    now = datetime.now(tz)
    
    # 判斷是早上還是下午報告
    if now.hour < 12:
        report_title = "🌅 AI 七雄 早盤追蹤"
        note = "（開盤前參考）"
    else:
        report_title = "🌙 AI 七雄 午盤追蹤"
        note = "（盤中/盤後參考）"
    
    lines = []
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"{report_title} {note}")
    lines.append(f"📅 報告時間：{current_time} (澳門時間)")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append("| 代號 | 公司 | 即時價格 | 漲跌幅 |")
    lines.append("|------|------|----------|--------|")
    
    for s in stock_data:
        ticker = s["ticker"]
        company = f"{s['ch_name']} ({s['en_name']})"
        price = f"${s['price']}" if s['price'] != "N/A" else "N/A"
        change = f"{s['day_change']:+.1f}%" if isinstance(s['day_change'], (int, float)) else "N/A"
        lines.append(f"| {ticker} | {company} | {price} | {change} |")
    
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("📌 簡評")
    
    # 找出漲跌幅最大和最小的股票
    valid_stocks = [s for s in stock_data if isinstance(s['day_change'], (int, float))]
    if valid_stocks:
        best = max(valid_stocks, key=lambda x: x['day_change'])
        worst = min(valid_stocks, key=lambda x: x['day_change'])
        lines.append(f"- 最強：{best['ticker']} ({best['ch_name']}) {best['day_change']:+.1f}%")
        lines.append(f"- 最弱：{worst['ticker']} ({worst['ch_name']}) {worst['day_change']:+.1f}%")
    
    lines.append("")
    lines.append("⚡ 免責聲明：以上數據僅供參考，不構成投資建議。")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    return "\n".join(lines)

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
        print("📲 AI 七雄報告已發送")
    except Exception as e:
        print(f"❌ 發送失敗: {e}")

def main():
    tz = timezone(timedelta(hours=8))
    current_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    
    print("=" * 50)
    print("🤖 AI 七雄每日追蹤")
    print(f"運行時間: {current_time}")
    print("=" * 50)
    
    # 獲取數據
    stock_data = get_stock_data()
    
    # 生成報告
    report = generate_report(stock_data, current_time)
    
    # 發送
    print("\n" + report)
    send_telegram(report)

if __name__ == "__main__":
    main()
