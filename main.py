import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
import time
import urllib.parse
from google import genai

def fetch_rss_data(source_name, url):
    """抓取 RSS 數據，增加更強的錯誤處理與 User-Agent"""
    print(f"📡 正在抓取 {source_name}...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
        # 獲取前 6 則新聞
        items = [f"[{source_name}] {item.find('title').text}" for item in root.findall('.//item')[:6]]
        return "\n".join(items)
    except Exception as e:
        print(f"⚠️ {source_name} 抓取失敗: {e}")
        return f"[{source_name}] (暫時無法獲取更新)"

def send_telegram_msg(text):
    """發送到 Telegram (使用卡片分隔符號優化排版)"""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    
    if not token or not chat_id:
        print("⚠️ 找不到 Telegram 設定。")
        return

    # 簡單清洗：移除可能干擾解析的符號，確保傳輸穩定
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
        print("❌ 找不到 GEMINI_API_KEY")
        sys.exit(1)

    # 初始化 Client
    client = genai.Client(api_key=api_key)

    # 1. 🔍 自動偵測可用模型名稱 (防 404)
    available_models = []
    target_model = "gemini-1.5-flash" # 預設 fallback
    try:
        for m in client.models.list():
            available_models.append(m.name)
        
        # 優先順序：2.0-flash > 1.5-flash > 1.5-flash-8b
        for candidate in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-flash-8b"]:
            if any(candidate in name for name in available_models):
                target_model = candidate
                break
        print(f"✅ 已自動選擇最優模型: {target_model}")
    except Exception as e:
        print(f"⚠️ 模型列表獲取受限，使用預設值: {target_model}")

    # 2. 抓取多源財經數據
    fed_news = fetch_rss_data("Fed 官網", "https://www.federalreserve.gov/feeds/press_all.xml")
    cnbc_news = fetch_rss_data("CNBC 財經", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147")
    market_news = fetch_rss_data("Yahoo 市場", "https://finance.yahoo.com/news/rssindex")
    
    combined_news = f"{fed_news}\n{cnbc_news}\n{market_news}"

    # 3. 定製卡片式分析 Prompt
    prompt = f"""
    你現在是華爾街頂尖首席投資官 (CIO)。請從以下數據中提取最具影響力的市場動態。
    數據源：
    {combined_news}
    
    請嚴格遵守以下卡片排版規範（禁止使用 Markdown 表格）：
    
    🚨 【重磅警報：總經與 Fed 動態】
    (若有 Fed 消息，請置頂分析對『美債殖利率』與『科技股估值』的影響。若無則寫「今日總經面平穩」。)
    
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
    
    請用繁體中文，語氣精鍊專業。
    """

    # 4. 執行生成與推送 (含 429 配額自動重試)
    for i in range(3):
        try:
            print(f"🤖 AI 首席分析師正在閱覽報告 (第 {i+1} 次)...")
            response = client.models.generate_content(model=target_model, contents=prompt)
            report = response.text
            
            print("--- 報告預覽 ---")
            print(report)
            send_telegram_msg(report)
            break 
        except Exception as e:
            if "429" in str(e):
                print("⏳ 觸發頻率限制，等待 60 秒後嘗試最後一次...")
                time.sleep(60)
            elif i < 2:
                print(f"⚠️ 嘗試失敗 ({e})，30秒後重試...")
                time.sleep(30)
            else:
                print(f"❌ 最終執行失敗: {e}")
                sys.exit(1)

if __name__ == "__main__":
    main()
