import os
import urllib.request
import urllib.parse

def main():
    # 從 GitHub Secrets 讀取設定
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    
    print(f"📡 正在發送測試訊號...")
    print(f"🛠️ 檢查點：Token 長度={len(token)}, Chat ID={chat_id}")

    # 1. 最簡單的訊息
    message = "Hello"
    
    # 2. 構建 URL
    params = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": message
    })
    url = f"https://api.telegram.org/bot{token}/sendMessage?{params}"
    
    # 3. 發送請求
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.getcode() == 200:
                print("✅ 成功！你的手機應該收到 'Hello' 了。")
            else:
                print(f"⚠️ 收到非預期回應碼: {response.getcode()}")
    except Exception as e:
        print(f"❌ 發送失敗：{e}")
        print("\n💡 除錯指南：")
        print("1. 確保你已經在 Telegram 搜尋你的機器人並點擊了 'START'。")
        print("2. 確保 GitHub Secrets 中的 TELEGRAM_CHAT_ID 只有數字。")
        print("3. 檢查 TELEGRAM_BOT_TOKEN 是否完整（包含數字、冒號和長字串）。")

if __name__ == "__main__":
    main()
