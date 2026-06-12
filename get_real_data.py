import pandas as pd
import akshare as ak
import concurrent.futures
from datetime import datetime, timedelta

print("🚀 启动自主量化引擎：严格执行康康双上选股算法...")

# ==========================================
# 算法条件 2 & 3：获取基础股池并【去ST】、【去新股基本面过滤】
# ==========================================
df_spot = ak.stock_zh_a_spot_em()

# 1. 【去ST】: 等价于通达信 NAMELIKE('ST')=0 AND NAMELIKE('*ST')=0
df_filter = df_spot[~df_spot['名称'].str.contains("ST|\\*ST")]

# 2. 基础过滤：去除北交所(8开头)和三板，保留主板、创业板、科创板
df_filter = df_filter[~df_filter['代码'].str.startswith(('8', '4', '9'))]
code_list = df_filter['代码'].tolist()

# 为了确保能计算20日均线，且判断上市是否满60天，我们向前取150天历史数据
start_date = (datetime.now() - timedelta(days=150)).strftime('%Y%m%d')

# ==========================================
# 算法条件 1 & 4：核心指标计算与综合选股
# ==========================================
def execute_strategy(code):
    try:
        # 获取单只股票历史K线
        df_hist = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start_date, adjust="qfq")
        
        # 【去新股】：等价于 BARSCOUNT(C)>=60 (上市满60个交易日)
        if len(df_hist) < 60:
            return None
            
        # 【双上核心】：计算 MA20
        df_hist['MA20'] = df_hist['收盘'].rolling(window=20).mean()
        
        # 提取最新一天（今天）和前一天的数据
        today_data = df_hist.iloc[-1]
        yesterday_data = df_hist.iloc[-2]
        
        close_today = today_data['收盘']
        ma20_today = today_data['MA20']
        ma20_yesterday = yesterday_data['MA20']
        
        # 严格执行公式：XG: C > MA20 AND MA20 > REF(MA20,1)
        is_price_above_ma20 = close_today > ma20_today
        is_ma20_turning_up = ma20_today > ma20_yesterday
        
        if is_price_above_ma20 and is_ma20_turning_up:
            return code  # 命中选股
            
    except:
        pass
    return None

# ==========================================
# ⚡ 多线程加速执行引擎
# ==========================================
print(f"📦 已过滤高风险及新股，目标计算股池：{len(code_list)} 只。正在并发计算...")
xg_selected_stocks = []

# 开启多线程，利用本地国内IP优势，2分钟内即可清洗完毕
with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
    results = executor.map(execute_strategy, code_list)
    for res in results:
        if res is not None:
            xg_selected_stocks.append(res)

final_count = len(xg_selected_stocks)

print("---")
print(f"🎉 综合选股(XG)计算完成！")
print(f"📅 统计日期：{datetime.now().strftime('%Y-%m-%d')}")
print(f"📊 今日最终符合『双上+去ST+去新股』的股票总数： {final_count} 只")
print("---")
