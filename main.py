import os
import google.generativeai as genai
import sys

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    
    # 檢查 1: Secret 有沒有讀到
    if not api_key:
        print("❌ 錯誤：找不到 GEMINI_API_KEY，請檢查 GitHub Secrets 設定。")
        sys.exit(1)
    
    print(f"✅ 成功讀取 API Key (前四位: {api_key[:4]}...)")

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        print("🤖 正在測試 AI 回應...")
        response = model.generate_content("你好，請說：測試成功")
        print(f"🌟 AI 回覆：{response.text}")
        
    except Exception as e:
        print(f"❌ AI 執行出錯：{str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
