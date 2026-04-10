import os
import sys
from google import genai

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ 錯誤：找不到 GEMINI_API_KEY")
        sys.exit(1)

    try:
        # 使用 2026 年最新的 Google GenAI 客戶端
        client = genai.Client(api_key=api_key)
        
        print("🤖 正在向 Gemini 發送請求...")
        # 注意：2026 年模型名稱簡化為 'gemini-2.0-flash' 或 'gemini-1.5-flash'
        response = client.models.generate_content(
            model='gemini-1.5-flash', 
            contents="請說：測試成功，準備好追蹤聰明錢了！"
        )
        
        print(f"🌟 AI 回覆：{response.text}")
        
    except Exception as e:
        print(f"❌ AI 執行出錯：{str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
