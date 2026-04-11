import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
import time
import json
from google import genai

def fetch_rss_data(source_name, url):
    """通用 RSS 抓取函數，具備瀏覽器偽裝"""
    print(f"📡 正在抓取 {source_name} 數據...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            xml_data = response.read()
        
        root = ET.fromstring(xml_data)
        items = []
        # 抓取前 10 則新聞，確保數據量足夠 AI 進行關聯分析
        for item in root.findall('.//item')[:10]:
            title = item.find('title').text
            items.append(f"[{source_name}] {title}")
        
        print(f"✅ {source_name} 獲取成功")
        return "\n".join(items)
    except Exception as e:
        print(f"⚠️ {source_name} 抓取失敗: {e}")
        return ""

def main():
    # 1. 讀取環境變數中的 API KEY
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ 錯誤：找不到 GEMINI_API_KEY，請檢查 GitHub Secrets 設定")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    # 2. 抓取多源數據（財經大盤 + 科技產業）
    f_news = fetch_rss_data("CNBC 財經", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147")
    t_news = fetch_rss_data("科技半導體", "https://www.theverge.com/rss/index.xml")
    
    combined_news = f"{f_news}\n{t_news}"

    if not combined_news.strip():
        print("⚠️ 無法獲取任何即時新聞，將使用預設數據測試。")
        combined_news = "目前新聞抓取失敗，請針對 2026 年 4 月最新的美股大盤、AI 伺服器供應鏈動向進行情境假設分析。"

    # 3. 定製化：專為素人設計的「標的對齊」Prompt
    prompt = f"""
    你現在是一位專為『財經素人』服務的實戰派投資顧問。你的任務是將複雜的新聞轉化為具體的投資行動建議。
    
    請針對以下新聞內容進行拆解：
    {combined_news}
    
    請嚴格依照以下格式產出報告，確保內容包含具體的股票代號 (Tickers)：
    
    ### 🚀 實戰標的：新聞與具體股票對照表
    請列出受新聞直接或間接影響的股票標的。
    | 關鍵標的 (Ticker) | 影響方向 | 新聞事實 (真實發生的) | 產業聯想與邏輯 (為什麼受影響) |
    | :--- | :--- | :--- | :--- |
    | 例如: NVDA.US | 🟢 看多 | 新聞提到 AI 需求暴增 | 作為 AI 晶片龍頭，訂單將直接轉化為獲利 |
    
    ### 🧠 深度拆解：事實、聯想與邏輯
    請用表格形式區分新聞與你的分析：
    | 核心觀察點 | 新聞事實 | 產業聯想 (AI 擴展知識) | 邏輯推演 (分析師判斷) |
    | :--- | :--- | :--- | :--- |
    
    ### 💡 素人投資筆記：這對你有什麼影響？
    * **哪些板塊現在不能碰？** (用最白話的方式解釋風險)
    * **有哪些「潛在受益者」？** (新聞沒寫，但 AI 聯想到的上下游供應鏈標的)
    
    ### 🏁 最終操作指南
    **【建議行動】**：(例如：觀望、分批佈局、獲利了結)
    **【核心觀察名單】**：(列出 3-5 個值得放入觀察清單的代號)
    
    ---
    **📌 本次報告參考之事實清單 (Raw Data):**
    {combined_news}
    
    請使用繁體中文，格式需美觀易讀。
    """

    # 4. 執行 AI 分析並加入 503 自動重試機制
    max_retries = 3
    for i in range(max_retries):
        try:
            print(f"🤖 正在向 Gemini 提交『素人實戰分析』請求 (嘗試第 {i+1} 次)...")
            response = client.models.generate_content(
                model='gemini-flash-latest', 
                contents=prompt
            )
            
            # 輸出最終報表到 GitHub Action Log
            print("\n" + "="*20 + " 聰明錢實戰追蹤報告 " + "="*20)
            print(response.text)
            print("="*60 + "\n")
            break 
            
        except Exception as e:
            error_text = str(e)
            if "503" in error_text and i < max_retries - 1:
                print(f"⚠️ 伺服器忙碌 (503)，等待 30 秒後進行第 {i+2} 次重試...")
                time.sleep(30)
            else:
                print(f"❌ 分析失敗：{error_text}")
                sys.exit(1)

if __name__ == "__main__":
    main()
