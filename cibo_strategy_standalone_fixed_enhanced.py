"""
Cibo 三驾马车策略 - 独立增强版本
包含完整的买入卖出模块、开盘前运行函数、回测功能和账本功能
"""

import pandas as pd
import numpy as np
import datetime
from datetime import timedelta
import math
import warnings
import os
import json
import time
from typing import Dict, List, Tuple, Optional
import matplotlib.pyplot as plt
warnings.filterwarnings('ignore')

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')

class Portfolio:
    """持仓管理类"""
    def __init__(self, initial_capital=1000000):
        self.initial_capital = initial_capital
        self.current_cash = initial_capital
        self.positions = {}  # {symbol: {'amount': 数量, 'avg_cost': 平均成本, 'value': 当前价值}}
        self.total_value = initial_capital
        self.daily_records = []
        
    def update_portfolio(self, current_prices: Dict):
        """更新持仓价值"""
        total_value = self.current_cash
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                position['value'] = position['amount'] * current_prices[symbol]
                total_value += position['value']
        self.total_value = total_value
        return total_value
        
    def add_position(self, symbol: str, amount: int, price: float):
        """添加持仓"""
        if symbol in self.positions:
            # 更新现有持仓
            old_amount = self.positions[symbol]['amount']
            old_avg_cost = self.positions[symbol]['avg_cost']
            total_cost = old_amount * old_avg_cost + amount * price
            new_amount = old_amount + amount
            self.positions[symbol]['amount'] = new_amount
            self.positions[symbol]['avg_cost'] = total_cost / new_amount
        else:
            # 新建持仓
            self.positions[symbol] = {
                'amount': amount,
                'avg_cost': price,
                'value': amount * price
            }
        self.current_cash -= amount * price
        
    def remove_position(self, symbol: str, amount: int, price: float):
        """移除持仓"""
        if symbol in self.positions:
            position = self.positions[symbol]
            if amount >= position['amount']:
                # 全部卖出
                profit = (price - position['avg_cost']) * position['amount']
                self.current_cash += position['amount'] * price
                del self.positions[symbol]
                return profit
            else:
                # 部分卖出
                profit = (price - position['avg_cost']) * amount
                self.current_cash += amount * price
                position['amount'] -= amount
                position['value'] = position['amount'] * price
                return profit
        return 0

class DataSourceManager:
    """数据源管理器"""
    
    def __init__(self):
        self.tushare_token = None
        self.data_sources = {}
        self.init_data_sources()
    
    def init_data_sources(self):
        """初始化数据源"""
        self.load_config()
        
        # 检查Tushare
        try:
            import tushare as ts
            if self.tushare_token:
                ts.set_token(self.tushare_token)
                self.data_sources['tushare'] = ts.pro_api()
                print("✓ Tushare 初始化成功")
            else:
                print("⚠ Tushare token未配置，使用免费接口")
                self.data_sources['tushare'] = ts
        except ImportError:
            print("✗ Tushare未安装")
        
        # 检查AKShare
        try:
            import akshare as ak
            self.data_sources['akshare'] = ak
            print("✓ AKShare 初始化成功")
        except ImportError:
            print("✗ AKShare未安装")
        
        # 检查Baostock
        try:
            import baostock as bs
            lg = bs.login()
            if lg.error_code == '0':
                self.data_sources['baostock'] = bs
                print("✓ Baostock 初始化成功")
            else:
                print("✗ Baostock 登录失败")
        except ImportError:
            print("✗ Baostock未安装")
    
    def load_config(self):
        """加载配置文件"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.tushare_token = config.get('tushare_token')
            except Exception as e:
                print(f"✗ 配置文件加载失败: {e}")
    
    def get_stock_data(self, symbol, start_date, end_date, fields=['open', 'high', 'low', 'close', 'volume']):
        """获取股票历史数据"""
        if 'baostock' in self.data_sources:
            try:
                bs = self.data_sources['baostock']
                if symbol.startswith('6'):
                    bs_code = f"sh.{symbol}"
                else:
                    bs_code = f"sz.{symbol}"
                
                rs = bs.query_history_k_data_plus(
                    bs_code,
                    f"date,{','.join(fields)}",
                    start_date=start_date,
                    end_date=end_date,
                    frequency="d",
                    adjustflag="3"
                )
                data_list = []
                while (rs.error_code == '0') & rs.next():
                    data_list.append(rs.get_row_data())
                
                if data_list:
                    df = pd.DataFrame(data_list, columns=rs.fields)
                    for field in fields:
                        if field in df.columns:
                            df[field] = pd.to_numeric(df[field], errors='coerce')
                    return df
            except Exception as e:
                print(f"Baostock获取{symbol}数据失败: {e}")
        
        if 'akshare' in self.data_sources:
            try:
                ak = self.data_sources['akshare']
                ak_code = f"{symbol}.SH" if symbol.startswith('6') else f"{symbol}.SZ"
                df = ak.stock_zh_a_hist(symbol=ak_code, period="daily", 
                                      start_date=start_date, end_date=end_date,
                                      adjust="hfq")
                return df
            except Exception as e:
                print(f"AKShare获取{symbol}数据失败: {e}")
        
        raise Exception(f"无法获取{symbol}的历史数据")
    
    def get_etf_data(self, etf_code, days=30):
        """获取ETF数据"""
        end_date = datetime.datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.datetime.now() - timedelta(days=days*2)).strftime('%Y-%m-%d')
        
        if 'akshare' in self.data_sources:
            try:
                ak = self.data_sources['akshare']
                df = ak.fund_etf_hist_sina(symbol=etf_code)
                if not df.empty:
                    return df.tail(days)
            except Exception as e:
                print(f"AKShare获取ETF{etf_code}数据失败: {e}")
        
        return self.get_stock_data(etf_code, start_date, end_date)

class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, strategy, start_date, end_date, initial_capital=1000000):
        self.strategy = strategy
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.results = {}
        self.price_cache = {}  # {symbol: DataFrame}
        
    def preload_price_data(self, symbols, extra_days=30):
        """预加载价格数据到缓存"""
        start_str = (self.start_date - timedelta(days=extra_days)).strftime('%Y-%m-%d')
        end_str = (self.end_date + timedelta(days=5)).strftime('%Y-%m-%d')
        print(f"预加载价格数据: {start_str} 到 {end_str}")
        for symbol in symbols:
            try:
                df = self.strategy.get_stock_data(symbol, start_str, end_str)
                if not df.empty and 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    df.set_index('date', inplace=True)
                    self.price_cache[symbol] = df
            except Exception as e:
                print(f"预加载{symbol}数据失败: {e}")
    
    def get_price_on_date(self, symbol, target_date):
        """获取指定日期的价格"""
        if symbol in self.price_cache:
            df = self.price_cache[symbol]
            if isinstance(target_date, datetime.datetime):
                target_date = target_date.date()
            elif not isinstance(target_date, datetime.date):
                target_date = pd.to_datetime(target_date).date()
            mask = df.index.date <= target_date
            valid_data = df[mask]
            if not valid_data.empty:
                return valid_data['close'].iloc[-1]
        return 0
    
    def run_backtest(self):
        """运行回测"""
        print(f"开始回测: {self.start_date.strftime('%Y-%m-%d')} 到 {self.end_date.strftime('%Y-%m-%d')}")
        
        current_date = self.start_date
        portfolio_history = []
        
        all_symbols = set()
        while current_date <= self.end_date:
            if current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue
            
            try:
                candidates = self.strategy.get_all_candidates(current_date)
                all_symbols.update(candidates)
                
                current_date += timedelta(days=1)
            except:
                current_date += timedelta(days=1)
        
        if all_symbols:
            self.preload_price_data(list(all_symbols))
            self.strategy.set_backtest_mode(self.price_cache, self.get_price_on_date)
        
        current_date = self.start_date
        while current_date <= self.end_date:
            if current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue
                
            try:
                strategy_results = self.strategy.execute_daily_strategy(current_date)
                
                daily_result = {
                    'date': current_date,
                    'total_value': self.strategy.portfolio.total_value,
                    'cash': self.strategy.portfolio.current_cash,
                    'positions:': len(self.strategy.portfolio.positions),
                    'strategy_results': strategy_results
                }
                portfolio_history.append(daily_result)
                
                print(f"日期: {current_date.strftime('%Y-%m-%d')}, 总资产: {self.strategy.portfolio.total_value:.2f}")
                
            except Exception as e:
                print(f"回测日期 {current_date} 执行失败: {e}")
            
            current_date += timedelta(days=1)
        
        self.results = {
            'portfolio_history': portfolio_history,
            'final_value': self.strategy.portfolio.total_value,
            'total_return': (self.strategy.portfolio.total_value - self.initial_capital) / self.initial_capital if self.initial_capital > 0 else 0
        }
        
        return self.results
    
    def generate_report(self):
        """生成回测报告"""
        if not self.results:
            print("请先运行回测")
            return
        
        history = self.results['portfolio_history']
        dates = [r['date'] for r in history]
        values = [r['total_value'] for r in history]
        
        # 计算指标
        total_return = self.results['total_return']
        max_drawdown = self.calculate_max_drawdown(values)
        sharpe_ratio = self.calculate_sharpe_ratio(values)
        
        print("\n" + "="*50)
        print("回测报告")
        print("="*50)
        print(f"回测期间: {self.start_date.strftime('%Y-%m-%d')} 到 {self.end_date.strftime('%Y-%m-%d')}")
        print(f"初始资金: {self.initial_capital:,.2f}")
        print(f"最终资金: {self.results['final_value']:,.2f}")
        print(f"总收益率: {total_return:.2%}")
        print(f"最大回撤: {max_drawdown:.2%}")
        print(f"夏普比率: {sharpe_ratio:.2f}")
        
        # 绘制收益曲线
        plt.figure(figsize=(12, 6))
        plt.plot(dates, values)
        plt.title('Portfolio Value Over Time')
        plt.xlabel('Date')
        plt.ylabel('Portfolio Value')
        plt.grid(True)
        plt.show()
    
    def calculate_max_drawdown(self, values):
        """计算最大回撤"""
        if not values or len(values) < 2:
            return 0.0
        peak = values[0]
        max_dd = 0
        for value in values:
            if value > peak:
                peak = value
            if peak > 0:
                dd = (peak - value) / peak
                if dd > max_dd:
                    max_dd = dd
        return max_dd
    
    def calculate_sharpe_ratio(self, values, risk_free_rate=0.02):
        """计算夏普比率"""
        if len(values) < 2:
            return 0.0
        returns = []
        for i in range(1, len(values)):
            if values[i-1] != 0:
                returns.append((values[i] - values[i-1]) / values[i-1])
        
        if len(returns) == 0:
            return 0.0
            
        std_ret = np.std(returns)
        if std_ret == 0:
            return 0.0
            
        excess_returns = [r - risk_free_rate/252 for r in returns]
        sharpe = np.mean(excess_returns) / std_ret * np.sqrt(252)
        return sharpe

class CiboStrategyEnhanced:
    """Cibo策略增强版本"""
    
    def __init__(self, initial_capital=1000000, config_file=None):
        self.initial_capital = initial_capital
        self.portfolio = Portfolio(initial_capital)
        
        # 策略持仓记录
        self.strategy_holdings = {1: [], 2: [], 3: [], 4: []}
        self.strategy_weights = [0.25, 0.15, 0.30, 0.30]  # 各策略权重: 小市值/ETF反弹/ETF轮动/白马
        
        # 全局变量（模拟原策略中的g变量）
        self.g = type('GlobalVars', (), {})()
        self.g.defense_signal = False
        self.g.huanshou_check = True
        self.g.DBL_control = True
        
        # 初始化数据源
        global CONFIG_FILE
        if config_file:
            CONFIG_FILE = config_file
        self.data_manager = DataSourceManager()
        
        # 设置策略参数
        self.set_strategy_params()
        
        # 交易记录
        self.trade_records = []
        
        # 回测模式支持
        self._backtest_mode = False
        self._price_cache = None
        self._price_getter = None
    
    def set_strategy_params(self):
        """设置策略参数"""
        # 策略1: 小市值参数
        self.xsz_version = "v3"
        self.xsz_stock_num = 5
        self.stoploss_limit = 0.09
        self.stoploss_market = 0.05
        
        # 策略2: ETF反弹参数  
        self.etf_pool_2 = [
            '159915',  # 创业板ETF
            '159536',  # 中证2000ETF
            '159629',  # 中证1000ETF
            '159922',  # 中证500ETF
            '159919',  # 沪深300ETF
        ]
        
        # 策略3: ETF轮动参数
        self.etf_pool_3 = [
            '518880',  # 黄金ETF
            '513100',  # 纳指ETF
            '513030',  # 德国30ETF
            '513130',  # 恒生科技ETF
            '512480',  # 半导体ETF
            '515050',  # 5GETF
            '512010',  # 医药ETF
            '512690',  # 酒ETF
        ]
        self.m_days = 21
        
        # 策略4: 白马参数
        self.stock_num_4 = 5
    
    # ==================== 数据获取方法 ====================
    def get_stock_data(self, symbol, start_date, end_date, fields=['close']):
        return self.data_manager.get_stock_data(symbol, start_date, end_date, fields)
    
    def get_etf_data(self, etf_code, days=30):
        return self.data_manager.get_etf_data(etf_code, days)
    
    def get_current_prices(self, symbols, target_date=None):
        """获取当前价格（支持回测模式）"""
        prices = {}
        for symbol in symbols:
            try:
                if self._backtest_mode and self._price_getter and target_date:
                    price = self._price_getter(symbol, target_date)
                    prices[symbol] = price if price > 0 else 0
                else:
                    df = self.get_stock_data(symbol, 
                                           datetime.datetime.now().strftime('%Y-%m-%d'),
                                           datetime.datetime.now().strftime('%Y-%m-%d'))
                    if not df.empty:
                        prices[symbol] = df['close'].iloc[-1]
                    else:
                        prices[symbol] = 0
            except:
                prices[symbol] = 0
        return prices
    
    def set_backtest_mode(self, price_cache, price_getter):
        """设置回测模式"""
        self._backtest_mode = True
        self._price_cache = price_cache
        self._price_getter = price_getter
    
    def get_all_candidates(self, current_date):
        """获取所有策略的候选股票（用于回测预加载）"""
        candidates = set()
        try:
            candidates.update(self.strategy_1_small_cap(current_date))
        except:
            pass
        try:
            candidates.update(self.strategy_2_etf_rebound(current_date))
        except:
            pass
        try:
            candidates.update(self.strategy_3_etf_rotation(current_date))
        except:
            pass
        try:
            candidates.update(self.strategy_4_white_horse(current_date))
        except:
            pass
        return candidates
    
    # ==================== 策略核心方法 ====================
    def calculate_momentum_score(self, prices, days=21):
        """计算动量得分"""
        if len(prices) < days:
            return 0, 0, 0
        
        recent_prices = prices[-days:]
        simple_return = (recent_prices.iloc[-1] / recent_prices.iloc[0] - 1) * 100
        
        ma_short = recent_prices.rolling(window=5).mean()
        ma_long = recent_prices.rolling(window=10).mean()
        ma_trend = 1 if ma_short.iloc[-1] > ma_long.iloc[-1] else -1
        
        def calculate_rsi(prices, period=14):
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            last_loss = loss.iloc[-1] if not pd.isna(loss.iloc[-1]) else 0
            if last_loss == 0 or pd.isna(last_loss):
                return 100.0
            last_gain = gain.iloc[-1] if not pd.isna(gain.iloc[-1]) else 0
            rs = last_gain / last_loss
            rsi = 100 - (100 / (1 + rs))
            return rsi if not pd.isna(rsi) else 50.0
        
        rsi_value = calculate_rsi(recent_prices)
        score = simple_return * 0.5 + ma_trend * 30 + (rsi_value - 50) * 0.2
        return score, simple_return, rsi_value
    
    # ==================== 四个策略的选股方法 ====================
    def strategy_1_small_cap(self, current_date):
        """策略1: 小市值策略 - 按市值从小到大排序选取"""
        print("执行小市值策略...")
        if 'akshare' in self.data_manager.data_sources:
            try:
                ak = self.data_manager.data_sources['akshare']
                stock_info = ak.stock_info_a_code_name()
                if stock_info.empty or 'code' not in stock_info.columns:
                    return self._get_fallback_stocks_1()
                
                try:
                    real_time_data = ak.stock_zh_a_spot_em()
                    if not real_time_data.empty and '代码' in real_time_data.columns and '总市值' in real_time_data.columns:
                        merged = stock_info.merge(
                            real_time_data[['代码', '总市值']], 
                            left_on='code', right_on='代码', how='inner'
                        )
                        merged = merged.dropna(subset=['总市值'])
                        merged['总市值'] = pd.to_numeric(merged['总市值'], errors='coerce')
                        merged = merged.dropna(subset=['总市值'])
                        merged = merged[merged['总市值'] > 0]
                        merged = merged.sort_values('总市值', ascending=True)
                        
                        excluded = ['688', '300', '301']
                        filtered = merged[~merged['code'].str.startswith(tuple(excluded))]
                        
                        selected = filtered['code'].head(self.xsz_stock_num).tolist()
                        if len(selected) >= self.xsz_stock_num:
                            return selected
                        
                        selected = merged['code'].head(self.xsz_stock_num).tolist()
                        return selected if selected else self._get_fallback_stocks_1()
                except Exception as e:
                    print(f"获取实时市值数据失败: {e}，使用基础排序")
                
                return stock_info['code'].head(self.xsz_stock_num).tolist()
            except Exception as e:
                print(f"小市值策略执行失败: {e}")
        return self._get_fallback_stocks_1()
    
    def _get_fallback_stocks_1(self):
        """策略1的回退股票列表"""
        return ['000001', '000002', '000858', '600519', '600036'][:self.xsz_stock_num]
    
    def strategy_2_etf_rebound(self, current_date):
        """策略2: ETF反弹策略"""
        print("执行ETF反弹策略...")
        buy_candidates = []
        for etf in self.etf_pool_2:
            try:
                df = self.get_etf_data(etf, days=5)
                if len(df) < 3:
                    continue
                pre_high = df['high'].max()
                current_price = df['close'].iloc[-1]
                open_price = df['open'].iloc[-1]
                if (open_price / pre_high < 0.98) and (current_price / open_price > 1.01):
                    buy_candidates.append(etf)
            except Exception as e:
                print(f"ETF反弹策略获取{etf}数据失败: {e}")
        return buy_candidates
    
    def strategy_3_etf_rotation(self, current_date):
        """策略3: ETF轮动策略"""
        print("执行ETF轮动策略...")
        momentum_scores = {}
        for etf in self.etf_pool_3:
            try:
                df = self.get_etf_data(etf, days=self.m_days + 5)
                if len(df) < self.m_days:
                    continue
                prices = df['close']
                score, _, _ = self.calculate_momentum_score(prices, self.m_days)
                momentum_scores[etf] = score
            except Exception as e:
                print(f"ETF轮动策略计算{etf}动量失败: {e}")
        if momentum_scores:
            ranked_etfs = sorted(momentum_scores.items(), key=lambda x: x[1], reverse=True)
            return [ranked_etfs[0][0]]
        return []
    
    def strategy_4_white_horse(self, current_date):
        """策略4: 白马攻防策略 - 基于基本面筛选优质白马股"""
        print("执行白马攻防策略...")
        if 'akshare' in self.data_manager.data_sources:
            try:
                ak = self.data_manager.data_sources['akshare']
                hs300 = ak.index_stock_cons_sina(symbol="000300")
                if hs300.empty or 'code' not in hs300.columns:
                    return self._get_fallback_stocks_4()
                
                try:
                    spot_data = ak.stock_zh_a_spot_em()
                    if not spot_data.empty and '代码' in spot_data.columns:
                        required_cols = ['代码', '市盈率-动态', 'ROE', '总市值']
                        available_cols = [c for c in required_cols if c in spot_data.columns]
                        if len(available_cols) >= 2:
                            merged = hs300.merge(
                                spot_data[available_cols], 
                                left_on='code', right_on='代码', how='inner'
                            )
                            
                            if '市盈率-动态' in merged.columns:
                                merged['市盈率-动态'] = pd.to_numeric(merged['市盈率-动态'], errors='coerce')
                                merged = merged[(merged['市盈率-动态'] > 0) & (merged['市盈率-动态'] < 50)]
                            
                            if 'ROE' in merged.columns:
                                merged['ROE'] = pd.to_numeric(merged['ROE'], errors='coerce')
                                merged = merged[merged['ROE'] > 5]
                                merged = merged.sort_values('ROE', ascending=False)
                            
                            selected = merged['code'].head(self.stock_num_4).tolist()
                            return selected if selected else self._get_fallback_stocks_4()
                except Exception as e:
                    print(f"获取白马基本面数据失败: {e}，使用基础列表")
                
                return hs300['code'].head(self.stock_num_4).tolist()
            except Exception as e:
                print(f"白马策略执行失败: {e}")
        return self._get_fallback_stocks_4()
    
    def _get_fallback_stocks_4(self):
        """策略4的回退股票列表（经典白马股）"""
        return ['600519', '000858', '600036', '000333', '002415'][:self.stock_num_4]
    
    # ==================== 买入卖出模块 ====================
    def open_position(self, symbol, strategy_id, amount=None, value=None, target_date=None):
        """开仓买入"""
        try:
            current_price = self.get_current_prices([symbol], target_date)[symbol]
            if current_price == 0:
                print(f"无法获取{symbol}的当前价格")
                return False
            
            if value is not None:
                amount = int(value / current_price / 100) * 100
            elif amount is None:
                strategy_value = self.portfolio.total_value * self.strategy_weights[strategy_id-1]
                existing_count = len(self.strategy_holdings[strategy_id])
                stock_count = max(existing_count + 1, 1)
                per_stock_value = strategy_value / stock_count
                amount = int(per_stock_value / current_price / 100) * 100
            
            if amount <= 0:
                print(f"买入数量为0，跳过{symbol}")
                return False
            
            cost = amount * current_price
            if cost > self.portfolio.current_cash:
                adjusted_amount = int(self.portfolio.current_cash * 0.9 / current_price / 100) * 100
                if adjusted_amount <= 0:
                    print(f"资金不足，无法买入{symbol}")
                    return False
                amount = adjusted_amount
                cost = amount * current_price
            
            self.portfolio.add_position(symbol, amount, current_price)
            self.strategy_holdings[strategy_id].append(symbol)
            
            trade_record = {
                'date': target_date if target_date else datetime.datetime.now(),
                'action': 'BUY',
                'symbol': symbol,
                'strategy': strategy_id,
                'amount': amount,
                'price': current_price,
                'value': cost
            }
            self.trade_records.append(trade_record)
            
            print(f"✅ 策略{strategy_id}买入 {symbol}: {amount}股 @ {current_price:.2f}, 成本: {cost:.2f}")
            return True
            
        except Exception as e:
            print(f"开仓买入{symbol}失败: {e}")
            return False
    
    def close_position(self, symbol, strategy_id, target_date=None):
        """平仓卖出"""
        try:
            if symbol not in self.portfolio.positions:
                print(f"{symbol}不在持仓中")
                return False
            
            current_price = self.get_current_prices([symbol], target_date)[symbol]
            if current_price == 0:
                print(f"无法获取{symbol}的当前价格")
                return False
            
            position = self.portfolio.positions[symbol]
            profit = self.portfolio.remove_position(symbol, position['amount'], current_price)
            
            # 从策略持仓中移除
            if symbol in self.strategy_holdings[strategy_id]:
                self.strategy_holdings[strategy_id].remove(symbol)
            
            trade_record = {
                'date': target_date if target_date else datetime.datetime.now(),
                'action': 'SELL',
                'symbol': symbol,
                'strategy': strategy_id,
                'amount': position['amount'],
                'price': current_price,
                'profit': profit
            }
            self.trade_records.append(trade_record)
            
            profit_rate = profit / (position['amount'] * position['avg_cost']) if position['amount'] * position['avg_cost'] > 0 else 0
            print(f"✅ 策略{strategy_id}卖出 {symbol}: {position['amount']}股 @ {current_price:.2f}, 盈利: {profit:.2f}({profit_rate:.2%})")
            return True
            
        except Exception as e:
            print(f"平仓卖出{symbol}失败: {e}")
            return False
    
    def strategy_1_buy(self, current_date):
        """策略1买入函数"""
        stocks = self.strategy_1_small_cap(current_date)
        for stock in stocks:
            self.open_position(stock, 1, target_date=current_date)
    
    def strategy_1_sell(self, current_date):
        """策略1卖出函数"""
        for stock in self.strategy_holdings[1][:]:
            self.close_position(stock, 1, target_date=current_date)
    
    def strategy_2_buy(self, current_date):
        """策略2买入函数"""
        etfs = self.strategy_2_etf_rebound(current_date)
        for etf in etfs:
            self.open_position(etf, 2, target_date=current_date)
    
    def strategy_2_sell(self, current_date):
        """策略2卖出函数"""
        for etf in self.strategy_holdings[2][:]:
            self.close_position(etf, 2, target_date=current_date)
    
    def strategy_3_buy(self, current_date):
        """策略3买入函数"""
        etfs = self.strategy_3_etf_rotation(current_date)
        for etf in etfs:
            self.open_position(etf, 3, target_date=current_date)
    
    def strategy_3_sell(self, current_date):
        """策略3卖出函数"""
        for etf in self.strategy_holdings[3][:]:
            self.close_position(etf, 3, target_date=current_date)
    
    def strategy_4_buy(self, current_date):
        """策略4买入函数"""
        stocks = self.strategy_4_white_horse(current_date)
        for stock in stocks:
            self.open_position(stock, 4, target_date=current_date)
    
    def strategy_4_sell(self, current_date):
        """策略4卖出函数"""
        for stock in self.strategy_holdings[4][:]:
            self.close_position(stock, 4, target_date=current_date)
    
    # ==================== 风控模块 ====================
    def check_stoploss(self, current_date):
        """检查并执行止损"""
        if not self.portfolio.positions:
            return
        
        all_symbols = list(self.portfolio.positions.keys())
        current_prices = self.get_current_prices(all_symbols, target_date=current_date)
        
        for symbol, position in list(self.portfolio.positions.items()):
            current_price = current_prices.get(symbol, 0)
            if current_price <= 0:
                continue
            
            avg_cost = position['avg_cost']
            if avg_cost <= 0:
                continue
            
            loss_rate = (avg_cost - current_price) / avg_cost
            
            strategy_id = self._find_strategy_for_symbol(symbol)
            
            if loss_rate >= self.stoploss_limit:
                print(f"🔴 触发止损(限价): {symbol}, 亏损率: {loss_rate:.2%}, 阈值: {self.stoploss_limit:.2%}")
                if strategy_id:
                    self.close_position(symbol, strategy_id, target_date=current_date)
            
            elif loss_rate >= self.stoploss_market:
                print(f"🟡 触发止损(市价): {symbol}, 亏损率: {loss_rate:.2%}, 阈值: {self.stoploss_market:.2%}")
                if strategy_id:
                    self.close_position(symbol, strategy_id, target_date=current_date)
    
    def _find_strategy_for_symbol(self, symbol):
        """查找股票所属策略"""
        for sid, holdings in self.strategy_holdings.items():
            if symbol in holdings:
                return sid
        return None
    
    # ==================== 开盘前运行函数 ====================
    def before_market_open(self, current_date):
        """开盘前运行函数"""
        print(f"\n=== 开盘前准备 {current_date.strftime('%Y-%m-%d')} ===")
        
        all_symbols = list(self.portfolio.positions.keys())
        current_prices = self.get_current_prices(all_symbols, target_date=current_date)
        self.portfolio.update_portfolio(current_prices)
        
        if self.strategy_weights[0] > 0:
            self.prepare_xsz(current_date)
        
        if self.strategy_weights[3] > 0:
            self.bm_before_market_open(current_date)
    
    def prepare_xsz(self, current_date):
        """小市值策略开盘前准备"""
        print("执行小市值策略开盘前准备...")
        # 这里可以添加小市值策略的特殊开盘前逻辑
    
    def bm_before_market_open(self, current_date):
        """白马策略开盘前准备"""
        print("执行白马策略开盘前准备...")
        # 这里可以添加白马策略的特殊开盘前逻辑
    
    # ==================== 账本功能 ====================
    def update_portfolio_data(self, positions_data):
        """更新持仓数据（账本功能）"""
        print("更新持仓数据...")
        self.portfolio.positions = positions_data.copy()
        
        # 重新计算总价值
        all_symbols = list(self.portfolio.positions.keys())
        current_prices = self.get_current_prices(all_symbols)
        self.portfolio.update_portfolio(current_prices)
        
        print(f"持仓更新完成，当前总资产: {self.portfolio.total_value:.2f}")
    
    def print_portfolio_summary(self):
        """打印持仓摘要"""
        print("\n" + "="*60)
        print("持仓摘要")
        print("="*60)
        print(f"总资产: {self.portfolio.total_value:,.2f}")
        print(f"现金: {self.portfolio.current_cash:,.2f}")
        print(f"持仓市值: {self.portfolio.total_value - self.portfolio.current_cash:,.2f}")
        
        if self.portfolio.positions:
            print("\n持仓明细:")
            for symbol, position in self.portfolio.positions.items():
                current_price = self.get_current_prices([symbol])[symbol]
                profit = (current_price - position['avg_cost']) * position['amount']
                profit_rate = profit / (position['amount'] * position['avg_cost']) if position['amount'] * position['avg_cost'] > 0 else 0
                print(f"  {symbol}: {position['amount']}股, 成本: {position['avg_cost']:.2f}, "
                      f"现价: {current_price:.2f}, 盈亏: {profit:.2f}({profit_rate:.2%})")
    
    # ==================== 每日策略执行 ====================
    def execute_daily_strategy(self, current_date):
        """执行每日策略"""
        self.before_market_open(current_date)
        
        self.check_stoploss(current_date)
        
        strategy_results = {}
        
        if self.strategy_weights[0] > 0:
            strategy_results['strategy1'] = self.execute_strategy_1(current_date)
        
        if self.strategy_weights[1] > 0:
            strategy_results['strategy2'] = self.execute_strategy_2(current_date)
        
        if self.strategy_weights[2] > 0:
            strategy_results['strategy3'] = self.execute_strategy_3(current_date)
        
        if self.strategy_weights[3] > 0:
            strategy_results['strategy4'] = self.execute_strategy_4(current_date)
        
        all_symbols = list(self.portfolio.positions.keys())
        current_prices = self.get_current_prices(all_symbols, target_date=current_date)
        self.portfolio.update_portfolio(current_prices)
        
        # 记录每日结果
        daily_record = {
            'date': current_date,
            'total_value': self.portfolio.total_value,
            'strategy_results': strategy_results
        }
        self.portfolio.daily_records.append(daily_record)
        
        return strategy_results
    
    def execute_strategy_1(self, current_date):
        """执行策略1"""
        self.strategy_1_sell(current_date)
        self.strategy_1_buy(current_date)
        return self.strategy_holdings[1]
    
    def execute_strategy_2(self, current_date):
        """执行策略2"""
        self.strategy_2_sell(current_date)
        self.strategy_2_buy(current_date)
        return self.strategy_holdings[2]
    
    def execute_strategy_3(self, current_date):
        """执行策略3"""
        self.strategy_3_sell(current_date)
        self.strategy_3_buy(current_date)
        return self.strategy_holdings[3]
    
    def execute_strategy_4(self, current_date):
        """执行策略4"""
        self.strategy_4_sell(current_date)
        self.strategy_4_buy(current_date)
        return self.strategy_holdings[4]

# 使用示例和测试
if __name__ == "__main__":
    print("=== Cibo策略增强版本 ===")
    print("包含完整的买入卖出模块、回测功能和账本功能")
    
    # 创建策略实例
    strategy = CiboStrategyEnhanced(initial_capital=1000000)
    
    # 测试单日策略执行
    test_date = datetime.datetime.now()
    print(f"\n测试日期: {test_date.strftime('%Y-%m-%d')}")
    
    # 执行策略
    results = strategy.execute_daily_strategy(test_date)
    
    # 打印持仓摘要
    strategy.print_portfolio_summary()
    
    # 回测示例
    print("\n" + "="*50)
    print("回测示例")
    print("="*50)
    
    start_date = datetime.datetime(2024, 1, 1)
    end_date = datetime.datetime(2024, 1, 31)
    
    backtest_engine = BacktestEngine(strategy, start_date, end_date)
    backtest_results = backtest_engine.run_backtest()
    backtest_engine.generate_report()
    
    print("\n策略执行完成！")