import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
import time
from datetime import datetime
import urllib.parse
import yfinance as yf
# 使用你在 YAML 中安裝的 google-generativeai
import google.generativeai as genai

def fetch_rss_data(source_name, url):
    """抓取 RSS 數據"""
    print(f"📡 正在抓取 {source_name}...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
        items = [item.find('title').text for item in root.findall('.//item')[:8]]
        return items
    except:
        return []

def get_stock_details(tickers):
    """獲取 Ticker 的真實股價與數據"""
    stock_info_text = ""
    for symbol in tickers:
        try:
            print(f"📊 正在獲取 {symbol} 的即時數據...")
            s = yf.Ticker(symbol)
            # 使用 fast_info 獲取最後成交價
            price = round(s.fast_info['last_price'], 2)
            stock_info_text += f"- {symbol}: 現價 ${price}\n"
        except Exception as e:
            print(f"⚠️ 無法獲取 {symbol}: {e}")
            continue
    return stock_info_text

def send_telegram_msg(text):
    """發送到 Telegram"""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id: return

    # 簡單清洗 Markdown 避免 Telegram 報錯
    clean_text = text.replace("**", "")
    if len(clean_text) > 4000: clean_text = clean_text[:4000] + "..."
    
    params = urllib.parse.urlencode({"chat_id": chat_id, "text": clean_text})
    url = f"https://api.telegram.org/bot{token}/sendMessage?{params}"
    try:
        urllib.request.urlopen(url, timeout=15)
        print("📲 嚴謹版報告已成功發送至 Telegram！")
    except Exception as e:
        print(f"❌ Telegram 推送失敗: {e}")

def main():
    # 1. 初始化 AI
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ 缺少 GEMINI_API_KEY")
        sys.exit(1)
    
    genai.configure(api_key=api_key)
    # 使用你驗證過的穩定模型名稱
    model = genai.GenerativeModel('gemini-1.5-flash')

    # 2. 準備數據與時間
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fed = fetch_rss_data("Fed", "https://www.federalreserve.gov/feeds/press_all.xml")
    cnbc = fetch_rss_data("CNBC", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147")
    yahoo = fetch_rss_data("Yahoo", "https://finance.yahoo.com/news/rssindex")
    
    all_titles = "\n".join(fed + cnbc + yahoo)
    
    # 3. 提取 Ticker (第一階段分析)
    ticker_list = ["PLTR", "NVDA", "TSLA"] # 預設值
    try:
        extract_res = model.generate_content(f"請從以下新聞中找出 5 個最相關的美股代號，僅回傳代號並用逗號隔開：\n{all_titles}")
        ticker_list = [t.strip().upper() for t in extract_res.text.split(",") if 1 < len(t.strip()) < 6][:5]
    except:
        pass

    # 4. 獲取真實股價 (關鍵嚴謹步驟)
    real_market_data = get_stock_details(ticker_list)

    # 5. 生成終極報告 (第二階段分析)
    final_prompt = f"""
    你現在是華爾街頂尖首席投資官。請結合新聞與真實數據產出卡片式報告。
    
    【當前真實市場數據】：
    {real_market_data}
    
    【最新新聞摘要】：
    {all_titles}
    
    【報告規範】：
    🚨 【重磅警報】：分析 Fed 與總經動態。
    ✨ 【今日實戰標的】：
       ━━━━━━━━━━━━━━━━
       💰 股票代號 Ticker
       ├─ 🚦 影響：🟢 看多 / 🔴 看空 / 🟡 觀望
       ├─ 📢 事實：(新聞核心)
       ├─ 📈 建議價位：(必須基於上述提供的現價給出支撐與壓力位)
       └─ 💡 理由：(白話投資邏輯)
       ━━━━━━━━━━━━━━━━
    🧠 【深度解析】：產業趨勢觀察。
    🏁 【最終操作指南】
    
    【報告資訊】：
    • 📅 產出時間：{current_time}
    • ⚠️ 聲明：AI 分析僅供參考，不構成投資建議。
    """

    try:
        print("🤖 AI 正在進行深度嚴謹分析...")
        response = model.generate_content(final_prompt)
        if response.text:
            send_telegram_msg(response.text)
            print("--- 報告預覽 ---")
            print(response.text)
    except Exception as e:
        print(f"❌ 報告生成失敗: {e}")

if __name__ == "__main__":
    main()
