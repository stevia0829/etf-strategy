# ETF Strategy - 多策略量化交易框架

基于 [Cibo 三驾马车策略](https://www.joinquant.com/post/65582) 的 A 股 ETF 量化交易系统，包含多策略回测引擎和多 Agent 智能分析框架。

## 策略体系

本项目包含 4 个独立子策略，可按比例分配资金组合运行：

| 策略 | 名称 | 核心逻辑 | 适用场景 |
|------|------|----------|----------|
| 策略1 | 小市值 | 小盘股筛选 + 行业分散 + 止损/顶背离控制 | A 股多头 |
| 策略2 | ETF反弹 | 宽基 ETF 超跌反弹（开盘跌2%+盘中涨1%） | 短线波段 |
| 策略3 | ETF轮动 | 20+ 只 ETF 加权动量排名轮动 | 趋势跟踪 |
| 策略4 | 白马攻防 | 沪深300蓝筹 + 市场温度计择时 | 防御配置 |

### ETF 轮动池（策略3）

涵盖 17 只国内外 ETF：黄金、白银、原油、豆粕、日经、纳指、道琼斯、德国DAX、恒生科技、半导体、芯片、通信、软件、5G、人工智能、机器人等。

## 项目结构

```
etf_strategy/
├── cibo_strategy.py                        # 聚宽平台原始版（需 jqdata SDK）
├── cibo_strategy_standalone_fixed.py       # 独立版（免费数据源）
├── cibo_strategy_standalone_fixed_enhanced.py  # 增强独立版（含回测引擎）
├── personal_select.py                      # AI 板块选股器
├── config.json                             # Tushare Token 配置
├── multi_agent/                            # 多 Agent 智能分析框架
│   ├── main.py                             # 入口脚本
│   ├── graph.py                            # LangGraph 图编排
│   ├── state.py                            # 共享状态定义
│   ├── config.yaml                         # ETF 池 + 策略参数配置
│   ├── agents/
│   │   ├── data_agent.py                   # 行情数据获取
│   │   ├── news_agent.py                   # 新闻 + 地缘风险分析
│   │   ├── strategy_agent.py               # 动量/MACD/RSI 信号计算
│   │   └── decision_agent.py               # 综合评估 + 推送
│   ├── tools/
│   │   ├── market_data_tools.py            # AKShare/Baostock 数据工具
│   │   ├── news_tools.py                   # 多源新闻聚合工具
│   │   ├── strategy_tools.py               # 策略计算工具
│   │   └── notification_tools.py           # 微信/钉钉推送工具
│   ├── utils/
│   │   ├── code_converter.py               # 股票代码格式互转
│   │   └── data_source_adapter.py          # 数据源适配器
│   └── prompts/
│       ├── news_analysis_prompt.py         # 新闻分析 Prompt
│       └── decision_prompt.py              # 决策 Prompt
```

## 多 Agent 框架

基于 LangGraph 的多 Agent 协作系统，自动完成数据获取、新闻分析、策略计算和综合决策。

```
START → Data Agent → ┬→ News Agent ──→ Decision Agent → END
                      └→ Strategy Agent ┘
```

- **Data Agent**：从 AKShare/Baostock 获取 ETF 行情和指数数据
- **News Agent**：聚合财经新闻 + 地缘政治搜索，LLM 评估风险评分
- **Strategy Agent**：计算加权动量得分、MACD、RSI、反弹信号
- **Decision Agent**：LLM 综合技术面 + 消息面给出推荐，推送到微信/钉钉

## 快速开始

### 环境要求

- Python 3.10+
- 可选：OpenAI / Anthropic API Key（多 Agent 框架的 LLM 分析功能需要）

### 安装

```bash
# 克隆仓库
git clone https://github.com/stevia0829/etf-strategy.git
cd etf-strategy

# 安装依赖
pip install -r multi_agent/requirements.txt

# 配置 Tushare Token（可选，AKShare 免费可用）
cp config.json.example config.json
# 编辑 config.json 填入 token
```

### 运行

```bash
# Dry-run 模式（测试数据+策略链路，不走 LLM，不推送）
python -m multi_agent.main --dry-run

# 完整运行
export OPENAI_API_KEY="sk-..."
python -m multi_agent.main

# 指定日期
python -m multi_agent.main --date 2026-04-09
```

### 推送配置

在 `.env` 文件或环境变量中设置 Webhook URL：

```bash
# 企业微信
export WECHAT_WEBHOOK_URL="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"

# 钉钉
export DINGTALK_WEBHOOK_URL="https://oapi.dingtalk.com/robot/send?access_token=xxx"
```

## 核心算法

### 加权对数线性回归动量

对价格取对数后做加权线性回归（权重 1→2，近期权重更大），用年化收益率乘以 R² 作为动量得分：

```
score = (e^(slope × 250) - 1) × R²
```

来源：`cibo_strategy.py` 的 `filter_moment_rank` 函数。

### ETF 反弹信号

当 ETF 开盘价低于近5日最高价的 98%，且当前价高于开盘价的 101% 时触发。

## 数据源

| 数据源 | 类型 | 说明 |
|--------|------|------|
| AKShare | 免费 | 推荐首选，无需注册 |
| Baostock | 免费 | 数据质量好，需登录 |
| Tushare | 需 Token | 功能丰富，[注册获取](https://tushare.pro/) |

股票代码格式：`000001.XSHE`（深市）、`600000.XSHG`（沪市）

## 注意事项

- 本项目仅供学习和研究使用，不构成任何投资建议
- 策略2 ETF反弹核心标的中证2000ETF于2023年9月上市，历史回测仅支持此日期之后
- 策略4 白马攻防为实验性策略，作者建议谨慎使用

