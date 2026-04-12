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
    
    # 移除 ** 避免格式跑掉
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
            # 這裡使用的是你剛才優化的精美 Prompt
            prompt = f"""
你現在是華爾街頂尖首席投資官 (CIO)。請從以下數據中提取最具影響力的市場動態。
數據源：
{combined_news}

請嚴格遵守以下卡片排版規範（禁止使用 Markdown 表格）：

🚨 【重磅警報：總經與 Fed 動態】
(若有 Fed 消息，請置頂分析對市場影響。若無則寫「今日總經面平穩」。)

✨ 【今日實戰標的對照】
列出 3-5 個標的，格式如下：
━━━━━━━━━━━━━━━━
💰 股票代號 Ticker
├─ 🚦 影響：🟢 看多 / 🔴 看空 / 🟡 觀望
├─ 📢 事實：(一句話核心)
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

請用繁體中文，語氣精鍊專業，善用粗體字標記關鍵字。
"""
            
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
