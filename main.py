import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
from google import genai

def fetch_finance_news():
    """更換為 CNBC 的 RSS 源，並加強偽裝"""
    print("📡 正在抓取 CNBC 即時財經數據...")
    # 更換為 CNBC 商業新聞源
    url = "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147"
    try:
        # 加強 Header 偽裝，讓它看起來更像真實瀏覽器
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/xml,application/xml,application/xhtml+xml'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()
        
        root = ET.fromstring(xml_data)
        news_items = []
        # 尋找 RSS 中的新聞標題
        for item in root.findall('.//item')[:12]: 
            title = item.find('title').text
            description = item.find('description').text if item.find('description') is not None else ""
            news_items.append(f"【標題】{title}\n【摘要】{description}")
            
        print(f"✅ 成功獲取 {len(news_items)} 則最新消息")
        return "\n\n".join(news_items)
    except Exception as e:
        print(f"⚠️ 抓取失敗: {e}")
        return "無法獲取即時新聞資料，請檢查網絡或源網址。"

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
