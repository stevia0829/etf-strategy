"""
Agent 2: 新闻+地缘风险分析 Agent
聚合多源新闻，使用 LLM 进行风险分析
"""
import json
from typing import Dict, Any

from multi_agent.state import TradingState
from multi_agent.tools.news_tools import fetch_financial_news, fetch_sector_news, search_web
from multi_agent.prompts.news_analysis_prompt import (
    NEWS_ANALYSIS_SYSTEM_PROMPT,
    NEWS_ANALYSIS_USER_TEMPLATE,
)


def _call_llm(system_prompt: str, user_prompt: str, config: dict) -> str:
    """调用 LLM，支持 OpenAI 和 Anthropic"""
    provider = config.get('provider', 'openai')
    model = config.get('model', 'gpt-4o-mini')
    temperature = config.get('temperature', 0.1)
    max_tokens = config.get('max_tokens', 2000)

    if provider == 'anthropic':
        from langchain_anthropic import ChatAnthropic
        llm = ChatAnthropic(model=model, temperature=temperature, max_tokens=max_tokens)
    else:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model=model, temperature=temperature, max_tokens=max_tokens)

    from langchain_core.messages import SystemMessage, HumanMessage
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ])
    return response.content


def _parse_llm_json(text: str) -> dict:
    """从 LLM 回复中提取 JSON"""
    # 尝试提取 ```json ... ``` 代码块
    if '```json' in text:
        start = text.index('```json') + 7
        end = text.index('```', start)
        text = text[start:end].strip()
    elif '```' in text:
        start = text.index('```') + 3
        end = text.index('```', start)
        text = text[start:end].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def news_agent_node(state: TradingState, config: dict = None) -> dict:
    """新闻分析 Agent 节点函数。

    聚合多源新闻，使用 LLM 分析地缘风险和板块情绪。
    """
    print("[News Agent] 开始获取和分析新闻...")

    default_config = {
        'provider': 'openai',
        'model': 'gpt-4o-mini',
        'temperature': 0.1,
        'max_tokens': 2000,
    }
    llm_config = config or default_config

    sector_keywords = state.get('sector_keywords', {
        '黄金': ['黄金', '贵金属'],
        '原油': ['原油', '石油'],
        '半导体': ['芯片', '半导体', '制裁'],
        '科技': ['AI', '人工智能', '科技'],
    })

    # 1. 获取财经新闻
    news = fetch_financial_news.invoke({'limit': 20})
    print(f"[News Agent] 获取了 {len(news)} 条财经新闻")

    # 2. 获取板块新闻
    sector_news = fetch_sector_news.invoke({
        'sector_keywords': sector_keywords,
        'limit': 5,
    })
    print(f"[News Agent] 获取了 {len(sector_news)} 个板块的新闻")

    # 3. 网络搜索地缘政治
    geopolitical_results = []
    for query in ['中美贸易 最新消息', '国际政治 金融市场风险']:
        results = search_web.invoke({'query': query, 'max_results': 3})
        geopolitical_results.extend(results)

    # 4. 格式化新闻内容给 LLM
    news_content = '\n'.join([
        f"- [{n.get('source')}] {n.get('title', '')} ({n.get('date', '')})"
        for n in news[:15]
    ])

    sector_news_parts = []
    for sector, articles in sector_news.items():
        titles = '; '.join([a.get('title', '') for a in articles[:3]])
        sector_news_parts.append(f"  {sector}: {titles}")
    sector_news_content = '\n'.join(sector_news_parts)

    geo_parts = []
    for r in geopolitical_results[:5]:
        geo_parts.append(f"- {r.get('title', '')}: {r.get('content', '')[:100]}")
    geopolitical_content = '\n'.join(geo_parts)

    sectors = ', '.join(sector_keywords.keys())

    # 5. LLM 分析
    user_prompt = NEWS_ANALYSIS_USER_TEMPLATE.format(
        news_content=news_content or '暂无新闻数据',
        sector_news_content=sector_news_content or '暂无板块新闻',
        geopolitical_content=geopolitical_content or '暂无地缘政治搜索结果',
        sectors=sectors,
    )

    try:
        llm_response = _call_llm(NEWS_ANALYSIS_SYSTEM_PROMPT, user_prompt, llm_config)
        analysis = _parse_llm_json(llm_response)
    except Exception as e:
        print(f"[News Agent] LLM 分析失败: {e}，使用默认值")
        analysis = {}

    # 6. 提取结果
    financial_news = news[:10]
    geopolitical_risks = analysis.get('geopolitical_summary', '暂无分析')
    sector_sentiment = analysis.get('sector_sentiment', {})
    news_risk_score = float(analysis.get('geopolitical_risk_score', 5.0))

    print(f"[News Agent] 风险评分: {news_risk_score}/10")
    print(f"[News Agent] 板块情绪: {sector_sentiment}")
    print("[News Agent] 新闻分析完成")

    return {
        'financial_news': financial_news,
        'geopolitical_risks': geopolitical_risks,
        'sector_sentiment': sector_sentiment,
        'news_risk_score': news_risk_score,
    }
