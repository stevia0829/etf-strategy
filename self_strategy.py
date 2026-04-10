"""
Cibo 三驾马车优化版 - 开源版本
策略1：小市值策略
策略2：ETF反弹策略 (只能测试 23.9月后, 2000etf上市时间为23.9)
策略3：ETF轮动策略
策略4：白马攻防 v2.0

此版本已移除对聚宽SDK的依赖，使用模拟环境进行测试
"""
import datetime
import math
import prettytable
import numpy as np
import pandas as pd
from datetime import timedelta
from prettytable import PrettyTable

# 模拟聚宽的全局变量
class Context:
    def __init__(self):
        self.portfolio = Portfolio()
        self.current_dt = datetime.datetime.now()
        self.previous_date = datetime.date.today() - datetime.timedelta(days=1)

class Portfolio:
    def __init__(self):
        self.total_value = 1000000  # 默认100万
        self.available_cash = 1000000
        self.positions = {}  # 模拟持仓

class G:
    def __init__(self):
        # 策略参数
        self.portfolio_value_proportion = [0.5, 0, 0.5, 0]  # 小市值/ETF反弹/ETF轮动/白马攻防 (用于长回测)
        self.starting_cash = 1000000
        self.stock_strategy = {}
        self.strategy_holdings = {1: [], 2: [], 3: [], 4: []}
        self.strategy_starting_cash = {
            1: self.starting_cash * self.portfolio_value_proportion[0],  # 小市值 初始资金
            2: self.starting_cash * self.portfolio_value_proportion[1],  # ETF反弹 初始资金
            3: self.starting_cash * self.portfolio_value_proportion[2],  # ETF轮动 初始资金
            4: self.starting_cash * self.portfolio_value_proportion[3],  # 白马攻防 初始资金
        }
        self.strategy_value_data = {}
        self.strategy_value = {
            1: self.starting_cash * self.portfolio_value_proportion[0],  # 小市值 初始资金
            2: self.starting_cash * self.portfolio_value_proportion[1],  # ETF反弹 初始资金
            3: self.starting_cash * self.portfolio_value_proportion[2],  # ETF轮动 初始资金
            4: self.starting_cash * self.portfolio_value_proportion[3],  # 白马攻防 初始资金
        }
        # 暂存一个ETF反弹的初始比例
        self.strategy_ETF_2000_proportion = self.portfolio_value_proportion[1]
        self.strategy_ETF_2000_proportion_reset = None  # 用于检测拨正

        # 策略1参数
        self.huanshou_check = False  # 放量换手检测
        self.xsz_version = "v3"  # 市值选用版本
        self.enable_dynamic_stock_num = True  # 启用动态选股数量 3~6
        self.xsz_stock_num = 5  # 默认的持股数量
        self.yesterday_HL_list = []  # 昨日涨停股票
        self.target_list = []  # 目标持仓股票
        self.xsz_buy_etf = "512800.XSHG"  # 空仓时购买ETF
        self.run_stoploss = True  # 是否进行止损
        self.stoploss_strategy = 3  # 1为止损线止损，2为市场趋势止损, 3为联合1、2策略
        self.stoploss_limit = 0.09  # 止损线
        self.stoploss_market = 0.05  # 市场趋势止损参数
        self.DBL_control = True  # 小市值大盘顶背离记录（用于风险控制）
        self.dbl = []
        self.check_dbl_days = 10  # 顶背离检测窗口期长度
        self.check_after_no_buy = False  # 检查后不再买入时间
        self.no_buy_stocks = {}  # 检查卖出的股票
        self.no_buy_after_day = 3  # 止损后不买入的时间窗口
        self.check_defense = False  # 成交额宽度检查
        self.industries = ["组20"]  # 高位防御板块
        self.defense_signal = None
        self.cnt_defense_signal = []  # 择时次数
        self.cnt_bank_signal = []  # 组20择时次数
        self.history_defense_date_list = []

        # 策略2参数
        self.limit_days = 2  # 最少持仓周期
        self.n_days = 5  # 持仓周期
        self.holding_days = 0
        self.buy_list = []
        # etf池子，优先级从高到低
        self.etf_pool_2 = [
            '159915.XSHE',  # 创业板etf
            '159536.XSHE',  # 中证2000
            '159629.XSHE',  # 中证1000
            '159922.XSHE',  # 中证500
            '159919.XSHE',  # 沪深300
            '159783.XSHE'  # 双创50
        ]

        # 策略3参数
        self.etf_pool_3 = [
            '518880.XSHG',  # 黄金ETF
            '161226.XSHE',  # (白银JJ)
            '501018.XSHG',  # 南方原油etf
            '159985.XSHE',  # 豆粕etf
            '513520.XSHG',  # 日经ETF
            '513100.XSHG',  # 纳指100
            '513300.XSHG',  # (纳斯达克ETF)
            '513400.XSHG',  # (道琼斯)
            '159206.XSHE',  # (卫星ETF).
            '159218.XSHE',  # (卫星产业ETF)
            '159227.XSHE',  # (航天航空ETF)
            '159565.XSHE',  # (汽车零部件ETF)
            '562500.XSHG',  # (机器人)
            '159819.XSHE',  # (人工智能)
            '159363.XSHE',  # (创业板人工智能TFHB)
            '512480.XSHG',  # (半导体)
            '512760.XSHG',  # (存储芯片)
            '515880.XSHG',  # (通信ETF)
            '515230.XSHG',  # 软件ETF
            '515050.XSHG',  # (5GETF)
        ]

# 创建全局变量
g = G()

# 模拟聚宽函数
def log_set_level(category, level):
    """模拟聚宽的日志设置"""
    pass

def set_backtest():
    """模拟回测设置"""
    print("设置回测参数...")

def set_benchmark(benchmark):
    """模拟设置基准"""
    print(f"设置基准: {benchmark}")

def set_option(option, value):
    """模拟设置选项"""
    print(f"设置选项: {option} = {value}")

def get_fundamentals(query_obj):
    """模拟获取基本面数据"""
    # 返回模拟数据
    df = pd.DataFrame({
        'code': ['000001.XSHE', '000002.XSHE', '000004.XSHE'],
        'market_cap': [1000000000, 2000000000, 1500000000],
        'circulating_market_cap': [800000000, 1500000000, 1200000000]
    })
    return df

# 示例：使用Tushare获取真实数据
import tushare as ts

# 配置tushare
ts.set_token('your_token_here')
pro = ts.pro_api()

# 替换get_price函数
def get_price(security, start_date, end_date, frequency='daily', fields=['open', 'close', 'high', 'low', 'volume']):
    stock_code = security.split('.')[0]  # 去除交易所后缀
    df = pro.daily(ts_code=stock_code, start_date=start_date.strftime('%Y%m%d'), 
                   end_date=end_date.strftime('%Y%m%d'))
    # 转换列名为聚宽风格
    df.rename(columns={'trade_date': 'date', 'vol': 'volume'}, inplace=True)
    return df[fields]

# 获取指数成分股
def get_index_stocks(index_code, date=None):
    index_code = index_code.split('.')[0]  # 去除交易所后缀
    df = pro.index_weight(index_code=index_code, trade_date=date.strftime('%Y%m%d') if date else None)
    return df['con_code'].tolist()

def get_index_stocks(index_code):
    """模拟获取指数成分股"""
    # 返回模拟的成分股列表
    if index_code == '399101.XSHE':
        return ['000001.XSHE', '000002.XSHE', '000004.XSHE', '000005.XSHE', '000006.XSHE']
    elif index_code == '000300.XSHG':
        return ['000001.XSHE', '000002.XSHE', '600000.XSHG', '600036.XSHG', '000005.XSHE']
    return []

def get_industry(security):
    """模拟获取行业信息"""
    result = {}
    if isinstance(security, list):
        for stock in security:
            result[stock] = {'sw_l2': {'industry_name': '金融'}}
    return result

def get_security_info(code):
    """模拟获取股票信息"""
    class SecurityInfo:
        def __init__(self):
            self.display_name = f"模拟股票{code[:6]}"
    
    return SecurityInfo()

def get_trade_days(start_date, end_date):
    """模拟获取交易日"""
    # 返回模拟的交易日列表
    return pd.date_range(start=start_date, end=end_date, freq='D').tolist()

def order_target_value(security, value):
    """模拟下单函数"""
    print(f"下单: {security}, 目标价值: {value}")
    return {"security": security, "value": value, "status": "success"}

def query(*args):
    """模拟查询对象"""
    class QueryObj:
        def filter(self, *args, **kwargs):
            return self
        def order_by(self, *args, **kwargs):
            return self
        def limit(self, n):
            return self
    return QueryObj()

def run_daily(func, time_str):
    """模拟每日运行"""
    print(f"设置每日运行: {func.__name__} at {time_str}")

def run_weekly(func, weekday, time_str):
    """模拟每周运行"""
    print(f"设置每周运行: {func.__name__} on weekday {weekday} at {time_str}")

def run_monthly(func, day, time_str):
    """模拟每月运行"""
    print(f"设置每月运行: {func.__name__} on day {day} at {time_str}")

def unschedule_all():
    """模拟取消所有调度"""
    print("取消所有调度任务")

def format_stock_code(code):
    """格式化股票代码"""
    return code[:6]

# 策略函数定义（简化版）
def prepare_xsz(context):
    """准备小市值策略"""
    print("准备小市值策略...")

def check_dbl(context):
    """检测大盘顶背离"""
    print("检测大盘顶背离...")

def strategy_1_sell(context):
    """策略1卖出"""
    print("策略1卖出...")

def strategy_1_buy(context):
    """策略1买入"""
    print("策略1买入...")

def xsz_sell_stocks(context):
    """小市值卖出股票"""
    print("小市值卖出股票...")

def xsz_huanshou_check(context):
    """换手检查"""
    print("换手检查...")

def xsz_check_limit_up(context):
    """涨停检查"""
    print("涨停检查...")

def check_defense_trigger(context):
    """防御触发检查"""
    print("防御触发检查...")

def close_account(context):
    """清仓账户"""
    print("清仓账户...")

def capital_balance_2(context):
    """资金再平衡"""
    print("资金再平衡...")

def strategy_2_sell(context):
    """策略2卖出"""
    print("策略2卖出...")

def strategy_2_buy(context):
    """策略2买入"""
    print("策略2买入...")

def strategy_3_sell(context):
    """策略3卖出"""
    print("策略3卖出...")

def strategy_3_buy(context):
    """策略3买入"""
    print("策略3买入...")

def bm_before_market_open(context):
    """白马开盘前准备"""
    print("白马开盘前准备...")

def bm_adjust_position(context):
    """白马调仓"""
    print("白马调仓...")

def make_record(context):
    """记录数据"""
    print("记录数据...")

def print_summary(context):
    """打印摘要"""
    print("打印摘要...")

""" ====================== 基础配置 ====================== """


def initialize(context):
    set_backtest()  # 设置回测条件
    set_params(context)  # 设置基础参数
    set_strategy_params(context)  # 设置策略参数

    # 过滤日志
    log_set_level('order', 'error')


# 基础参数设置
def set_params(context):
    # 策略名
    """
    注意:
    1. 白马v2是半成品开发内容, 放进来希望大家去优化了. 目前收益低回撤大, cibo本人是不会考虑实盘使用
    2. 对于白马v2是否使用依旧保持 三马v4.0 版本替换掉的结论
    3. ETF反弹核心标的在23.9月才上市, 回测过去周期策略失效
    4. 本策略预设的研究周期设计为 长:18-25, 中20-25, 短24-25, 早于18的 15/17 极端行情暂不做考虑
    """
    g.portfolio_value_proportion = [0.5, 0, 0.5, 0]  # 小市值/ETF轮动 (用于长回测)

    g.starting_cash = context.portfolio.total_value  # 策略初始资金, 用于计算子策略收益波动曲线
    g.stock_strategy = {}  # 记录股票对应的策略, 反向映射方便检索
    g.strategy_holdings = {1: [], 2: [], 3: [], 4: []}
    # 记录策略初始的金额, 用于计算各策略收益波动曲线
    g.strategy_starting_cash = {
        1: g.starting_cash * g.portfolio_value_proportion[0],  # 小市值 初始资金
        2: g.starting_cash * g.portfolio_value_proportion[1],  # ETF反弹 初始资金
        3: g.starting_cash * g.portfolio_value_proportion[2],  # ETF轮动 初始资金
        4: g.starting_cash * g.portfolio_value_proportion[3],  # 白马攻防 初始资金
    }
    # 记录每日策略收益
    g.strategy_value_data = {}
    g.strategy_value = {
        1: g.starting_cash * g.portfolio_value_proportion[0],  # 小市值 初始资金
        2: g.starting_cash * g.portfolio_value_proportion[1],  # ETF反弹 初始资金
        3: g.starting_cash * g.portfolio_value_proportion[2],  # ETF轮动 初始资金
        4: g.starting_cash * g.portfolio_value_proportion[3],  # 白马攻防 初始资金
    }
    # 暂存一个ETF反弹的初始比例
    g.strategy_ETF_2000_proportion = g.portfolio_value_proportion[1]
    g.strategy_ETF_2000_proportion_reset = None  # 用于检测拨正
    capital_balance_2(context)  # 首次就进行一次检测


# 策略参数设置
def set_strategy_params(context):
    """ 策略1 小市值 参数 """
    g.huanshou_check = False  # 放量换手检测，Ture是日频判断是否放量，False则不然
    g.xsz_version = "v3"  # 市值选用版本 可选值: v1/v2/v3 具体逻辑自己看代码吧, 写不下
    g.enable_dynamic_stock_num = True  # 启用动态选股数量 3~6
    g.xsz_stock_num = 5  # 默认的持股数量, 启用动态后会被覆盖为 3~6
    g.yesterday_HL_list = []  # 昨日涨停股票
    g.target_list = []  # 目标持仓股票
    g.xsz_buy_etf = "512800.XSHG"  # 空仓时购买ETF
    # 止损检查
    g.run_stoploss = True  # 是否进行止损
    g.stoploss_strategy = 3  # 1为止损线止损，2为市场趋势止损, 3为联合1、2策略
    g.stoploss_limit = 0.09  # 止损线
    g.stoploss_market = 0.05  # 市场趋势止损参数
    # 顶背离检查
    g.DBL_control = True  # 小市值大盘顶背离记录（用于风险控制）
    g.dbl = []
    g.check_dbl_days = 10  # 顶背离检测窗口期长度, 窗口内不仅买入
    # 异常处理窗口期检查
    g.check_after_no_buy = False  # 检查后不再买入时间
    g.no_buy_stocks = {}  # 检查卖出的股票
    g.no_buy_after_day = 3  # 止损后不买入的时间窗口
    # 成交额宽度检查
    g.check_defense = False  # 成交额宽度检查
    g.industries = ["组20"]  # 高位防御板块
    g.defense_signal = None
    g.cnt_defense_signal = []  # 择时次数
    g.cnt_bank_signal = []  # 组20择时次数
    g.history_defense_date_list = []

    """ 策略2 ETF反弹 参数 """
    g.limit_days = 2  # 最少持仓周期
    g.n_days = 5  # 持仓周期
    g.holding_days = 0
    g.buy_list = []
    # etf池子，优先级从高到低
    g.etf_pool_2 = [
        '159915.XSHE',  # 创业板etf
        '159536.XSHE',  # 中证2000
        '159629.XSHE',  # 中证1000
        '159922.XSHE',  # 中证500
        '159919.XSHE',  # 沪深300
        '159783.XSHE'  # 双创50
    ]

    """ 策略3 ETF轮动 参数 """
    # 策略3全局变量
    g.etf_pool_3 = [
        '518880.XSHG',  # 黄金ETF
        '161226.XSHE',  # (白银JJ)
        '501018.XSHG',  # 南方原油etf
        '159985.XSHE',  # 豆粕etf
        '513520.XSHG',  # 日经ETF
        '513100.XSHG',  # 纳指100
        '513300.XSHG',  # (纳斯达克ETF)
        '513400.XSHG',  # (道琼斯)
        '159206.XSHE',  # (卫星ETF).
        '159218.XSHE',  # (卫星产业ETF)
        '159227.XSHE',  # (航天航空ETF)
        '159565.XSHE',  # (汽车零部件ETF)
        '562500.XSHG',  # (机器人)
        '159819.XSHE',  # (人工智能)
        '159363.XSHE',  # (创业板人工智能TFHB)
        '512480.XSHG',  # (半导体)
        '512760.XSHG',  # (存储芯片)
        '515880.XSHG',  # (通信ETF)
        '515230.XSHG',  # 软件ETF
        '515050.XSHG',  # (5GETF)
    ]


""" ====================== 执行入口, 定时任务下发 ====================== """


def after_code_changed(context):
    unschedule_all()

    # 策略1 小市值策略
    if g.portfolio_value_proportion[0] > 0:
        run_daily(prepare_xsz, '9:05')
        # 初次检测成交额
        if g.check_defense and g.defense_signal is None:
            check_defense_trigger(context)
        # 每日开盘前检测大盘顶背离, 只针对策略1
        if g.DBL_control:
            run_daily(check_dbl, '9:31')  # 不要早于9点30, 否则会导致绘制的收益曲线无法拿到价格信息
        run_weekly(strategy_1_sell, 2, '09:35')
        run_weekly(strategy_1_buy, 2, '09:35:02')
        run_daily(xsz_sell_stocks, time='10:00')  # 止损函数
        # 换手检查
        if g.huanshou_check:
            run_daily(xsz_huanshou_check, '10:30')
        # 涨停板检查
        run_daily(xsz_check_limit_up, '14:00')
        # 成交额宽度检测
        if g.check_defense:
            run_daily(check_defense_trigger, '14:50')
        # 检测清仓并买入ETF
        run_daily(close_account, '9:35')

    # 策略2 ETF反弹策略
    if g.strategy_ETF_2000_proportion > 0:
        run_daily(capital_balance_2, '14:45')  # 基于 2023.9.28 进行资金再平衡
        run_daily(strategy_2_sell, '14:49')
        run_daily(strategy_2_buy, '14:50')

    # 策略3 ETF轮动策略
    if g.portfolio_value_proportion[2] > 0:
        run_daily(strategy_3_sell, '9:35:00')
        run_daily(strategy_3_buy, '9:35:05')

    # 策略4 白马策略
    if g.portfolio_value_proportion[3] > 0:
        run_monthly(bm_before_market_open, 1, time='8:00')
        # run_daily(bm_before_market_open, time='15:10')
        run_monthly(bm_adjust_position, 1, time='9:35')

    # 记录各策略每日收益
    run_daily(make_record, '15:01')
    # 打印每日收益
    run_daily(print_summary, '15:02')


# 主程序入口
if __name__ == "__main__":
    # 创建上下文
    context = Context()
    
    # 初始化策略
    initialize(context)
    
    # 触发代码变更（设置定时任务）
    after_code_changed(context)
    
    print("策略初始化完成")