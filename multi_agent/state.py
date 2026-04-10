"""
LangGraph 共享状态定义
"""
from typing import TypedDict, List, Dict, Any, Optional


class TradingState(TypedDict, total=False):
    """多 Agent 交易分析系统的共享状态"""

    # --- 输入 ---
    run_date: str                           # 运行日期 ISO格式 "2026-04-10"
    etf_pool: List[str]                     # 要分析的 ETF 代码列表
    stock_pool: List[str]                   # 可选的股票代码列表

    # --- Data Agent 输出 ---
    etf_prices: Dict[str, Any]             # {etf_code: {dates:[], close:[], open:[], ...}}
    etf_current_prices: Dict[str, float]   # {etf_code: 最新收盘价}
    market_indices: Dict[str, Any]         # {index_code: {close, change_pct, ...}}

    # --- News Agent 输出 ---
    financial_news: List[Dict[str, str]]   # [{title, content, source, date}]
    geopolitical_risks: str                # LLM 总结的地缘风险段落
    sector_sentiment: Dict[str, str]       # {板块: bullish/bearish/neutral}
    news_risk_score: float                 # 0-10 综合风险分

    # --- Strategy Agent 输出 ---
    momentum_scores: Dict[str, float]      # {etf_code: 动量得分}
    macd_signals: Dict[str, Dict]          # {etf_code: {dif, dea, hist, signal}}
    rsi_values: Dict[str, float]           # {etf_code: rsi值}
    etf_ranking: List[str]                 # 按动量得分降序排列的 ETF 列表
    etf_bounce_candidates: List[str]       # 满足反弹条件的 ETF
    strategy_signals: Dict[str, Any]       # {etf_code: {action, reason}}

    # --- Decision Agent 输出 ---
    final_recommendations: List[Dict[str, Any]]  # [{symbol, name, action, reason, confidence, risk_level}]
    risk_assessment: str                   # LLM 生成的整体风险段落
    notification_sent: bool                # 推送是否成功
    notification_payload: str              # 推送的 Markdown 内容
