import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time


def get_sector_adv(sector_code="300300"):
    """
    获取板块指数的实时涨幅（通达信 INDEXADV 的等效值）
    :param sector_code: 板块指数代码 (默认为人工智能板块 300300)
    :return: 板块涨幅 (数值，如 0.8 表示 0.8%)
    """
    try:
        # 获取板块指数行情
        sector_df = ak.index_zh_a_hist(symbol=sector_code, period="daily",
                                       start_date=(datetime.now() - timedelta(days=1)).strftime("%Y%m%d"),
                                       end_date=datetime.now().strftime("%Y%m%d"))
        if not sector_df.empty:
            # 计算涨幅（前一天的收盘价到当天的涨幅）
            prev_close = sector_df['收盘'].iloc[-2]
            current_close = sector_df['收盘'].iloc[-1]
            return (current_close - prev_close) / prev_close * 100
        return 0.0
    except Exception as e:
        print(f"获取板块涨幅失败: {e}")
        return 0.0


def get_stock_data(code, days=10):
    """
    获取股票历史K线数据 (包括收盘价、成交量等)
    :param code: 股票代码
    :param days: 获取历史天数
    :return: DataFrame 包含历史K线数据
    """
    try:
        # 获取股票历史数据
        stock_df = ak.stock_zh_a_hist(symbol=code, period="daily",
                                      start_date=(datetime.now() - timedelta(days=days + 1)).strftime("%Y%m%d"),
                                      end_date=datetime.now().strftime("%Y%m%d"))
        if not stock_df.empty:
            # 重命名列以便于计算
            stock_df = stock_df.rename(columns={
                "日期": "date",
                "开盘": "open",
                "最高": "high",
                "最低": "low",
                "收盘": "close",
                "成交量": "volume"
            })
            return stock_df
        return None
    except Exception as e:
        print(f"获取股票 {code} 数据失败: {e}")
        return None


def calculate_macd(df, fast=6, slow=13, signal=5):
    """
    计算MACD指标
    :param df: 包含收盘价的DataFrame
    :param fast: 快线周期
    :param slow: 慢线周期
    :param signal: 信号线周期
    :return: 包含MACD指标的DataFrame
    """
    # 计算EMA
    df['ema_fast'] = df['close'].ewm(span=fast, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=slow, adjust=False).mean()

    # MACD线
    df['macd'] = df['ema_fast'] - df['ema_slow']

    # 信号线
    df['macd_signal'] = df['macd'].ewm(span=signal, adjust=False).mean()

    # MACD柱
    df['macd_hist'] = df['macd'] - df['macd_signal']

    return df


def calculate_rsi(df, n=3):
    """
    计算RSI指标
    :param df: 包含收盘价的DataFrame
    :param n: RSI周期
    :return: 包含RSI的DataFrame
    """
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(n).mean()
    avg_loss = loss.rolling(n).mean()

    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    return df


def get_sector_stocks(sector_name="人工智能"):
    """
    获取特定板块的股票列表
    :param sector_name: 板块名称 (默认: 人工智能)
    :return: 股票代码列表
    """
    try:
        # 获取板块股票列表
        sector_df = ak.stock_sector_em()
        sector_stocks = sector_df[sector_df['板块'] == sector_name]
        return sector_stocks['代码'].tolist()
    except Exception as e:
        print(f"获取板块股票失败: {e}")
        return []


def is_st_stock(name):
    """
    判断是否为ST股
    :param name: 股票名称
    :return: True if ST stock, False otherwise
    """
    return "ST" in name or "*ST" in name


def calculate_market_cap(code):
    """
    获取股票总市值 (单位: 亿元)
    :param code: 股票代码
    :return: 总市值 (亿元)
    """
    try:
        # 获取股票基本信息
        stock_info = ak.stock_zh_a_spot()
        stock_info = stock_info[stock_info['代码'] == code]
        if not stock_info.empty:
            # 总市值 (单位: 元)
            market_cap = stock_info['总市值'].values[0]
            return market_cap / 10 ** 8  # 转换为亿元
        return 0.0
    except Exception as e:
        print(f"获取市值失败: {e}")
        return 0.0


def get_sector_adv_value():
    """
    获取板块涨幅值 (用于公式中的 SECTOR_ADV)
    :return: 板块涨幅 (数值)
    """
    # 使用人工智能板块 (300300) 作为代表
    return get_sector_adv(sector_code="300300")


def is_valid_stock(stock_code, sector_adv):
    """
    检查股票是否满足选股条件
    :param stock_code: 股票代码
    :param sector_adv: 板块涨幅
    :return: True if stock meets all conditions, False otherwise
    """
    # 获取股票数据 (最近10天)
    df = get_stock_data(stock_code, days=15)
    if df is None or len(df) < 10:
        return False

    # 计算MACD
    df = calculate_macd(df)

    # 计算RSI
    df = calculate_rsi(df)

    # 通达信公式条件检查
    # 1. 底背离条件 (BOTTOM_BACK)
    last_low = df['low'].iloc[-1]
    low_10 = df['low'].rolling(window=10).min().iloc[-1]
    macd_dif = df['macd'].iloc[-1]
    macd_dif_10 = df['macd'].iloc[-11]

    bottom_back = (last_low < low_10) and (macd_dif > macd_dif_10) and (macd_dif < 0.0001)

    # 2. 底背离确认 (BACK_CONF)
    macd_neg_3 = df['macd'].iloc[-4:-1] < 0.0001
    back_conf = (macd_neg_3.sum() >= 2) and bottom_back

    # 3. 趋势条件 (TREND_COND)
    ma10 = df['close'].rolling(10).mean().iloc[-1]
    ma30 = df['close'].rolling(30).mean().iloc[-1]
    ma30_up = ma30 > df['close'].rolling(30).mean().iloc[-2]

    trend_cond = (df['close'].rolling(10).mean() > df['close'].rolling(30).mean()).rolling(5).sum().iloc[
                     -1] >= 5 and ma30_up

    # 4. 回踩条件 (COND2)
    back_ratio = 0.90
    cond2 = (df['close'].iloc[-1] >= ma30 * back_ratio) and (df['close'].iloc[-1] <= ma30)

    # 5. 量能条件 (COND4)
    vol_10 = df['volume'].rolling(10).mean().iloc[-1]
    vol_25 = df['volume'].rolling(25).max().iloc[-1]
    vol_ratio_10 = 0.35
    vol_ratio_25 = 1.0

    cond4 = (df['volume'].iloc[-1] > vol_10 * vol_ratio_10) and (df['volume'].iloc[-1] < vol_25 * vol_ratio_25)

    # 6. 总市值条件 (COND5)
    market_cap = calculate_market_cap(stock_code)
    cond5 = market_cap > 10

    # 7. 涨幅条件 (COND6)
    prev_close = df['close'].iloc[-2]
    current_close = df['close'].iloc[-1]
    max_up_ratio = 15
    cond6 = (current_close / prev_close - 1) * 100 < max_up_ratio

    # 8. 非ST股条件 (COND7)
    stock_info = ak.stock_zh_a_spot()
    stock_name = stock_info[stock_info['代码'] == stock_code]['名称'].values[0]
    cond7 = not is_st_stock(stock_name)

    # 9. 板块条件 (COND8)
    cond8 = sector_adv > 0.0001

    # 10. 波动率过滤 (VOL_FILTER)
    vol_rate = df['close'].rolling(20).std().iloc[-1] / df['close'].rolling(20).mean().iloc[-1] * 100
    vol_filter = vol_rate < 30

    # 所有条件满足
    return (trend_cond and back_conf and cond2 and cond4 and cond5 and cond6 and cond7 and cond8 and vol_filter)


def run_daily_selection():
    """
    每日自动运行选股
    """
    print(f"{'=' * 50}")
    print(f"【A股每日选股系统】运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 50}")

    # 1. 获取板块涨幅
    sector_adv = get_sector_adv_value()
    print(f"板块涨幅: {sector_adv:.2f}%")

    # 2. 获取板块股票列表
    sector_stocks = get_sector_stocks(sector_name="人工智能")
    print(f"板块股票数量: {len(sector_stocks)}")

    # 3. 逐个检查股票
    valid_stocks = []
    for i, stock in enumerate(sector_stocks, 1):
        print(f"正在检查股票 {i}/{len(sector_stocks)}: {stock}")
        if is_valid_stock(stock, sector_adv):
            valid_stocks.append(stock)

    # 4. 输出结果
    print(f"\n{'=' * 50}")
    print(f"【选股结果】")
    print(f"有效股票数量: {len(valid_stocks)}")
    if valid_stocks:
        print("有效股票列表:")
        for stock in valid_stocks:
            print(f"  - {stock}")
    else:
        print("未找到符合条件的股票")

    # 5. 保存结果到文件
    if valid_stocks:
        result_df = pd.DataFrame(valid_stocks, columns=['股票代码'])
        result_df.to_csv(f"stock_selection_{datetime.now().strftime('%Y%m%d')}.csv", index=False)
        print(f"\n选股结果已保存至: stock_selection_{datetime.now().strftime('%Y%m%d')}.csv")

    print(f"{'=' * 50}")
    return valid_stocks


if __name__ == "__main__":
    # 每天早上9:00自动运行 (模拟)
    print("正在启动每日选股系统...")
    time.sleep(1)  # 简单模拟延迟

    # 实际运行时，可以设置为每天9:00自动运行
    valid_stocks = run_daily_selection()

    # 如果没有股票，尝试放宽条件
    if not valid_stocks:
        print("\n【警告】未找到有效股票，尝试放宽条件...")
        # 简化版：仅检查板块条件和回踩条件
        valid_stocks = []
        for i, stock in enumerate(sector_stocks, 1):
            print(f"正在检查股票 {i}/{len(sector_stocks)}: {stock}")
            # 简化条件检查
            if sector_adv > 0.0001:  # 板块条件
                valid_stocks.append(stock)

        if valid_stocks:
            print(f"\n【简化版】找到 {len(valid_stocks)} 只股票")
            # 保存简化结果
            result_df = pd.DataFrame(valid_stocks, columns=['股票代码'])
            result_df.to_csv(f"stock_selection_simple_{datetime.now().strftime('%Y%m%d')}.csv", index=False)
        else:
            print("【警告】即使放宽条件，仍未找到有效股票")

    print("\n选股系统运行完成!")