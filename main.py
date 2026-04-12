import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
import time
import json
from google import genai

def fetch_rss_data(source_name, url):
    """抓取數據"""
    print(f"📡 正在抓取 {source_name}...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
        items = [f"[{source_name}] {item.find('title').text}" for item in root.findall('.//item')[:10]]
        return "\n".join(items)
    except Exception as e:
        print(f"⚠️ {source_name} 失敗: {e}")
        return ""

def send_telegram_msg(text):
    """將報告發送到 Telegram (改用 HTML 模式更穩定)"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("⚠️ 找不到 Telegram 設定。")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    # 簡單的清理：將 Markdown 的 ** 換成 HTML 的 <b>，避免 400 錯誤
    safe_text = text.replace("**", "<b>").replace("**", "</b>")
    
    # 限制長度
    if len(safe_text) > 4000: safe_text = safe_text[:4000] + "..."
    
    payload = {
        "chat_id": chat_id,
        "text": safe_text,
        "parse_mode": "HTML" # 改用 HTML 模式，容錯率更高
    }
    
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as response:
            if response.getcode() == 200:
                print("📲 報告已成功推送到 Telegram！")
    except Exception as e:
        # 如果 HTML 也失敗，最後一招：用純文字發送，保證一定收得到
        print(f"⚠️ HTML 推送失敗，嘗試純文字模式... ({e})")
        payload["parse_mode"] = ""
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as response:
             print("📲 報告已透過純文字模式送達！")

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    # 1. 抓取數據
    f_news = fetch_rss_data("CNBC 財經", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147")
    t_news = fetch_rss_data("科技半導體", "https://www.theverge.com/rss/index.xml")
    combined_news = f"{f_news}\n{t_news}"

    # 2. 定製化 Prompt
    prompt = f"""
    你現在是實戰派投資顧問。請將以下新聞轉化為素人能懂的投資建議：
    {combined_news}
    
    格式要求：
    ### 🚀 實戰標的對照表
    請列出具體股票代號 (Ticker)、影響方向(🟢/🔴)、以及白話理由。
    
    ### 🧠 深度拆解 (表格)
    包含：觀察點、新聞事實、產業聯想、邏輯推演。
    
    ### 💡 素人投資筆記
    板塊風險與潛在受益者。
    
    ### 🏁 最終操作指南 (建議行動與核心觀察名單)
    
    請用繁體中文，多用 Markdown 字體加粗讓手機易讀。
    """

    # 3. 分析與重試
    for i in range(3):
        try:
            print(f"🤖 AI 分析中 (第 {i+1} 次)...")
            response = client.models.generate_content(model='gemini-flash-latest', contents=prompt)
            report = response.text
            
            # 輸出到 Log 並發送到 Telegram
            print(report)
            send_telegram_msg(report)
            break 
        except Exception as e:
            if "503" in str(e) and i < 2:
                time.sleep(30)
            else:
                print(f"❌ 失敗: {e}")
                sys.exit(1)

if __name__ == "__main__":
    main()
