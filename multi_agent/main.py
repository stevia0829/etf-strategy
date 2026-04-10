"""
Multi-Agent ETF 策略分析框架 - 入口脚本

用法:
    python -m multi_agent.main                    # 今日分析
    python -m multi_agent.main --date 2026-04-09  # 指定日期
    python -m multi_agent.main --dry-run          # Dry-run 模式（不走LLM，不推送）
"""
import argparse
import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser(description='Multi-Agent ETF 策略分析框架')
    parser.add_argument('--date', type=str, default=None,
                        help='指定运行日期 (YYYY-MM-DD)，默认为今天')
    parser.add_argument('--dry-run', action='store_true',
                        help='Dry-run 模式：跳过 LLM 调用和推送')
    parser.add_argument('--config', type=str, default=None,
                        help='配置文件路径')
    return parser.parse_args()


def run_dry_mode(etf_pool: list, run_date: str):
    """Dry-run 模式：只运行 Data Agent + Strategy Agent，跳过 LLM 和推送"""
    from multi_agent.agents.data_agent import data_agent_node
    from multi_agent.agents.strategy_agent import strategy_agent_node

    print("=" * 60)
    print(f"[DRY-RUN] ETF 策略分析 {run_date}")
    print("=" * 60)

    # Step 1: 获取数据
    state = {
        'run_date': run_date,
        'etf_pool': etf_pool,
    }
    data_result = data_agent_node(state)
    state.update(data_result)

    # Step 2: 策略计算
    strategy_result = strategy_agent_node(state)
    state.update(strategy_result)

    # 打印结果
    print("\n" + "=" * 60)
    print("DRY-RUN 结果摘要")
    print("=" * 60)

    ranking = state.get('etf_ranking', [])
    scores = state.get('momentum_scores', {})
    rsi = state.get('rsi_values', {})
    signals = state.get('strategy_signals', {})

    print(f"\n动量排名 TOP 10:")
    for i, code in enumerate(ranking[:10], 1):
        score = scores.get(code, 0)
        r = rsi.get(code, '-')
        sig = signals.get(code, {})
        print(f"  {i}. {code} - 动量: {score:.4f}, RSI: {r}, 信号: {sig.get('action', '-')}")

    bounce = state.get('etf_bounce_candidates', [])
    if bounce:
        print(f"\n反弹候选: {bounce}")

    market = state.get('market_indices', {})
    if market:
        print(f"\n市场指数:")
        for code, data in market.items():
            print(f"  {code}: {data.get('close', '-')} ({data.get('change_pct', '-')}%)")

    print("\n" + "=" * 60)
    print("DRY-RUN 完成（跳过了 LLM 分析和推送）")
    print("=" * 60)


def run_full_mode(etf_pool: list, run_date: str):
    """完整模式：运行所有 Agent"""
    from multi_agent.graph import build_trading_graph

    print("=" * 60)
    print(f"ETF 策略分析 {run_date}")
    print("=" * 60)

    # 构建图
    graph = build_trading_graph()

    # 初始状态
    initial_state = {
        'run_date': run_date,
        'etf_pool': etf_pool,
    }

    # 运行
    start_time = time.time()
    result = graph.invoke(initial_state)
    elapsed = time.time() - start_time

    print(f"\n分析完成，耗时 {elapsed:.1f}s")

    if result.get('notification_sent'):
        print("推送通知已发送")
    else:
        print("未发送推送通知")

    return result


def main():
    args = parse_args()

    # 加载配置
    from multi_agent.graph import load_config, get_etf_pool
    config = load_config(args.config)

    run_date = args.date or datetime.now().strftime('%Y-%m-%d')
    etf_pool = get_etf_pool(config)

    print(f"ETF 池: {len(etf_pool)} 只")
    print(f"运行日期: {run_date}")

    if args.dry_run:
        run_dry_mode(etf_pool, run_date)
    else:
        run_full_mode(etf_pool, run_date)


if __name__ == '__main__':
    main()
