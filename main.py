import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
import time
import urllib.parse
from google import genai

def fetch_rss_data(source_name, url):
    """抓取 RSS 數據"""
    print(f"📡 正在抓取 {source_name}...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
        items = [f"[{source_name}] {item.find('title').text}" for item in root.findall('.//item')[:6]]
        return "\n".join(items)
    except Exception as e:
        print(f"⚠️ {source_name} 抓取失敗: {e}")
        return f"[{source_name}] (暫時無法獲取更新)"

def send_telegram_msg(text):
    """發送到 Telegram"""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    
    if not token or not chat_id:
        print("⚠️ 找不到 Telegram 設定。")
        return

    clean_text = text.replace("**", "")
    if len(clean_text) > 4000: clean_text = clean_text[:4000] + "..."
    
    params = urllib.parse.urlencode({"chat_id": chat_id, "text": clean_text})
    url = f"https://api.telegram.org/bot{token}/sendMessage?{params}"
    
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.getcode() == 200:
                print("📲 報告已成功推送到 Telegram！")
    except Exception as e:
        print(f"❌ 推送失敗: {e}")

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    # 1. 抓取多源財經數據
    fed_news = fetch_rss_data("Fed 官網", "https://www.federalreserve.gov/feeds/press_all.xml")
    cnbc_news = fetch_rss_data("CNBC 財經", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147")
    market_news = fetch_rss_data("Yahoo 市場", "https://finance.yahoo.com/news/rssindex")
    combined_news = f"{fed_news}\n{cnbc_news}\n{market_news}"

    # 2. 定製分析 Prompt
    prompt = f"請針對以下財經數據進行專業投資分析，使用繁體中文和卡片式排版：{combined_news}"

    # 3. 執行生成 (使用絕對模型路徑)
    for i in range(3):
        try:
            print(f"🤖 AI 分析中 (使用 models/gemini-1.5-flash)...")
            # 關鍵修正點：加上 models/ 前綴
            response = client.models.generate_content(model='models/gemini-1.5-flash', contents=prompt)
            report = response.text
            send_telegram_msg(report)
            break 
        except Exception as e:
            print(f"⚠️ 嘗試 {i+1} 失敗: {e}")
            time.sleep(20)

if __name__ == "__main__":
    main()
