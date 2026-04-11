import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
from google import genai

def fetch_finance_news():
    """抓取路透社財經新聞 RSS (範例源)"""
    print("📡 正在從國際新聞源抓取數據...")
    url = "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best"
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
        
        root = ET.fromstring(xml_data)
        news_items = []
        for item in root.findall('.//item')[:10]: # 抓取前 10 則新聞
            title = item.find('title').text
            news_items.append(title)
        return "\n".join(f"- {t}" for t in news_items)
    except Exception as e:
        print(f"⚠️ 抓取新聞失敗: {e}")
        return "無法獲取即時新聞資料。"

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ 錯誤：找不到 API Key")
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    
    # 1. 獲取原始數據
    raw_news = fetch_finance_news()
    
    # 2. 設定 AI 扮演的角色指令
    prompt = f"""
    你現在是一位資深的『聰明錢』追蹤分析師。
    以下是剛獲取的國際財經新聞摘要：
    
    {raw_news}
    
    請針對以上內容，進行以下分析：
    1. **核心動向**：用三句話總結目前市場最重要的資金流向。
    2. **機構訊號**：是否有提到大銀行、對沖基金或巨鯨的動作？
    3. **風險提示**：目前市場最需要擔心的變數是什麼？
    4. **明日觀點**：根據這些消息，你對明天市場的情緒判斷（看多/看空/觀望）。
    
    請用繁體中文回答，並使用 Markdown 格式讓報告易於閱讀。
    """

    try:
        print(f"🤖 正在使用 Gemini 進行深度分析...")
        # 使用昨天測試成功的模型
        response = client.models.generate_content(
            model='gemini-flash-latest', 
            contents=prompt
        )
        
        print("\n" + "🚀" + "="*15 + " 聰明錢每日分析報告 " + "="*15)
        print(response.text)
        print("="*50 + "\n")
        
    except Exception as e:
        print(f"❌ 分析過程中出錯：{str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
