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
    """發送到 Telegram (純文字卡片版)"""
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

    fed = fetch_rss_data("Fed 官網", "https://www.federalreserve.gov/feeds/press_all.xml")
    cnbc = fetch_rss_data("CNBC", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147")
    yahoo = fetch_rss_data("Yahoo", "https://finance.yahoo.com/news/rssindex")
    combined_news = f"{fed}\n{cnbc}\n{yahoo}"

    target_model = 'gemini-flash-latest'

    for i in range(3):
        try:
            print(f"🤖 AI 使用 {target_model} 分析中 (第 {i+1} 次)...")
            prompt = f"你現在是首席分析師，請針對以下數據提供繁體中文卡片式報告，包含🚨重磅警報、✨實戰標的、🧠深度解析。標的請用粗體和分隔線。數據：\n{combined_news}"
            
            response = client.models.generate_content(model=target_model, contents=prompt)
            
            if response.text:
                send_telegram_msg(response.text)
                print("--- 內容預覽 ---")
                print(response.text)
                break
        except Exception as e:
            print(f"⚠️ 失敗原因: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
