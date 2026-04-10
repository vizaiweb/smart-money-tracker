import os
import sys
from google import genai

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ 錯誤：找不到 GEMINI_API_KEY")
        sys.exit(1)

    try:
        # 初始化客戶端
        client = genai.Client(api_key=api_key)
        
        # 嘗試使用最基礎的模型名稱（不帶前綴）
        model_id = 'gemini-1.5-flash' 
        
        print(f"🤖 正在嘗試向模型 {model_id} 發送請求...")
        
        response = client.models.generate_content(
            model=model_id, 
            contents="請說：環境配置成功，開始追蹤主要基金！"
        )
        
        print("\n" + "="*20)
        print(f"🌟 AI 回覆：{response.text}")
        print("="*20 + "\n")
        
    except Exception as e:
        print(f"❌ 執行出錯：{str(e)}")
        print("\n正在為您查詢目前可用的模型列表...")
        try:
            # 如果失敗，列出所有可用模型供參考
            for m in client.models.list():
                print(f"可用模型: {m.name}")
        except:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()
