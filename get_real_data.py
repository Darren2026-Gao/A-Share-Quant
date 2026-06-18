import pandas as pd
import efinance as ef
import concurrent.futures
from datetime import datetime, timedelta

print("🚀 启动 efinance 量化选股引擎：严格执行双上过滤算法...")

# ==========================================
# 算法条件 2 & 3：获取基础股池并【去ST】、【去新股】
# ==========================================
# 获取沪深京A股实时行情快照
df_spot = ef.stock.get_realtime_quotes()

# 1. 【去ST】: 过滤名称中带有 ST 或 *ST 的股票
df_filter = df_spot[~df_spot['股票名称'].str.contains("ST|\\*ST")]

# 2. 基础过滤：去除北京证券交易所（8开头的代码）
df_filter = df_filter[~df_filter['股票代码'].str.startswith('8')]
code_list = df_filter['股票代码'].tolist()

print(f"📦 已过滤高风险股池，目标计算股池：{len(code_list)} 只。正在并发计算趋势指标...")

# ==========================================
# 算法条件 1 & 4：核心指标计算与综合选股
# ==========================================
def execute_strategy(code):
    try:
        # 获取单只股票的历史日K线（efinance默认返回丰富历史，足够计算MA20和判断上市天数）
        # qfq=1 代表前复权
        df_hist = ef.stock.get_quote_history(code, fqt=1)
        
        # 【去新股】：等价于 BARSCOUNT(C)>=60 (上市满60个交易日)
        if len(df_hist) < 60:
            return None
            
        # 【双上核心】：计算 MA20
        # efinance 返回的收盘价列名为 '收盘'
        df_hist['MA20'] = df_hist['收盘'].rolling(window=20).mean()
        
        # 提取最新一天（今天）和前一天的数据
        today_data = df_hist.iloc[-1]
        yesterday_data = df_hist.iloc[-2]
        
        close_today = today_data['收盘']
        ma20_today = today_data['MA20']
        ma20_yesterday = yesterday_data['MA20']
        
        # 严格执行通达信公式：XG: C > MA20 AND MA20 > REF(MA20,1)
        is_price_above_ma20 = close_today > ma20_today
        is_ma20_turning_up = ma20_today > ma20_yesterday
        
        if is_price_above_ma20 and is_ma20_turning_up:
            return {
                "code": code,
                "name": today_data['股票名称'],
                "close": close_today,
                "ma20": round(ma20_today, 2)
            }
    except:
        pass
    return None

# ==========================================
# ⚡ 多线程加速执行引擎
# ==========================================
xg_selected_stocks = []

# 开启 30 线程并行下载
with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
    results = executor.map(execute_strategy, code_list)
    for res in results:
        if res is not None:
            xg_selected_stocks.append(res)

final_count = len(xg_selected_stocks)

print("\n" + "="*40)
print(f"🎉 综合选股(XG)计算完成！")
print(f"📅 统计日期：{datetime.now().strftime('%Y-%m-%d')}")
print(f"📊 今日最终符合『双上+去ST+去新股』的股票总数： {final_count} 只")
print("="*40)

# 如果你想顺便看一下选出来的股票前几名长啥样，可以打印出来瞧瞧
if final_count > 0:
    print("\n💡 部分符合条件的股票示例：")
    for stock in xg_selected_stocks[:5]:
        print(f"代码: {stock['code']} | 名称: {stock['name']} | 收盘价: {stock['close']} | MA20: {stock['ma20']}")
