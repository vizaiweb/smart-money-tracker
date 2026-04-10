import os
import sys
from google import genai

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ 錯誤：找不到 GEMINI_API_KEY")
        sys.exit(1)

    try:
        client = genai.Client(api_key=api_key)
        
        # 根據你的列表，我們切換到 2.0 版本，這是 2026 年的主流穩定版
        model_id = 'gemini-2.0-flash' 
        
        print(f"🤖 正在嘗試向模型 {model_id} 發送請求...")
        
        response = client.models.generate_content(
            model=model_id, 
            contents="請說：2.0 Flash 模型連接成功！Smart Money Tracker 準備就緒。"
        )
        
        print("\n" + "="*30)
        print(f"🌟 AI 回覆：{response.text}")
        print("="*30 + "\n")
        
    except Exception as e:
        print(f"❌ 執行出錯：{str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
