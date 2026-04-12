import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
import time
from datetime import datetime
import urllib.parse
from google import genai

def fetch_rss_data(source_name, url):
    """抓取 RSS 數據"""
    print(f"📡 正在抓取 {source_name}...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
        items = [f"[{source_name}] {item.find('title').text}" for item in root.findall('.//item')[:6]]
        return "\n".join(items)
    except Exception as e:
        return f"[{source_name}] 暫無更新"

def send_telegram_msg(text):
    """推送到 Telegram"""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id: return

    clean_text = text.replace("**", "")
    if len(clean_text) > 4000: clean_text = clean_text[:4000] + "..."
    
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
    
    client = genai.Client(api_key=api_key)

    # 1. 抓取數據與記錄時間
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sources = ["Fed 聯準會官網", "CNBC 財經新聞", "Yahoo Finance 市場動態"]
    
    fed = fetch_rss_data("Fed 官網", "https://www.federalreserve.gov/feeds/press_all.xml")
    cnbc = fetch_rss_data("CNBC", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147")
    yahoo = fetch_rss_data("Yahoo", "https://finance.yahoo.com/news/rssindex")
    combined_news = f"{fed}\n{cnbc}\n{yahoo}"

    # 2. 強化版 Prompt (含價格與時戳要求)
    prompt = f"""
    你現在是華爾街頂尖首席投資官。請針對以下數據提供繁體中文卡片式報告。
    數據源內容：
    {combined_news}
    
    【排版要求】：
    🚨 【重磅警報】 (Fed 消息與總經)
    
    ✨ 【今日實戰標的對照】
    ━━━━━━━━━━━━━━━━
    💰 股票代號 Ticker
    ├─ 🚦 影響：🟢 看多 / 🔴 看空 / 🟡 觀望
    ├─ 📢 事實：(一句話核心)
    ├─ 📈 建議價位：(根據情緒給出建議切入點與止損位)
    └─ 💡 理由：(投資邏輯)
    ━━━━━━━━━━━━━━━━
    
    🧠 【深度解析：產業趨勢】
    
    🏁 【最終操作指南】
    
    ---
    📊 【報告資訊】
    • 📅 產出時間：{current_time}
    • 🔗 參考來源：{', '.join(sources)}
    • ⚠️ 聲明：AI 分析僅供參考，不構成投資建議。
    """

    # 3. 執行生成
    target_model = 'gemini-flash-latest'
    for i in range(3):
        try:
            print(f"🤖 AI 分析中 (第 {i+1} 次)...")
            response = client.models.generate_content(model=target_model, contents=prompt)
            if response.text:
                send_telegram_msg(response.text)
                break
        except Exception as e:
            print(f"⚠️ 失敗: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
