import os
import google.generativeai as genai

# 1. 配置 Gemini API
# 在 GitHub Actions 運行時，它會從環境變數讀取 Secret
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

def fetch_investment_data():
    """
    模擬抓取數據。
    實際開發時，這裡可以替換成 requests.get(RSS_URL) 或 SEC API
    """
    mock_data = """
    消息來源：Pershing Square 季度致股東信
    內容：我們在 2026 年第一季度大幅增加了對 AI 基礎設施公司的持倉。
    Bill Ackman 認為目前市場低估了能源需求對 AI 發展的制約，因此轉向投資核能相關企業。
    同時，我們清空了所有傳統零售業的股份。
    """
    return mock_data

def summarize_with_ai(raw_text):
    """
    調用 Gemini AI 進行分析
    """
    prompt = f"你是一位資深投資分析師。請將以下原始資訊總結為三個重點，並標註投資情緒（看多/看空/中立）：\n\n{raw_text}"
    
    response = model.generate_content(prompt)
    return response.text

def main():
    print("🚀 開始抓取投資消息...")
    data = fetch_investment_data()
    
    print("🤖 正在使用 Gemini AI 生成摘要...")
    summary = summarize_with_ai(data)
    
    print("\n--- AI 分析結果 ---")
    print(summary)
    print("-------------------\n")
    
    # 這裡可以加入代碼將 summary 寫入 database 或更新網頁文件

if __name__ == "__main__":
    main()
