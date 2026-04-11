import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
import time
from google import genai

def fetch_rss_data(source_name, url):
    """通用 RSS 抓取函數，具備偽裝 Header 避免被擋"""
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
        # 抓取前 6 則新聞以保持 Context 長度適中
        for item in root.findall('.//item')[:6]:
            title = item.find('title').text
            items.append(f"[{source_name}] {title}")
        
        print(f"✅ {source_name} 獲取成功")
        return "\n".join(items)
    except Exception as e:
        print(f"⚠️ {source_name} 抓取失敗: {e}")
        return ""

def main():
    # 讀取 API KEY
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ 錯誤：找不到 GEMINI_API_KEY")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    # 1. 抓取多源數據（財經大盤 + 科技半導體）
    finance_news = fetch_rss_data("CNBC 財經", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147")
    tech_news = fetch_rss_data("科技半導體", "https://www.theverge.com/rss/index.xml")
    
    combined_news = f"{finance_news}\n{tech_news}"

    if not combined_news.strip():
        combined_news = "無法獲取即時新聞，請根據目前 2026 年 4 月的半導體與總經趨勢進行分析。"

    # 2. 定製化 AI 分析提示詞
    prompt = f"""
    你現在是一位專精於『科技股與半導體』的聰明錢 (Smart Money) 分析師。
    以下是從 CNBC 與 The Verge 獲取的最新新聞摘要：
    
    {combined_news}
    
    請進行深度分析並產出報告：
    1. **核心動向**：針對目前的總體財經環境（利率、通膨、大盤）給出三句總結。
    2. **科技與半導體專欄**：是否有關於 AI 晶片 (如 NVIDIA, TSMC, AMD)、晶圓代工或新技術的重大消息？
    3. **資金交叉點**：宏觀消息如何影響科技股的資金流向？（例如：公債殖利率上升對納斯達克的壓力）。
    4. **聰明錢警告**：觀察是否有機構減碼、監管加嚴或市場過熱的訊號。
    5. **明日情緒判斷**：針對『科技板塊』給出：【看多/看空/觀望】並附上一句理由。
    
    請使用繁體中文，並以 Markdown 格式呈現，確保條理清晰。
    """

    # 3. 執行分析並加入 503 自動重試機制
    max_retries = 3
    for i in range(max_retries):
        try:
            print(f"🤖 正在向 Gemini 提交分析請求 (嘗試次數: {i+1})...")
            response = client.models.generate_content(
                model='gemini-flash-latest', 
                contents=prompt
            )
            
            # 輸出最終報表
            print("\n" + "🚀" + "="*15 + " 聰明錢：科技與半導體追蹤日報 " + "="*15)
            print(response.text)
            print("="*60 + "\n")
            break # 成功則跳出循環
            
        except Exception as e:
            error_msg = str(e)
            if "503" in error_msg and i < max_retries - 1:
                print(f"⚠️ 伺服器忙碌 (503)，等待 30 秒後重試...")
                time.sleep(30)
            else:
                print(f"❌ 分析失敗：{error_msg}")
                sys.exit(1)

if __name__ == "__main__":
    main()
