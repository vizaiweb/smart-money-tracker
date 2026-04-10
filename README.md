# smart-money-tracker
🚀 An AI-powered investment intelligence dashboard that tracks top fund managers, legendary investors, and SEC 13F filings in real-time. Built with Next.js, Python, and Gemini AI.

# 📈 Smart-Money-Tracker 2026

**Smart-Money-Tracker** 是一個自動化的投資情報監測工具。它旨在幫助投資者從雜亂的社交媒體和繁瑣的監管文件中，提取出最有價值的「聰明錢 (Smart Money)」動向。

## 🌟 核心功能
- **大佬動向追蹤**: 自動抓取頂級投資人（如 Bill Ackman, Ray Dalio 等）在 X (Twitter) 與 Substack 的最新公開觀點。
- **13F 持倉自動掃描**: 即時連接 SEC EDGAR 數據庫，監控主要對沖基金的季度調倉變化。
- **AI 智能總結**: 整合 **Google Gemini AI**，自動將長篇研究報告或訪談轉換為「三點式摘要」。
- **情緒指標 (Sentiment Analysis)**: 分析市場大咖對當前宏觀環境的看空/看多傾向。

## 🛠️ 技術棧 (Tech Stack)
- **Frontend**: Next.js 14+, Tailwind CSS (部署於 Vercel)
- **Backend**: Python (FastAPI) + GitHub Actions (自動化任務)
- **AI Engine**: Google Gemini API (Flash 1.5)
- **Data Source**: SEC RSS Feeds, Social Media RSS Bridges
- **Database**: Supabase (PostgreSQL)

## 🤖 自動化流程 (GitHub Actions)
本專案利用 GitHub Actions 實現「零成本」自動化：
1. **每小時一次**: 執行 Python 腳本抓取新消息。
2. **AI 處理**: 將獲取的文本傳送至 Gemini 進行摘要分析。
3. **數據更新**: 將結果推送至數據庫並觸發前端網頁更新。

## 🚦 快速開始
1. **Clone 倉庫**
   ```bash
   git clone [https://github.com/你的用戶名/smart-money-tracker.git](https://github.com/你的用戶名/smart-money-tracker.git)
