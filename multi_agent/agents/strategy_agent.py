"""
Agent 3: 策略信号计算 Agent
计算动量得分、MACD、RSI、ETF排名等，纯计算无 LLM 调用
"""
from typing import Dict, Any, List

from multi_agent.state import TradingState
from multi_agent.tools.strategy_tools import (
    calculate_weighted_momentum,
    calculate_macd,
    calculate_rsi,
    detect_etf_bounce,
)


def strategy_agent_node(state: TradingState) -> dict:
    """策略信号计算 Agent 节点函数。

    对每只 ETF 计算动量得分、MACD、RSI，生成排名和信号。
    """
    print("[Strategy Agent] 开始计算策略信号...")
    etf_prices = state.get('etf_prices', {})

    momentum_scores = {}
    macd_signals = {}
    rsi_values = {}
    etf_bounce_candidates = []
    strategy_signals = {}

    for code, price_data in etf_prices.items():
        close_prices = price_data.get('close', [])
        open_prices = price_data.get('open', [])
        high_prices = price_data.get('high', [])

        if not close_prices or len(close_prices) < 26:
            continue

        # 1. 动量得分
        score = calculate_weighted_momentum.invoke({'prices': close_prices, 'days': 21})
        momentum_scores[code] = round(score, 4)

        # 2. MACD
        macd = calculate_macd.invoke({'prices': close_prices, 'fast': 12, 'slow': 26, 'signal': 9})
        macd_signals[code] = macd

        # 3. RSI
        rsi = calculate_rsi.invoke({'prices': close_prices, 'period': 14})
        rsi_values[code] = round(rsi, 2)

        # 4. ETF 反弹检测
        if open_prices and high_prices:
            is_bounce = detect_etf_bounce.invoke({
                'prices': close_prices,
                'opens': open_prices,
                'highs': high_prices,
            })
            if is_bounce:
                etf_bounce_candidates.append(code)

        # 5. 综合信号
        action = 'HOLD'
        reasons = []

        if score > 0.5:
            action = 'BUY'
            reasons.append(f'动量得分{score:.2f}为正')
        elif score < -0.2:
            action = 'SELL'
            reasons.append(f'动量得分{score:.2f}为负')

        if macd['signal'] == 'golden_cross':
            action = 'BUY'
            reasons.append('MACD金叉')
        elif macd['signal'] == 'death_cross':
            reasons.append('MACD死叉')

        if rsi > 70:
            reasons.append(f'RSI={rsi:.1f}超买')
            if action == 'BUY':
                action = 'HOLD'
        elif rsi < 30:
            reasons.append(f'RSI={rsi:.1f}超卖')

        strategy_signals[code] = {
            'action': action,
            'reason': '; '.join(reasons) if reasons else '无明显信号',
        }

    # 6. ETF 动量排名
    etf_ranking = sorted(momentum_scores.keys(), key=lambda x: momentum_scores[x], reverse=True)

    print(f"[Strategy Agent] 计算了 {len(momentum_scores)} 只 ETF 的信号")
    print(f"[Strategy Agent] 动量排名前3: {etf_ranking[:3]}")
    print(f"[Strategy Agent] 反弹候选: {etf_bounce_candidates}")
    print("[Strategy Agent] 策略计算完成")

    return {
        'momentum_scores': momentum_scores,
        'macd_signals': macd_signals,
        'rsi_values': rsi_values,
        'etf_ranking': etf_ranking,
        'etf_bounce_candidates': etf_bounce_candidates,
        'strategy_signals': strategy_signals,
    }
