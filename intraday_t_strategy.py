import pandas as pd
import talib
import time

# 全局变量
monitor_duration = 60  # MACD 监控时长（分钟），可调节
buy_funds_ratio = 0.5  # 买入金额占账户可用资金比例，可调节
sell_holding_ratio = 0.5  # 卖出持仓量比例，可调节

def initialize(context):
    # 初始化函数，在策略开始时调用
    context.symbol = '000001.SZ'  # 交易的股票代码，可根据需要修改
    context.last_buy_time = None
    context.last_sell_time = None

def handle_bar(context, bar_dict):
    # 每个 bar 数据更新时调用
    symbol = context.symbol
    # 获取历史数据
    hist_data = history_bars(symbol, monitor_duration * 60, '1m', ['close', 'high', 'low'])
    if len(hist_data) < 34:  # MACD 计算至少需要 34 个数据点
        return

    close_prices = hist_data['close']
    high_prices = hist_data['high']
    low_prices = hist_data['low']

    # 计算 MACD
    macd, signal, hist = talib.MACD(close_prices, fastperiod=12, slowperiod=26, signalperiod=9)

    # 买点判断
    if len(low_prices) > 0 and len(macd) > 0:
        current_low = low_prices[-1]
        min_low = low_prices.min()
        current_macd = macd[-1]
        min_macd = macd.min()
        if current_low == min_low and current_macd > min_macd and macd[-1] > signal[-1] and macd[-2] <= signal[-2]:
            # 满足买点条件，进行买入操作
            available_funds = context.account.cash
            buy_amount = available_funds * buy_funds_ratio
            current_price = bar_dict[symbol].close
            volume = int(buy_amount / current_price)
            if volume > 0:
                order_volume(symbol, volume, OrderType_Market)
                context.last_buy_time = time.time()

    # 卖点判断
    if len(high_prices) > 0 and len(macd) > 0:
        current_high = high_prices[-1]
        max_high = high_prices.max()
        current_macd = macd[-1]
        max_macd = macd.max()
        if current_high == max_high and current_macd < max_macd:
            # 满足卖点条件，进行卖出操作
            holding_volume = context.account.position(symbol).volume
            sell_volume = int(holding_volume * sell_holding_ratio)
            if sell_volume > 0:
                order_volume(symbol, -sell_volume, OrderType_Market)
                context.last_sell_time = time.time()

    # 强制卖点判断：盘中 15 秒内快速下跌 3% 及以上
    recent_prices = history_bars(symbol, 15, '1s', ['close'])
    if len(recent_prices) == 15:
        start_price = recent_prices[0]['close']
        end_price = recent_prices[-1]['close']
        if (start_price - end_price) / start_price >= 0.03:
            holding_volume = context.account.position(symbol).volume
            if holding_volume > 0:
                order_volume(symbol, -holding_volume, OrderType_Market)
                context.last_sell_time = time.time()

    # 强制卖出：跌破 5 日线（14:45 分）
    current_time = pd.Timestamp.now()
    if current_time.hour == 14 and current_time.minute == 45:
        five_day_data = history_bars(symbol, 5, '1d', ['close'])
        if len(five_day_data) == 5:
            five_day_avg = five_day_data['close'].mean()
            current_price = bar_dict[symbol].close
            if current_price < five_day_avg:
                holding_volume = context.account.position(symbol).volume
                if holding_volume > 0:
                    order_volume(symbol, -holding_volume, OrderType_Market)
                    context.last_sell_time = time.time()