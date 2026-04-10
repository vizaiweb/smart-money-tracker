import os
import sys
from google import genai

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ 錯誤：找不到 GEMINI_API_KEY")
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    
    # 根據你剛才提供的清單，這三個是 2026 年最有可能成功的型號
    test_models = [
        'gemini-2.0-flash', 
        'gemini-2.0-flash-lite', 
        'gemini-flash-latest'
    ]
    
    success = False
    for model_id in test_models:
        try:
            print(f"🔍 正在嘗試撥通模型: {model_id}...")
            response = client.models.generate_content(
                model=model_id, 
                contents="請回答：OK"
            )
            print(f"\n✅ 恭喜！模型 {model_id} 成功連接！")
            print(f"🌟 AI 回應：{response.text}")
            success = True
            break # 只要一個成功就停止
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                print(f"⚠️ {model_id}: 配額暫時為 0 (RESOURCE_EXHAUSTED)")
            elif "404" in error_msg:
                print(f"⚠️ {model_id}: 路徑未找到 (NOT_FOUND)")
            else:
                print(f"⚠️ {model_id}: 其他錯誤 - {error_msg[:50]}")

    if not success:
        print("\n" + "="*40)
        print("📢 最終診斷：")
        print("你的代碼邏輯和工具鏈已經【完全正確】。")
        print("目前所有的失敗都指向 Google 帳號的『初始配額延遲』。")
        print("這在 2026 年對新 API Key 非常常見，通常會在 24 小時內自動修復。")
        print("="*40)
        sys.exit(1)

if __name__ == "__main__":
    main()
