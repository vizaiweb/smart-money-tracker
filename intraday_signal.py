"""
盘中信号检查脚本 - 美股交易时段高频运行
功能：快速检查盘中异动，生成交易信号
"""

import json
import os
import sys
import urllib.parse
import time
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import yfinance as yf
from google.genai import Client


# ===== 五大賽道股票池 =====
SECTOR_WATCHLIST = {
    "🚀 科技/AI": [
        "NVDA","AMD","INTC","ARM","MU","SMCI","AAPL","MSFT","META","GOOGL","AMZN",
        "AVGO","QCOM","TXN","AMAT","LRCX","KLAC","ASML","PLTR","CRM","ADBE","NOW","SNOW","PANW","CRWD"
    ],
    "⚡ 能源/電網": ["ETR","GEV","WMB","VRT","SLB","DVN","NEE","CEG","SMR","OKLO","TLN","VST"],
    "🛡️ 國防/航太": ["BA","LMT","RTX","NOC","GD","LHX","SWMR","AVEX","ACHR","JOBY","RKLB"],
    "💊 醫療保健": ["LLY","TMO","BSX","CVS","MANE","KLRA","JNJ","PFE","MRK","ABBV","UNH","DHR"],
    "💰 金融": ["C","V","SCHW","CBRE","ALL","JPM","BAC","MS","GS","AXP","COIN","HOOD"]
}
ALL_TICKERS = list({t for lst in SECTOR_WATCHLIST.values() for t in lst})

# 热点关键词（高能预警）
HOT_KEYWORDS = ['Ising', 'Quantum', 'Superconductor', 'Photonics', 'CPO', 'Nuclear', 'Fusion', 'LLM Architecture']

# 新闻源（精简版，盘中只抓快速源）
NEWS_SOURCES = {
    "Lobsters": {"url": "https://lobste.rs/rss", "sector": "科技/AI"},
    "The Hacker News": {"url": "https://thehackernews.com/feeds/posts/default", "sector": "科技/AI"},
    "Yahoo Finance": {"url": "https://finance.yahoo.com/news/rss", "sector": "綜合"},
}


def load_technical_data():
    """加载盘前计算好的技术指标"""
    try:
        with open("technical_data_quick.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("⚠️ 未找到 technical_data_quick.json，请先运行 update_technical_data.py")
        return {}
    except Exception as e:
        print(f"⚠️ 加载技术数据失败: {e}")
        return {}


def fetch_rss_quick(source_name, url, max_items=3):
    """快速抓取RSS（盘中只取少量）"""
    try:
        import xml.etree.ElementTree as ET
        import urllib.request
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            root = ET.fromstring(resp.read())
        titles = []
        for item in root.findall('.//item'):
            title = item.find('title')
            if title is not None and title.text:
                titles.append(title.text.strip())
        return titles[:max_items]
    except Exception as e:
        print(f"⚠️ {source_name} 抓取失败: {e}")
        return []


def get_intraday_momentum(tickers, base_data):
    """
    获取盘中实时动能
    只检查有技术基准的股票
    """
    momentum = []
    print("📈 扫描盘中异动...")
    
    for ticker in tickers:
        if ticker not in base_data:
            continue
            
        try:
            stock = yf.Ticker(ticker)
            # 获取当日5分钟数据
            hist = stock.history(period="1d", interval="5m")
            
            if len(hist) >= 2:
                current = hist['Close'].iloc[-1]
                open_price = hist['Open'].iloc[0]
                prev_close = base_data[ticker].get('price', current)
                
                # 计算当日涨幅和盘中涨幅
                day_change = ((current - prev_close) / prev_close) * 100
                intraday_change = ((current - open_price) / open_price) * 100
                volume = hist['Volume'].iloc[-1]
                
                # 异动条件：涨幅>1% 或 跌幅>2% 或 盘中波动大
                if abs(day_change) > 1.0 or abs(intraday_change) > 1.5:
                    momentum.append({
                        "ticker": ticker,
                        "price": round(current, 2),
                        "day_change": round(day_change, 2),
                        "intraday_change": round(intraday_change, 2),
                        "signal": "蓄力上涨" if day_change > 0 else "回调关注",
                        "sector": base_data[ticker].get("sector", "其他")
                    })
        except Exception as e:
            pass
    
    # 按涨幅绝对值排序
    momentum.sort(key=lambda x: abs(x['day_change']), reverse=True)
    print(f"   发现 {len(momentum)} 只异动股")
    return momentum[:10]


def get_quick_news():
    """快速抓取新闻（盘中只取少量）"""
    news_list = []
    for name, src in NEWS_SOURCES.items():
        items = fetch_rss_quick(name, src["url"], max_items=3)
        for it in items:
            news_list.append({"title": it, "sector": src["sector"], "source": name})
        time.sleep(0.1)
    return news_list


def extract_quick_signals(news_items):
    """快速从新闻中提取信号"""
    keywords = {
        "AI/算力": ["AI", "GPU", "算力", "NVIDIA", "AMD"],
        "能源/核电": ["核能", "电网", "SMR", "新能源"],
        "国防": ["国防", "军工", "导弹", "太空"],
        "医疗": ["减肥药", "GLP-1", "FDA", "医疗"],
        "宏观": ["降息", "美联储", "通胀", "就业"]
    }
    signals = {}
    for news in news_items:
        title = news["title"].lower()
        for sig, kw in keywords.items():
            if any(k.lower() in title for k in kw):
                signals[sig] = signals.get(sig, 0) + 1
    return signals


def calculate_intraday_score(momentum_stock, tech_data):
    """
    盘中实时评分
    结合技术基准 + 盘中异动
    """
    ticker = momentum_stock["ticker"]
    tech_info = tech_data.get(ticker, {})
    
    score = tech_info.get("tech_score", 0)
    
    # 盘中异动加分
    day_change = momentum_stock.get("day_change", 0)
    if day_change > 2:
        score += 1.5
    elif day_change > 1:
        score += 0.5
    elif day_change < -2:
        score -= 1  # 跌幅过大减分
    
    # 成交量加分（基于技术基准中的量比）
    volume_ratio = tech_info.get("volume_ratio", 1)
    if volume_ratio > 1.5:
        score += 0.5
    
    return min(max(score, 0), 6)  # 最高6分


def send_telegram(text):
    """发送Telegram消息"""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    
    if not token or not chat_id:
        print("⚠️ 未配置Telegram凭证，跳过发送")
        return
    
    text = text.replace("*", "")
    if len(text) > 4000:
        text = text[:3900] + "\n...(訊息過長截斷)"
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    
    try:
        urllib.request.urlopen(url, data=data, timeout=15)
        print("📲 已发送Telegram")
    except Exception as e:
        print(f"❌ 发送失败: {e}")


def main():
    print("=" * 50)
    print("盘中信号检查程序")
    tz = timezone(timedelta(hours=8))
    current_time = datetime.now(tz)
    print(f"运行时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # 1. 加载技术基准数据
    technical_base = load_technical_data()
    if not technical_base:
        print("❌ 无技术基准数据，请先运行 update_technical_data.py")
        sys.exit(1)
    print(f"✅ 加载 {len(technical_base)} 只股票的技术基准")
    
    # 2. 获取盘中异动
    momentum_stocks = get_intraday_momentum(ALL_TICKERS, technical_base)
    
    # 3. 快速抓取新闻
    print("📰 抓取最新新闻...")
    news_items = get_quick_news()
    print(f"   获取 {len(news_items)} 条新闻")
    
    # 4. 提取信号
    signals = extract_quick_signals(news_items)
    
    # 5. 盘中评分
    scored_stocks = []
    for stock in momentum_stocks:
        score = calculate_intraday_score(stock, technical_base)
        stock["intraday_score"] = score
        if score >= 3:
            scored_stocks.append(stock)
    
    scored_stocks.sort(key=lambda x: x["intraday_score"], reverse=True)
    
    # 6. 高能预警
    all_titles = " ".join([n["title"] for n in news_items])
    is_emergency = any(kw.lower() in all_titles.lower() for kw in HOT_KEYWORDS)
    
    # 7. 生成报告
    report_lines = []
    report_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    report_lines.append(f"⏰ 盘中快报 | {current_time.strftime('%H:%M')}")
    if is_emergency:
        report_lines.append("🚨 高能技术预警已触发")
    report_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    # 信号摘要
    if signals:
        report_lines.append("\n【热点信号】")
        for sig, count in list(signals.items())[:5]:
            report_lines.append(f"  🔥 {sig}: {count}条")
    
    # 值得关注的股票
    if scored_stocks:
        report_lines.append("\n【值得关注】")
        for stock in scored_stocks[:5]:
            report_lines.append(f"  📌 {stock['ticker']} | {stock['sector']}")
            report_lines.append(f"     盘中: {stock['day_change']:+.1f}% | 实时: ${stock['price']}")
            report_lines.append(f"     综合分: {stock['intraday_score']}/6")
            report_lines.append("")
    else:
        report_lines.append("\n【值得关注】")
        report_lines.append("  暂无高分信号，继续观察")
    
    # 操作建议
    report_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    report_lines.append("【操作建议】")
    
    if scored_stocks and scored_stocks[0]["intraday_score"] >= 4.5:
        report_lines.append(f"  ✅ 重点关注: {scored_stocks[0]['ticker']}")
        report_lines.append(f"     止损参考: 跌破5日线或-2%")
        report_lines.append(f"     建议仓位: 不超过总资金 5%")
    elif scored_stocks:
        report_lines.append(f"  👀 列入观察: {scored_stocks[0]['ticker']}")
        report_lines.append(f"     等待放量确认后再考虑")
    else:
        report_lines.append("  ⏸️ 今日无明确信号，建议观望")
    
    report_lines.append("\n【风险提醒】")
    report_lines.append("  • 5日均线是生命线，跌破即止损")
    report_lines.append("  • 连续止损2次，今日停止交易")
    report_lines.append("  • 单只股票仓位 ≤ 10%")
    
    # 新闻摘要
    if news_items:
        report_lines.append("\n【最新快讯】")
        for news in news_items[:3]:
            title = news["title"][:60]
            report_lines.append(f"  📰 {title}...")
    
    report_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    report_lines.append("⚡ 以上分析仅供参考，不构成投资建议。")
    
    report = "\n".join(report_lines)
    
    # 8. 发送
    print("\n" + report)
    send_telegram(report)


if __name__ == "__main__":
    main()
