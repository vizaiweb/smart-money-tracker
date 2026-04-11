import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
import time
import json
from google import genai

def fetch_rss_data(source_name, url):
    """通用 RSS 抓取函數"""
    print(f"📡 正在抓取 {source_name} 數據...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
        items = []
        for item in root.findall('.//item')[:8]:
            title = item.find('title').text
            items.append(f"[{source_name}] {title}")
        print(f"✅ {source_name} 獲取成功")
        return "\n".join(items)
    except Exception as e:
        print(f"⚠️ {source_name} 抓取失敗: {e}")
        return ""

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ 錯誤：找不到 API KEY")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    # 1. 抓取多源數據
    f_news = fetch_rss_data("CNBC 財經", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147")
    t_news = fetch_rss_data("科技半導體", "https://www.theverge.com/rss/index.xml")
    combined_news = f"{f_news}\n{t_news}"

    # 2. 強制表格化與事實拆解的 Prompt
    prompt = f"""
    你現在是一位專業的資深投資分析師。請針對以下新聞摘要進行深度拆解。
    
    新聞內容：
    {combined_news}
    
    請嚴格依照以下格式產出報告：
    
    ### 🚀 聰明錢：科技與半導體實戰拆解表
    請使用 Markdown 表格形式，列出 5 個核心觀察點，欄位包含：
    | 核心觀察點 | 新聞事實 (真實發生的) | 產業聯想 (AI 擴展知識) | 邏輯推演 (分析師判斷) |
    | :--- | :--- | :--- | :--- |
    
    ### 🧠 深度洞察與風險預警
    * **資金交叉點**：宏觀經濟與科技板塊的連動分析。
    * **警告訊號**：目前市場有哪些隱憂？
    
    ### 🏁 明日市場情緒判斷
    **【情緒判斷】**：(看多/看空/觀望)
    **【核心理由】**：(一句話總結)
    
    ---
    **📌 本次報告的事實清單 (Raw Data List):**
    (請在此列出你所參考的原始新聞標題，確保透明度)
    
    請使用繁體中文。
    """

    # 3. 執行分析並加入重試機制
    max_retries = 3
    for i in range(max_retries):
        try:
            print(f"🤖 正在向 Gemini 提交『拆解式分析』請求 (嘗試 {i+1})...")
            response = client.models.generate_content(model='gemini-flash-latest', contents=prompt)
            
            report_text = response.text
            print("\n" + "="*20 + " 最終拆解報告 " + "="*20)
            print(report_text)
            print("="*55 + "\n")
            break 
            
        except Exception as e:
            if "503" in str(e) and i < max_retries - 1:
                print("⚠️ 伺服器忙碌，30 秒後重試...")
                time.sleep(30)
            else:
                print(f"❌ 失敗：{e}")
                sys.exit(1)

if __name__ == "__main__":
    main()
