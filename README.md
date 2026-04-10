# ETF Strategy - 多 Agent ETF 量化分析与推送系统

基于多 Agent 协作框架的 A 股 ETF 智能分析系统，自动完成动量筛选、新闻聚合、风险评估和报告推送。

## 系统功能图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ETF 量化分析与推送系统                         │
├─────────────┬─────────────┬──────────────┬─────────────────────────┤
│   数据采集层  │   策略计算层  │   情报分析层   │       输出推送层        │
├─────────────┼─────────────┼──────────────┼─────────────────────────┤
│             │             │              │                         │
│  ETF 行情数据 │  加权动量得分 │  财经新闻聚合  │   Markdown 分析报告     │
│  市场指数快照 │  MACD 信号   │  地缘政治搜索  │   PDF 报告生成          │
│  个股基本面   │  RSI 指标    │  行业龙头动态  │   企业微信推送           │
│  板块资金流向 │  ETF 反弹检测 │  政策监管动态  │   钉钉机器人推送         │
│             │  综合信号判定 │  板块情绪分类  │                         │
│             │             │              │                         │
├─────────────┴─────────────┴──────────────┴─────────────────────────┤
│  AKShare · Baostock · Tushare · DuckDuckGo · LLM (GPT-4o / Claude) │
└─────────────────────────────────────────────────────────────────────┘
```

### 分析流程

```
 ┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌────────────┐
 │ ETF 动量  │     │  行业情报深度  │     │  多维综合评分  │     │  报告生成   │
 │  初筛     │────▶│   分析       │────▶│   筛选       │────▶│  & 推送    │
 │          │     │              │     │              │     │            │
 │ ·动量Top10│     │ ·行业新闻     │     │ ·技术面得分   │     │ ·Markdown  │
 │ ·反弹信号 │     │ ·政治风险     │     │ ·消息面得分   │     │ ·PDF报告   │
 │ ·MACD金叉 │     │ ·龙头动态     │     │ ·风险等级评定  │     │ ·Webhook   │
 └──────────┘     └──────────────┘     └──────────────┘     └────────────┘
```

## Agent 架构交互图

```
                           ┌──────────────────┐
                           │    config.yaml    │
                           │  ETF池/策略参数    │
                           └────────┬─────────┘
                                    │
                            ┌───────▼───────┐
                            │   LangGraph    │
                            │   State Graph  │
                            └───────┬───────┘
                                    │
                      ┌─────────────▼──────────────┐
                      │       Data Agent            │
                      │  ┌───────────────────────┐  │
                      │  │ AKShare / Baostock     │  │
                      │  │ · ETF OHLCV 数据       │  │
                      │  │ · 市场指数快照          │  │
                      │  │ · 个股基本面数据        │  │
                      │  └───────────────────────┘  │
                      └──────┬──────────────┬───────┘
                             │              │
                    价格数据  │              │  价格数据
                             ▼              ▼
              ┌────────────────────┐  ┌────────────────────┐
              │   Strategy Agent   │  │    News Agent       │
              │                    │  │                     │
              │ ┌────────────────┐ │  │ ┌─────────────────┐ │
              │ │ 动量得分计算    │ │  │ │ AKShare 财经新闻 │ │
              │ │ MACD / RSI     │ │  │ │ 东财板块新闻     │ │
              │ │ ETF 反弹检测    │ │  │ │ DuckDuckGo 搜索  │ │
              │ │ 信号综合判定    │ │  │ └────────┬────────┘ │
              │ └────────────────┘ │  │          │          │
              │                    │  │ ┌────────▼────────┐ │
              │  纯计算，无LLM     │  │ │ LLM 风险分析     │ │
              │                    │  │ │ ·地缘风险评分    │ │
              └────────┬───────────┘  │ │ ·板块情绪分类    │ │
                       │              │ │ ·尾部风险识别    │ │
          技术指标信号  │              │ └─────────────────┘ │
                       │              └──────────┬──────────┘
                       │     消息面分析           │
                       │                         │
                       └──────────┬──────────────┘
                                  │
                       ┌──────────▼──────────────┐
                       │     Decision Agent       │
                       │                          │
                       │  ┌────────────────────┐  │
                       │  │ LLM 综合评估        │  │
                       │  │ ·技术面 × 消息面    │  │
                       │  │ ·风险等级评定       │  │
                       │  │ ·标的推荐排序       │  │
                       │  └────────┬───────────┘  │
                       │           │              │
                       │  ┌────────▼───────────┐  │
                       │  │ 报告生成 & 推送     │  │
                       │  │ ·Markdown 报告     │  │
                       │  │ ·企业微信 Webhook  │  │
                       │  │ ·钉钉机器人 Webhook│  │
                       │  └────────────────────┘  │
                       └──────────────────────────┘
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │  企业微信 / 钉钉通知   │
                       │  每日 ETF 分析报告     │
                       └──────────────────────┘
```

### Agent 间数据流

```
TradingState (LangGraph 共享状态)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Data Agent 写入:
  etf_prices · etf_current_prices · market_indices

Strategy Agent 写入:
  momentum_scores · macd_signals · rsi_values
  etf_ranking · etf_bounce_candidates · strategy_signals

News Agent 写入:
  financial_news · geopolitical_risks
  sector_sentiment · news_risk_score

Decision Agent 写入:
  final_recommendations · risk_assessment
  notification_sent · notification_payload
```

## ETF 池

### 轮动池（17 只）

| 类别 | ETF |
|------|-----|
| 大宗商品 | 黄金、白银、原油、豆粕 |
| 海外指数 | 日经、纳指100、纳斯达克、道琼斯、德国DAX |
| 港股 | 恒生科技 |
| 科技 | 半导体、存储芯片、通信、软件、5G、人工智能、机器人 |

### 反弹池（6 只）

创业板ETF、中证2000、中证1000、中证500、沪深300、双创50

## 项目结构

```
etf_strategy/
├── multi_agent/                            # 多 Agent 分析框架
│   ├── main.py                             # 入口脚本
│   ├── graph.py                            # LangGraph 图编排
│   ├── state.py                            # 共享状态定义
│   ├── config.yaml                         # ETF 池 + 策略参数配置
│   ├── agents/
│   │   ├── data_agent.py                   # 行情数据获取
│   │   ├── news_agent.py                   # 新闻 + 地缘风险分析
│   │   ├── strategy_agent.py               # 动量/MACD/RSI 信号计算
│   │   └── decision_agent.py               # 综合评分 + 报告推送
│   ├── tools/
│   │   ├── market_data_tools.py            # AKShare/Baostock 数据工具
│   │   ├── news_tools.py                   # 多源新闻聚合工具
│   │   ├── strategy_tools.py               # 动量/技术指标计算工具
│   │   └── notification_tools.py           # 微信/钉钉推送工具
│   ├── utils/
│   │   ├── code_converter.py               # 股票代码格式互转
│   │   └── data_source_adapter.py          # 数据源适配器
│   └── prompts/
│       ├── news_analysis_prompt.py         # 新闻分析 Prompt
│       └── decision_prompt.py              # 决策 Prompt
├── cibo_strategy_standalone_fixed_enhanced.py  # 策略回测引擎
├── personal_select.py                      # 板块选股器
└── config.json.example                     # 数据源配置模板
```

## 快速开始

### 环境要求

- Python 3.10+
- OpenAI 或 Anthropic API Key（LLM 分析功能需要）

### 安装

```bash
git clone https://github.com/stevia0829/etf-strategy.git
cd etf-strategy
pip install -r multi_agent/requirements.txt

# 配置数据源（可选，AKShare 免费无需配置）
cp config.json.example config.json
```

### 运行

```bash
# Dry-run 模式（不走 LLM，不推送，测试数据+策略链路）
python -m multi_agent.main --dry-run

# 完整运行
export OPENAI_API_KEY="sk-..."
python -m multi_agent.main

# 指定日期
python -m multi_agent.main --date 2026-04-09
```

### 推送配置

```bash
# 企业微信 Webhook
export WECHAT_WEBHOOK_URL="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"

# 钉钉 Webhook
export DINGTALK_WEBHOOK_URL="https://oapi.dingtalk.com/robot/send?access_token=xxx"
```

## 核心算法

### 加权对数线性回归动量

对价格取对数后做加权线性回归（权重 1→2，近期权重更大），年化收益率乘以 R² 作为得分：

```
score = (e^(slope × 250) - 1) × R²
```

### ETF 反弹信号

开盘价 < 近5日最高价 × 98% 且 当前价 > 开盘价 × 101% 时触发。

## 数据源

| 数据源 | 类型 | 说明 |
|--------|------|------|
| AKShare | 免费 | 推荐首选，无需注册 |
| Baostock | 免费 | 数据质量好 |
| Tushare | 需 Token | 功能丰富，[注册获取](https://tushare.pro/) |

## 后续计划

- [ ] 支持自定义 ETF 池动态更新
- [ ] 行业龙头企业自动关联分析
- [ ] PDF 格式报告生成
- [ ] 历史推荐回测追踪
- [ ] 多时间周期动量对比

## 注意事项

- 本项目仅供学习和研究使用，不构成任何投资建议
- 推送内容为 AI 生成的分析参考，投资决策请自行判断

## 致谢

- [AKShare](https://github.com/akfamily/akshare) - 开源金融数据接口
- [LangGraph](https://github.com/langchain-ai/langgraph) - Agent 编排框架
