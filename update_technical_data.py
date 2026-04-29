"""
盘后数据更新脚本 - 每天美股收盘后运行一次
功能：计算所有关注股票的技术指标，保存到JSON文件供盘中使用
"""

import json
import yfinance as yf
import pandas as pd
from datetime import datetime, timezone, timedelta
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# ===== 五大賽道股票池（与main.py保持一致）=====
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


def check_technical_signals(ticker):
    """
    检查单只股票的技术指标
    返回包含所有技术指标的字典
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="2mo")  # 获取2个月数据确保指标计算准确
        
        if len(hist) < 30:
            return None
        
        close = hist['Close']
        high = hist['High']
        low = hist['Low']
        volume = hist['Volume']
        
        # ===== 移动平均线 =====
        ma5 = close.tail(5).mean()
        ma10 = close.tail(10).mean()
        ma20 = close.tail(20).mean()
        ma60 = close.tail(60).mean() if len(close) >= 60 else close.mean()
        
        current_price = close.iloc[-1]
        prev_close = close.iloc[-2] if len(close) >= 2 else current_price
        
        # ===== 成交量分析 =====
        avg_volume_20 = volume.tail(20).mean()
        avg_volume_5 = volume.tail(5).mean()
        current_volume = volume.iloc[-1]
        volume_ratio = current_volume / avg_volume_20 if avg_volume_20 > 0 else 1
        volume_ratio_5 = current_volume / avg_volume_5 if avg_volume_5 > 0 else 1
        
        # ===== RSI (14天) =====
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs.iloc[-1])) if loss.iloc[-1] != 0 else 50
        
        # ===== MACD =====
        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        macd_signal = macd.ewm(span=9, adjust=False).mean()
        macd_histogram = macd - macd_signal
        
        # ===== 布林带 (20,2) =====
        bb_middle = ma20
        bb_std = close.tail(20).std()
        bb_upper = bb_middle + (bb_std * 2)
        bb_lower = bb_middle - (bb_std * 2)
        
        # ===== ATR (14天) - 用于止损=====
        high_low = high - low
        high_close = (high - close.shift()).abs()
        low_close = (low - close.shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=14).mean().iloc[-1]
        
        # ===== 价格位置判断 =====
        above_ma5 = current_price > ma5
        above_ma10 = current_price > ma10
        above_ma20 = current_price > ma20
        above_ma60 = current_price > ma60
        ma5_above_ma20 = ma5 > ma20
        
        # 布林带位置 (0=下轨以下, 1=中轨, 2=上轨以上)
        if current_price < bb_lower:
            bb_position = 0
        elif current_price > bb_upper:
            bb_position = 2
        else:
            bb_position = 1
        
        # ===== 单日涨跌幅 =====
        day_change = ((current_price - prev_close) / prev_close) * 100
        
        # ===== 查找所属赛道 =====
        sector = next((s for s, lst in SECTOR_WATCHLIST.items() if ticker in lst), "其他")
        
        return {
            "ticker": ticker,
            "sector": sector,
            "price": round(current_price, 2),
            "day_change": round(day_change, 2),
            "volume_ratio": round(volume_ratio, 2),
            "volume_ratio_5": round(volume_ratio_5, 2),
            "rsi": round(rsi, 1),
            "macd": round(macd.iloc[-1], 3),
            "macd_signal": round(macd_signal.iloc[-1], 3),
            "macd_histogram": round(macd_histogram.iloc[-1], 3),
            "atr": round(atr, 2),
            "bb_upper": round(bb_upper, 2),
            "bb_middle": round(bb_middle, 2),
            "bb_lower": round(bb_lower, 2),
            "bb_position": bb_position,
            "ma5": round(ma5, 2),
            "ma10": round(ma10, 2),
            "ma20": round(ma20, 2),
            "ma60": round(ma60, 2),
            "above_ma5": above_ma5,
            "above_ma10": above_ma10,
            "above_ma20": above_ma20,
            "above_ma60": above_ma60,
            "ma5_above_ma20": ma5_above_ma20,
            "atr_stop_loss": round(current_price - 2 * atr, 2),  # 2倍ATR止损价
            "timestamp": datetime.now(timezone(timedelta(hours=8))).isoformat()
        }
        
    except Exception as e:
        print(f"⚠️ {ticker} 技术指标计算失败: {e}")
        return None


def batch_check_technical(tickers, max_workers=10):
    """
    并发检查多只股票的技术指标
    """
    results = {}
    print(f"📊 开始计算 {len(tickers)} 只股票的技术指标...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(check_technical_signals, t): t for t in tickers}
        
        completed = 0
        for future in as_completed(futures):
            ticker = futures[future]
            completed += 1
            try:
                result = future.result(timeout=30)
                if result:
                    results[ticker] = result
                if completed % 20 == 0:
                    print(f"   进度: {completed}/{len(tickers)}")
            except Exception as e:
                print(f"⚠️ {ticker} 超时或错误: {e}")
    
    print(f"✅ 成功计算 {len(results)} 只股票的技术指标")
    return results


def calculate_technical_score(tech_data):
    """
    根据技术指标计算综合得分 (0-5分)
    供盘中快速使用
    """
    score = 0
    
    # 价格位置 (2分)
    if tech_data.get("above_ma5"):
        score += 1
    if tech_data.get("above_ma20"):
        score += 1
    
    # 均线多头排列 (1分)
    if tech_data.get("ma5_above_ma20"):
        score += 1
    
    # 成交量放量 (1分)
    volume_ratio = tech_data.get("volume_ratio", 0)
    if volume_ratio > 1.2:
        score += 1
    
    # RSI健康区间 (1分)
    rsi = tech_data.get("rsi", 50)
    if 30 < rsi < 70:
        score += 1
    elif rsi > 80 or rsi < 20:
        score -= 1  # 极端值减分
    
    # MACD金叉信号 (加分)
    macd = tech_data.get("macd_histogram", 0)
    if macd > 0:
        score += 0.5
    
    return min(max(score, 0), 5)  # 限制0-5分


def main():
    print("=" * 50)
    print("盘后技术指标更新程序")
    print(f"开始时间: {datetime.now(timezone(timedelta(hours=8)))}")
    print("=" * 50)
    
    # 计算所有股票的技术指标
    technical_results = batch_check_technical(ALL_TICKERS)
    
    # 为每只股票添加评分
    for ticker, data in technical_results.items():
        data["tech_score"] = calculate_technical_score(data)
    
    # 生成摘要报告
    high_score_stocks = [
        f"{ticker}({data['tech_score']}分)"
        for ticker, data in technical_results.items()
        if data.get('tech_score', 0) >= 4
    ]
    
    print(f"\n📈 高分股票 (≥4分): {len(high_score_stocks)} 只")
    if high_score_stocks:
        print(f"   {', '.join(high_score_stocks[:20])}")
    
    # 保存到JSON文件
    output_file = "technical_data.json"
    with open(output_file, "w") as f:
        json.dump(technical_results, f, indent=2, ensure_ascii=False)
    
    # 同时保存一个精简版（用于快速读取）
    quick_lookup = {
        ticker: {
            "price": data["price"],
            "tech_score": data["tech_score"],
            "above_ma5": data["above_ma5"],
            "volume_ratio": data["volume_ratio"],
            "rsi": data["rsi"],
            "atr_stop_loss": data["atr_stop_loss"],
            "sector": data["sector"]
        }
        for ticker, data in technical_results.items()
    }
    
    with open("technical_data_quick.json", "w") as f:
        json.dump(quick_lookup, f, indent=2)
    
    # 输出统计信息
    print("\n" + "=" * 50)
    print("📊 技术指标统计摘要")
    print("=" * 50)
    
    scores = [d["tech_score"] for d in technical_results.values()]
    if scores:
        print(f"平均技术分: {sum(scores)/len(scores):.1f}")
        print(f"最高分: {max(scores)}")
        print(f"最低分: {min(scores)}")
    
    print(f"\n✅ 数据已保存到 technical_data.json")
    print(f"✅ 精简版已保存到 technical_data_quick.json")
    print(f"结束时间: {datetime.now(timezone(timedelta(hours=8)))}")


if __name__ == "__main__":
    main()
