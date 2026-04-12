import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
import time
import urllib.parse
from google import genai

def fetch_rss_data(source_name, url):
    """抓取 RSS 數據，並模擬瀏覽器 Header 避免被擋"""
    print(f"📡 正在抓取 {source_name}...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
        # 獲取前 6 則新聞標題
        items = [f"[{source_name}] {item.find('title').text}" for item in root.findall('.//item')[:6]]
        return "\n".join(items)
    except Exception as e:
        print(f"⚠️ {source_name} 抓取失敗: {e}")
        return f"[{source_name}] (暫時無法獲取更新)"

def send_telegram_msg(text):
    """將分析報告推送到 Telegram"""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    
    if not token or not chat_id:
        print("⚠️ 找不到 Telegram 設定，請檢查 Secrets。")
        return

    # 移除 ** 粗體符號以確保 Telegram 解析穩定
    clean_text = text.replace("**", "")
    
    if len(clean_text) > 4000: 
        clean_text = clean_text[:4000] + "..."
    
    params = urllib.parse.urlencode({"chat_id": chat_id, "text": clean_text})
    url = f"https://api.telegram.org/bot{token}/sendMessage?{params}"
    
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.getcode() == 200:
                print("📲 專業報告已成功推送到 Telegram！")
    except Exception as e:
        print(f"❌ Telegram 推送失敗: {e}")

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ 找不到 GEMINI_API_KEY")
        sys.exit(1)

    # 初始化 Client
    client = genai.Client(api_key=api_key)

    # 1. 抓取多源財經數據 (Fed + CNBC + Yahoo)
    fed_news = fetch_rss_data("Fed 官網", "https://www.federalreserve.gov/feeds/press_all.xml")
    cnbc_news = fetch_rss_data("CNBC 財經", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147")
    market_news = fetch_rss_data("Yahoo 市場", "https://finance.yahoo.com/news/rssindex")
    
    combined_news = f"{fed_news}\n{cnbc_news}\n{market_news}"

    # 2. 定製「卡片式」高級分析 Prompt
    prompt = f"""
    你現在是華爾街頂尖首席投資官 (CIO)。請從以下數據中提取最具影響力的市場動態。
    數據源：
    {combined_news}
    
    請嚴格遵守以下卡片排版規範（禁止使用表格）：
    
    🚨 【重磅警報：總經與 Fed 動態】
    (若有 Fed 消息，請置頂分析對市場直接影響。若無則寫「今日總經面平穩」。)
    
    ✨ 【今日實戰標的對照】
    列出 3-5 個標的，格式如下：
    ━━━━━━━━━━━━━━━━
    💰 股票代號 Ticker
    ├─ 🚦 影響：🟢 看多 / 🔴 看空 / 🟡 觀望
    ├─ 📢 事實：(一句話新聞核心)
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
    
    請用繁體中文，語氣果斷精鍊，善用 Emoji 增加可讀性。
    """

    # 3. 執行 AI 生成與推送 (使用你驗證成功的 gemini-flash-latest)
    target_model = 'gemini-flash-latest'
    
    for i in range(3):
        try:
            print(f"🤖 AI 首席分析師正在閱覽報告 (第 {i+1} 次)...")
            response = client.models.generate_content(model=target_model, contents=prompt)
            
            if response.text:
                report = response.text
                print("--- 報告內容預覽 ---")
                print(report)
                send_telegram_msg(report)
                break 
        except Exception as e:
            if "429" in str(e):
                print("⏳ 觸發頻率限制，強制等待 60 秒後重試...")
                time.sleep(60)
            else:
                print(f"⚠️ 嘗試失敗 ({e})，20秒後重試...")
                time.sleep(20)

if __name__ == "__main__":
    main()
