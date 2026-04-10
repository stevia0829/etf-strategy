"""
Agent 4: 综合决策 Agent
综合动量信号和新闻风险，使用 LLM 做出最终推荐并推送
"""
import json
from typing import Dict, Any

from multi_agent.state import TradingState
from multi_agent.tools.notification_tools import send_wechat_webhook, send_dingtalk_webhook
from multi_agent.prompts.decision_prompt import (
    DECISION_SYSTEM_PROMPT,
    DECISION_USER_TEMPLATE,
)


# ETF 代码到名称的映射
ETF_NAMES = {
    '518880.XSHG': '黄金ETF', '161226.XSHE': '白银基金', '501018.XSHG': '南方原油',
    '159985.XSHE': '豆粕ETF', '513520.XSHG': '日经ETF', '513100.XSHG': '纳指100',
    '513300.XSHG': '纳斯达克ETF', '513400.XSHG': '道琼斯ETF', '513030.XSHG': '德国30',
    '513130.XSHG': '恒生科技ETF', '512480.XSHG': '半导体', '512760.XSHG': '存储芯片',
    '515880.XSHG': '通信ETF', '515230.XSHG': '软件ETF', '515050.XSHG': '5GETF',
    '159819.XSHE': '人工智能', '562500.XSHG': '机器人', '159915.XSHE': '创业板ETF',
    '159536.XSHE': '中证2000', '159629.XSHE': '中证1000', '159922.XSHE': '中证500',
    '159919.XSHE': '沪深300', '159783.XSHE': '双创50', '000300.XSHG': '沪深300指数',
    '399101.XSHE': '中证1000指数',
}


def _get_name(code: str) -> str:
    return ETF_NAMES.get(code, code[:6])


def _call_llm(system_prompt: str, user_prompt: str, config: dict) -> str:
    """调用 LLM"""
    provider = config.get('provider', 'openai')
    model = config.get('model', 'gpt-4o-mini')

    if provider == 'anthropic':
        from langchain_anthropic import ChatAnthropic
        llm = ChatAnthropic(model=model, temperature=0.1, max_tokens=2000)
    else:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model=model, temperature=0.1, max_tokens=2000)

    from langchain_core.messages import SystemMessage, HumanMessage
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ])
    return response.content


def _parse_llm_json(text: str) -> dict:
    """从 LLM 回复中提取 JSON"""
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


def _format_notification(state: TradingState, recommendations: list, risk_assessment: str) -> str:
    """格式化推送消息（Markdown）"""
    run_date = state.get('run_date', '')
    etf_ranking = state.get('etf_ranking', [])
    momentum_scores = state.get('momentum_scores', {})
    rsi_values = state.get('rsi_values', {})
    macd_signals = state.get('macd_signals', {})
    news_risk_score = state.get('news_risk_score', 5.0)

    lines = [
        f"### ETF策略分析报告 ({run_date})",
        "",
        "#### 动量排名 TOP 5",
    ]
    for i, code in enumerate(etf_ranking[:5], 1):
        name = _get_name(code)
        score = momentum_scores.get(code, 0)
        rsi = rsi_values.get(code, '-')
        lines.append(f"{i}. **{name}** ({code[:6]}) - 动量: {score:.2f}, RSI: {rsi}")

    lines.append("")
    lines.append(f"#### 新闻风险评分: {news_risk_score}/10")
    lines.append("")

    if recommendations:
        lines.append("#### 投资建议")
        for rec in recommendations[:5]:
            symbol = rec.get('symbol', '')
            name = rec.get('name', _get_name(symbol))
            action = rec.get('action', 'HOLD')
            confidence = rec.get('confidence', 0)
            risk = rec.get('risk_level', 'MEDIUM')
            reason = rec.get('reason', '')
            emoji = {'BUY': '🟢', 'SELL': '🔴', 'HOLD': '🟡'}.get(action, '⚪')
            lines.append(f"- {emoji} **{action}** {name}: {reason} (信心:{confidence:.0%}, 风险:{risk})")

    lines.append("")
    lines.append("#### 风险评估")
    lines.append(risk_assessment)

    return '\n'.join(lines)


def decision_agent_node(state: TradingState, config: dict = None) -> dict:
    """综合决策 Agent 节点函数。

    综合技术面和消息面做出推荐，推送通知。
    """
    print("[Decision Agent] 开始综合决策...")

    default_config = {
        'provider': 'openai',
        'model': 'gpt-4o-mini',
        'temperature': 0.1,
        'max_tokens': 2000,
    }
    llm_config = config or default_config

    etf_ranking = state.get('etf_ranking', [])
    momentum_scores = state.get('momentum_scores', {})
    macd_signals = state.get('macd_signals', {})
    rsi_values = state.get('rsi_values', {})
    strategy_signals = state.get('strategy_signals', {})
    news_risk_score = state.get('news_risk_score', 5.0)
    geopolitical_risks = state.get('geopolitical_risks', '暂无')
    sector_sentiment = state.get('sector_sentiment', {})
    financial_news = state.get('financial_news', [])
    market_indices = state.get('market_indices', {})

    # 1. 构建排名表
    ranking_lines = []
    for i, code in enumerate(etf_ranking[:10], 1):
        name = _get_name(code)
        score = momentum_scores.get(code, 0)
        rsi = rsi_values.get(code, '-')
        macd_sig = macd_signals.get(code, {}).get('signal', '-')
        ranking_lines.append(f"{i}. {name}({code[:6]}) - 动量:{score:.2f} RSI:{rsi} MACD:{macd_sig}")
    etf_ranking_table = '\n'.join(ranking_lines)

    # 2. 技术指标汇总
    tech_lines = []
    for code in etf_ranking[:10]:
        sig = strategy_signals.get(code, {})
        tech_lines.append(f"- {code[:6]}: {sig.get('action', '-')} ({sig.get('reason', '-')})")
    technical_summary = '\n'.join(tech_lines)

    # 3. 市场指数
    market_lines = []
    for code, data in market_indices.items():
        name = _get_name(code)
        market_lines.append(f"- {name}: {data.get('close', '-')} ({data.get('change_pct', '-')}%)")
    market_summary = '\n'.join(market_lines)

    # 4. 尾部风险
    tail_risks = []
    for n in financial_news[:3]:
        tail_risks.append(n.get('title', ''))
    tail_risks_str = '; '.join(tail_risks) if tail_risks else '暂无'

    # 5. LLM 决策
    user_prompt = DECISION_USER_TEMPLATE.format(
        etf_ranking_table=etf_ranking_table,
        technical_summary=technical_summary,
        risk_score=news_risk_score,
        geopolitical_risks=geopolitical_risks,
        sector_sentiment=json.dumps(sector_sentiment, ensure_ascii=False),
        tail_risks=tail_risks_str,
        market_summary=market_summary,
    )

    try:
        llm_response = _call_llm(DECISION_SYSTEM_PROMPT, user_prompt, llm_config)
        analysis = _parse_llm_json(llm_response)
    except Exception as e:
        print(f"[Decision Agent] LLM 决策失败: {e}，使用规则决策")
        analysis = {}

    # 6. 提取推荐
    recommendations = analysis.get('recommendations', [])
    risk_assessment = analysis.get('risk_assessment', analysis.get('overall_assessment', '暂无评估'))

    # 如果 LLM 没返回推荐，用规则生成
    if not recommendations:
        recommendations = _rule_based_decision(state)

    print(f"[Decision Agent] 生成了 {len(recommendations)} 条推荐")

    # 7. 格式化并推送
    notification_payload = _format_notification(state, recommendations, risk_assessment)
    notification_sent = False

    # 尝试推送（从环境变量或 config 获取 webhook URL）
    import os
    wechat_url = os.environ.get('WECHAT_WEBHOOK_URL', '')
    dingtalk_url = os.environ.get('DINGTALK_WEBHOOK_URL', '')

    if wechat_url:
        notification_sent = send_wechat_webhook.invoke({
            'webhook_url': wechat_url,
            'message': notification_payload,
        }) or notification_sent

    if dingtalk_url:
        notification_sent = send_dingtalk_webhook.invoke({
            'webhook_url': dingtalk_url,
            'message': notification_payload,
        }) or notification_sent

    if not wechat_url and not dingtalk_url:
        print("[Decision Agent] 未配置 Webhook URL，跳过推送")

    print("[Decision Agent] 决策完成")
    print(f"\n{notification_payload}")

    return {
        'final_recommendations': recommendations,
        'risk_assessment': risk_assessment,
        'notification_sent': notification_sent,
        'notification_payload': notification_payload,
    }


def _rule_based_decision(state: TradingState) -> list:
    """规则决策：当 LLM 不可用时的回退方案"""
    recommendations = []
    etf_ranking = state.get('etf_ranking', [])
    momentum_scores = state.get('momentum_scores', {})
    rsi_values = state.get('rsi_values', {})
    strategy_signals = state.get('strategy_signals', {})
    news_risk_score = state.get('news_risk_score', 5.0)

    for code in etf_ranking[:5]:
        score = momentum_scores.get(code, 0)
        rsi = rsi_values.get(code, 50)
        sig = strategy_signals.get(code, {})
        action = sig.get('action', 'HOLD')

        # 风险高时降低信心
        confidence = 0.7
        risk_level = 'MEDIUM'
        if news_risk_score > 7:
            confidence = 0.4
            risk_level = 'HIGH'
        elif news_risk_score < 3:
            confidence = 0.85
            risk_level = 'LOW'

        recommendations.append({
            'symbol': code,
            'name': _get_name(code),
            'action': action,
            'reason': sig.get('reason', '动量排名靠前'),
            'confidence': confidence,
            'risk_level': risk_level,
        })

    return recommendations
