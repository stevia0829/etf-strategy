"""
行情数据获取工具 - LangChain Tool 封装
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from langchain_core.tools import tool

from multi_agent.utils.data_source_adapter import DataSourceAdapter


@tool
def fetch_etf_price_data(etf_codes: List[str], days: int = 60) -> Dict[str, Any]:
    """获取 ETF 历史价格数据。

    Args:
        etf_codes: ETF 代码列表（JoinQuant 格式，如 '518880.XSHG'）
        days: 回看天数，默认 60 天

    Returns:
        {etf_code: {date: [...], close: [...], open: [...], high: [...], low: [...], volume: [...]}}
    """
    adapter = DataSourceAdapter()
    result = {}
    for code in etf_codes:
        try:
            df = adapter.get_etf_data(code, days=days)
            if not df.empty:
                result[code] = adapter.serialize_dataframe(df)
        except Exception as e:
            print(f"[market_data] 获取 {code} ETF数据失败: {e}")
    return result


@tool
def fetch_current_prices(symbols: List[str]) -> Dict[str, float]:
    """获取股票/ETF 最新价格。

    Args:
        symbols: 代码列表（JoinQuant 格式）

    Returns:
        {code: 最新价格}
    """
    adapter = DataSourceAdapter()
    return adapter.get_current_prices(symbols)


@tool
def fetch_market_index_data(index_codes: List[str]) -> Dict[str, Any]:
    """获取市场指数快照数据（沪深300、中证1000等）。

    Args:
        index_codes: 指数代码列表（JoinQuant 格式）

    Returns:
        {index_code: {close, change_pct, date}}
    """
    adapter = DataSourceAdapter()
    return adapter.get_market_index_data(index_codes)


def get_data_tools():
    """返回所有行情数据工具列表"""
    return [fetch_etf_price_data, fetch_current_prices, fetch_market_index_data]
