"""
LangGraph 图定义与编排

流程: START → Data Agent → ┬→ News Agent ──→ Decision Agent → END
                            └→ Strategy Agent ┘

News Agent 和 Strategy Agent 并行执行。
"""
import yaml
import os
from functools import partial
from typing import Optional

from langgraph.graph import StateGraph, END

from multi_agent.state import TradingState
from multi_agent.agents.data_agent import data_agent_node
from multi_agent.agents.news_agent import news_agent_node
from multi_agent.agents.strategy_agent import strategy_agent_node
from multi_agent.agents.decision_agent import decision_agent_node


def load_config(config_path: Optional[str] = None) -> dict:
    """加载配置文件"""
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')

    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_etf_pool(config: dict) -> list:
    """从配置中提取 ETF 代码列表（轮动池 + 反弹池）"""
    pools = config.get('etf_pools', {})
    codes = []
    for pool_name, items in pools.items():
        for item in items:
            code = item.get('code', '')
            if code and code not in codes:
                codes.append(code)
    return codes


def build_trading_graph(llm_config: Optional[dict] = None) -> StateGraph:
    """构建交易分析 LangGraph 图。

    Args:
        llm_config: LLM 配置（provider, model 等），不传则从 config.yaml 读取

    Returns:
        编译后的 LangGraph 图
    """
    config = load_config()
    if llm_config is None:
        llm_config = config.get('llm', {})

    # 用 partial 注入配置到需要 LLM 的 agent
    news_node = partial(news_agent_node, config=llm_config)
    decision_node = partial(decision_agent_node, config=llm_config)

    # 构建图
    graph = StateGraph(TradingState)

    graph.add_node("data_agent", data_agent_node)
    graph.add_node("news_agent", news_node)
    graph.add_node("strategy_agent", strategy_agent_node)
    graph.add_node("decision_agent", decision_node)

    # 入口
    graph.set_entry_point("data_agent")

    # Data Agent 完成后，News 和 Strategy 并行
    graph.add_edge("data_agent", "news_agent")
    graph.add_edge("data_agent", "strategy_agent")

    # 两个都完成后，进入 Decision
    graph.add_edge("news_agent", "decision_agent")
    graph.add_edge("strategy_agent", "decision_agent")

    # Decision 完成后结束
    graph.add_edge("decision_agent", END)

    return graph.compile()
