"""
策略计算工具 - 动量得分、MACD、RSI、ETF反弹检测
核心算法从 cibo_strategy.py 和 cibo_strategy_standalone_fixed_enhanced.py 提取
"""
import math
from typing import Dict, List, Tuple, Any, Optional

import numpy as np
import pandas as pd
from langchain_core.tools import tool


@tool
def calculate_weighted_momentum(prices: List[float], days: int = 21) -> float:
    """计算加权对数线性回归动量得分（cibo_strategy.py 核心算法）。

    对价格取对数后做加权线性回归，用年化收益率乘以R²作为最终得分。
    权重从1线性递增到2，越近期的数据权重越大。

    Args:
        prices: 收盘价序列（从旧到新）
        days: 计算窗口天数，默认 21

    Returns:
        动量得分（年化收益率 × R²）
    """
    if len(prices) < days:
        return 0.0

    recent = prices[-days:]
    y = np.log(recent)
    x = np.arange(len(y))
    weights = np.linspace(1, 2, len(y))

    try:
        slope, intercept = np.polyfit(x, y, 1, w=weights)
    except Exception:
        return 0.0

    annualized_returns = math.exp(slope * 250) - 1

    fitted = slope * x + intercept
    ss_res = np.sum(weights * (y - fitted) ** 2)
    ss_tot = np.sum(weights * (y - np.average(y, weights=weights)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    return float(annualized_returns * r2)


@tool
def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, Any]:
    """计算 MACD 指标。

    Args:
        prices: 收盘价序列（从旧到新）
        fast: 快线周期，默认 12
        slow: 慢线周期，默认 26
        signal: 信号线周期，默认 9

    Returns:
        {dif: float, dea: float, hist: float, signal: str}
        signal: 'golden_cross'(金叉) / 'death_cross'(死叉) / 'neutral'
    """
    if len(prices) < slow + signal:
        return {'dif': 0, 'dea': 0, 'hist': 0, 'signal': 'insufficient_data'}

    s = pd.Series(prices)
    ema_fast = s.ewm(span=fast, adjust=False).mean()
    ema_slow = s.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    hist = (dif - dea) * 2

    last_dif = float(dif.iloc[-1])
    last_dea = float(dea.iloc[-1])
    last_hist = float(hist.iloc[-1])

    # 判断金叉/死叉
    if len(dif) >= 2:
        prev_hist = float(hist.iloc[-2])
        if prev_hist <= 0 and last_hist > 0:
            cross_signal = 'golden_cross'
        elif prev_hist >= 0 and last_hist < 0:
            cross_signal = 'death_cross'
        else:
            cross_signal = 'neutral'
    else:
        cross_signal = 'neutral'

    return {
        'dif': round(last_dif, 4),
        'dea': round(last_dea, 4),
        'hist': round(last_hist, 4),
        'signal': cross_signal
    }


@tool
def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """计算 RSI 指标。

    Args:
        prices: 收盘价序列（从旧到新）
        period: RSI 周期，默认 14

    Returns:
        RSI 值（0-100）
    """
    if len(prices) < period + 1:
        return 50.0

    s = pd.Series(prices)
    delta = s.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss.replace(0, float('inf'))
    rsi = 100 - (100 / (1 + rs))

    val = rsi.iloc[-1]
    return float(val) if not pd.isna(val) else 50.0


@tool
def rank_etfs_by_momentum(etf_prices: Dict[str, List[float]], days: int = 21) -> List[str]:
    """对 ETF 池按动量得分排名。

    Args:
        etf_prices: {etf_code: 收盘价列表}
        days: 动量计算窗口

    Returns:
        按动量得分降序排列的 ETF 代码列表
    """
    scores = {}
    for code, prices in etf_prices.items():
        if isinstance(prices, list) and len(prices) >= days:
            scores[code] = calculate_weighted_momentum.invoke({
                'prices': prices, 'days': days
            })
        else:
            scores[code] = 0.0

    return sorted(scores.keys(), key=lambda x: scores[x], reverse=True)


@tool
def detect_etf_bounce(prices: List[float], opens: List[float],
                       highs: List[float], lookback: int = 5,
                       drop_threshold: float = 0.98,
                       recover_threshold: float = 1.01) -> bool:
    """检测 ETF 反弹信号（策略2核心逻辑）。

    条件: 今日开盘价 < 近期最高价 × drop_threshold 且 当前价 > 开盘价 × recover_threshold

    Args:
        prices: 收盘价序列
        opens: 开盘价序列
        highs: 最高价序列
        lookback: 回看天数
        drop_threshold: 下跌阈值，默认 0.98
        recover_threshold: 反弹阈值，默认 1.01

    Returns:
        是否满足反弹条件
    """
    if len(prices) < lookback + 1 or len(opens) < 1 or len(highs) < lookback:
        return False

    recent_high_max = max(highs[-lookback:])
    today_open = opens[-1]
    current_price = prices[-1]

    dropped = today_open / recent_high_max < drop_threshold
    recovered = current_price / today_open > recover_threshold

    return dropped and recovered


def get_strategy_tools():
    """返回所有策略计算工具列表"""
    return [calculate_weighted_momentum, calculate_macd, calculate_rsi,
            rank_etfs_by_momentum, detect_etf_bounce]
