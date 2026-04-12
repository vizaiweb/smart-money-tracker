import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
import time
import json
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
        # 獲取前 8 則新聞
        items = [f"[{source_name}] {item.find('title').text}" for item in root.findall('.//item')[:8]]
        return "\n".join(items)
    except Exception as e:
        print(f"⚠️ {source_name} 抓取失敗: {e}")
        return ""

def send_telegram_msg(text):
    """發送到 Telegram (純文字模式，避開格式解析報錯)"""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    
    if not token or not chat_id:
        print("⚠️ 找不到 Telegram 設定。")
        return

    # 1. 清理文本，確保不包含導致解析失敗的特殊符號
    # 移除 Markdown 的 ** 符號，改用更乾淨的排版
    clean_text = text.replace("**", "").replace("### ", "📌 ").replace("🚀 ", "✨ ")
    
    if len(clean_text) > 4000: clean_text = clean_text[:4000] + "..."
    
    # 2. 使用 GET 請求發送
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
        print("❌ 找不到 GEMINI_API_KEY")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    # 1. 抓取數據
    f_news = fetch_rss_data("CNBC 財經", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147")
    t_news = fetch_rss_data("科技半導體", "https://www.theverge.com/rss/index.xml")
    combined_news = f"{f_news}\n{t_news}"

    # 2. 定製 Prompt
    prompt = f"""
    你現在是資深投資分析師。請將以下新聞轉化為素人能懂的投資建議。
    新聞：{combined_news}
    
    要求格式如下：
    ### 🚀 實戰標的對照表
    (列出 Ticker、影響方向🟢/🔴、白話理由)
    
    ### 🧠 深度拆解 (表格)
    (包含觀察點、事實、聯想、邏輯)
    
    ### 💡 素人筆記
    (風險板塊與隱藏受益者)
    
    ### 🏁 最終操作指南
    (具體行動建議)
    
    請用繁體中文。
    """

    # 3. 執行分析與重試
    for i in range(3):
        try:
            print(f"🤖 AI 分析中 (第 {i+1} 次)...")
            response = client.models.generate_content(model='gemini-flash-latest', contents=prompt)
            report = response.text
            
            # 輸出日誌
            print(report)
            # 發送到 Telegram
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
