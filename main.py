import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
import time
from datetime import datetime
import urllib.parse
import yfinance as yf
from google.genai import Client

def fetch_rss_data(source_name, url):
    """抓取 RSS 數據"""
    print(f"📡 正在抓取 {source_name}...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
        # 獲取前 8 則新聞標題
        items = [item.find('title').text for item in root.findall('.//item')[:8]]
        return items
    except Exception as e:
        print(f"⚠️ {source_name} 抓取失敗: {e}")
        return []

def get_stock_details(tickers):
    """獲取 Ticker 的真實股價"""
    stock_info_text = ""
    for symbol in tickers:
        try:
            print(f"📊 正在獲取 {symbol} 的即時數據...")
            s = yf.Ticker(symbol)
            # 獲取最新成交價
            price = round(s.fast_info['last_price'], 2)
            stock_info_text += f"- {symbol}: 現價 ${price}\n"
        except Exception as e:
            print(f"⚠️ 無法獲取 {symbol} 數據: {e}")
            continue
    return stock_info_text

def send_telegram_msg(text):
    """發送到 Telegram"""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("❌ 缺少 Telegram 配置")
        return

    # 移除 ** 避免格式解析問題
    clean_text = text.replace("**", "")
    if len(clean_text) > 4000:
        clean_text = clean_text[:4000] + "..."
    
    params = urllib.parse.urlencode({"chat_id": chat_id, "text": clean_text})
    url = f"https://api.telegram.org/bot{token}/sendMessage?{params}"
    try:
        urllib.request.urlopen(url, timeout=15)
        print("📲 嚴謹版報告已成功發送至 Telegram！")
    except Exception as e:
        print(f"❌ Telegram 推送失敗: {e}")

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ 缺少 GEMINI_API_KEY")
        sys.exit(1)
    
    # 初始化新版 Client
    client = Client(api_key=api_key)

    # 1. 抓取數據與時間
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fed = fetch_rss_data("Fed", "https://www.federalreserve.gov/feeds/press_all.xml")
    cnbc = fetch_rss_data("CNBC", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147")
    yahoo = fetch_rss_data("Yahoo", "https://finance.yahoo.com/news/rssindex")
    all_titles = "\n".join(fed + cnbc + yahoo)
    
    if not all_titles.strip():
        print("⚠️ 未抓取到任何新聞，停止運行。")
        return

    # 2. 第一階段：讓 AI 從新聞提取 5 個最相關的 Ticker
    print("🔍 AI 正在識別熱門標的...")
    try:
        extract_res = client.models.generate_content(
            model='gemini-flash-latest', 
            contents=f"請從以下新聞標題中找出 5 個最相關的美股代號，僅回傳代號並用逗號隔開：\n{all_titles}"
        )
        ticker_list = [t.strip().upper() for t in extract_res.text.split(",") if 1 < len(t.strip()) < 6][:5]
    except:
        ticker_list = ["NVDA", "TSLA", "PLTR"]

    # 3. 第二階段：獲取這些 Ticker 的真實現價
    real_market_data = get_stock_details(ticker_list)

    # 4. 第三階段：生成終極報告 (結合新聞 + 真實價格)
    prompt = f"""
你現在是華爾街頂尖首席投資官 (CIO)。請結合「最新新聞」與「真實現價」產出報告。

【參考數據】
產出時間：{current_time}
真實市價：
{real_market_data}
新聞摘要：
{all_titles}

請嚴格遵守以下卡片排版規範（禁止使用表格）：

🚨 【重磅警報：總經與 Fed 動態】
(若有 Fed 消息，請置頂分析對市場影響。若無則寫「今日總經面平穩」。)

✨ 【今日實戰標的對照】
列出 3-5 個標的，格式如下：
━━━━━━━━━━━━━━━━
💰 股票代號 Ticker (參考現價: $XXX)
├─ 🚦 影響：🟢 看多 / 🔴 看空 / 🟡 觀望
├─ 📢 事實：(一句話新聞核心)
├─ 📈 操作建議：(結合現價，提供精確的建議買入位、止盈位與止損位)
└─ 💡 理由：(白話投資邏輯)
━━━━━━━━━━━━━━━━

🧠 【深度解析：產業趨勢】
📌 觀察點名稱
• 📝 事實紀錄：...
• 🧪 產業聯想：...
• ⚖️ 邏輯推演：...

🏁 【最終操作指南】
• 🎯 建議行動：...
• 👁️ 核心觀察名單：...

請用繁體中文，語氣精鍊專業，標的請用粗體標記。
"""

    try:
        print(f"🤖 AI 使用 gemini-flash-latest 進行嚴謹分析中...")
        response = client.models.generate_content(model='gemini-flash-latest', contents=prompt)
        
        if response.text:
            send_telegram_msg(response.text)
            print("--- 報告內容預覽 ---")
            print(response.text)
    except Exception as e:
        print(f"❌ 報告生成失敗: {e}")

if __name__ == "__main__":
    main()
