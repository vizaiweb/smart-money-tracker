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
        
        # 更換為 1.5 系列的最新穩定指向
        model_id = 'gemini-1.5-flash-latest' 
        
        print(f"🤖 嘗試切換至模型 {model_id}...")
        
        response = client.models.generate_content(
            model=model_id, 
            contents="請說：1.5 Flash 測試成功！"
        )
        
        print("\n" + "="*30)
        print(f"🌟 AI 回覆：{response.text}")
        print("="*30 + "\n")
        
    except Exception as e:
        print(f"❌ 執行出錯：{str(e)}")
        # 如果還是 429，我們就確認是帳號配額同步問題
        if "429" in str(e):
            print("\n💡 提示：這代表 Google 尚未給予你此模型的免費額度。")
            print("建議：請檢查 Google AI Studio 網頁版是否能正常對話。")
        sys.exit(1)

if __name__ == "__main__":
    main()
