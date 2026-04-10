"""
Agent 1: 数据获取 Agent
从 AKShare/Baostock 获取 ETF 和市场指数数据，无 LLM 调用
"""
from typing import Dict, Any
from datetime import datetime

from multi_agent.state import TradingState
from multi_agent.utils.data_source_adapter import DataSourceAdapter


def data_agent_node(state: TradingState) -> dict:
    """数据获取 Agent 节点函数。

    从配置的数据源获取 ETF 历史价格、最新价格和市场指数数据。
    """
    print("[Data Agent] 开始获取行情数据...")
    run_date = state.get('run_date', datetime.now().strftime('%Y-%m-%d'))
    etf_pool = state.get('etf_pool', [])

    adapter = DataSourceAdapter()

    # 1. 获取 ETF 历史价格
    etf_prices = {}
    etf_current_prices = {}
    for code in etf_pool:
        try:
            df = adapter.get_etf_data(code, days=60)
            if not df.empty:
                etf_prices[code] = adapter.serialize_dataframe(df)
                # 最新收盘价
                if 'close' in df.columns:
                    etf_current_prices[code] = float(df['close'].iloc[-1])
        except Exception as e:
            print(f"[Data Agent] 获取 {code} 数据失败: {e}")

    print(f"[Data Agent] 成功获取 {len(etf_prices)} 只 ETF 的历史数据")

    # 2. 获取市场指数
    market_indices = {}
    default_indices = ['000300.XSHG', '399101.XSHE', '159536.XSHE']
    try:
        market_indices = adapter.get_market_index_data(default_indices)
    except Exception as e:
        print(f"[Data Agent] 获取市场指数失败: {e}")

    print(f"[Data Agent] 获取了 {len(market_indices)} 个市场指数")
    print("[Data Agent] 数据获取完成")

    return {
        'etf_prices': etf_prices,
        'etf_current_prices': etf_current_prices,
        'market_indices': market_indices,
    }
