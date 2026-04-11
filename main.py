import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
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
        for item in root.findall('.//item')[:6]: # 每個源抓取前 6 則
            title = item.find('title').text
            items.append(f"[{source_name}] {title}")
        return "\n".join(items)
    except Exception as e:
        print(f"⚠️ {source_name} 抓取失敗: {e}")
        return ""

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    # 1. 抓取多源數據
    finance_news = fetch_rss_data("CNBC 財經", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147")
    tech_news = fetch_rss_data("科技半導體", "https://www.theverge.com/rss/index.xml")
    
    combined_news = f"{finance_news}\n{tech_news}"

    # 2. 定製化 Prompt
    prompt = f"""
    你現在是一位專精於『科技股與半導體』的聰明錢分析師。
    以下是最新獲取的財經與科技新聞摘要：
    
    {combined_news}
    
    請進行深度分析：
    1. **科技與半導體動向**：是否有提到 AI 晶片 (如 NVIDIA/TSMC)、設備、或新技術突破？
    2. **資金交叉點**：宏觀經濟消息（如利率）如何影響科技股的估值？
    3. **聰明錢警告**：科技領域是否有過熱或大戶減碼的跡象？
    4. **每日判斷**：給出針對『科技板塊』的明日情緒（看多/看空/觀望）。
    
    請用繁體中文回答，使用 Markdown 格式。
    """

    try:
        print(f"🤖 正在結合科技數據進行分析...")
        response = client.models.generate_content(
            model='gemini-flash-latest', 
            contents=prompt
        )
        print("\n🚀" + "="*15 + " 科技與半導體追蹤日報 " + "="*15)
        print(response.text)
        print("="*50 + "\n")
    except Exception as e:
        print(f"❌ 分析出錯：{str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
