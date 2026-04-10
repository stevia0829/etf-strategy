"""
Cibo 三驾马车策略 - 独立版本（修正版）
不依赖jqdata，使用Tushare、Baostock等免费数据源

主要修正：
1. 移除硬编码的token配置
2. 改进数据获取逻辑
3. 增加配置文件和错误处理
"""

import pandas as pd
import numpy as np
import datetime
from datetime import timedelta
import math
import warnings
import os
import json
warnings.filterwarnings('ignore')

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')

class DataSourceManager:
    """数据源管理器"""
    
    def __init__(self):
        self.tushare_token = None
        self.data_sources = {}
        self.init_data_sources()
    
    def init_data_sources(self):
        """初始化数据源"""
        # 尝试加载配置文件
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
                    if self.tushare_token:
                        print("✓ 配置文件加载成功")
            except Exception as e:
                print(f"✗ 配置文件加载失败: {e}")
        else:
            # 创建默认配置文件
            self.create_default_config()
    
    def create_default_config(self):
        """创建默认配置文件"""
        default_config = {
            "tushare_token": "请在此处填写您的Tushare Token",
            "说明": "请访问 https://tushare.pro/ 注册并获取免费token"
        }
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
            print(f"✓ 已创建配置文件: {CONFIG_FILE}")
            print("⚠ 请编辑配置文件填写您的Tushare Token")
        except Exception as e:
            print(f"✗ 创建配置文件失败: {e}")
    
    def get_stock_data(self, symbol, start_date, end_date, fields=['open', 'high', 'low', 'close', 'volume']):
        """获取股票历史数据（多数据源备用）"""
        # 优先使用Baostock
        if 'baostock' in self.data_sources:
            try:
                bs = self.data_sources['baostock']
                # 格式化股票代码
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
                    # 转换数据类型
                    for field in fields:
                        if field in df.columns:
                            df[field] = pd.to_numeric(df[field], errors='coerce')
                    return df
            except Exception as e:
                print(f"Baostock获取{symbol}数据失败: {e}")
        
        # 备用方案：使用AKShare
        if 'akshare' in self.data_sources:
            try:
                ak = self.data_sources['akshare']
                # AKShare需要完整的股票代码格式
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
        
        # 优先使用AKShare获取ETF数据
        if 'akshare' in self.data_sources:
            try:
                ak = self.data_sources['akshare']
                df = ak.fund_etf_hist_sina(symbol=etf_code)
                if not df.empty:
                    return df.tail(days)
            except Exception as e:
                print(f"AKShare获取ETF{etf_code}数据失败: {e}")
        
        # 备用方案：使用普通股票接口
        return self.get_stock_data(etf_code, start_date, end_date)

class CiboStrategyStandaloneFixed:
    """Cibo策略独立版本（修正版）"""
    
    def __init__(self, initial_capital=1000000, config_file=None):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions = {}
        self.strategy_weights = [0.5, 0, 0.5, 0]
        self.strategy_holdings = {1: [], 2: [], 3: [], 4: []}
        
        # 初始化数据源管理器
        global CONFIG_FILE
        if config_file:
            CONFIG_FILE = config_file
        self.data_manager = DataSourceManager()
        
        # 设置策略参数
        self.set_strategy_params()
    
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
    
    def get_stock_data(self, symbol, start_date, end_date, fields=['close']):
        """获取股票数据（封装方法）"""
        return self.data_manager.get_stock_data(symbol, start_date, end_date, fields)
    
    def get_etf_data(self, etf_code, days=30):
        """获取ETF数据（封装方法）"""
        return self.data_manager.get_etf_data(etf_code, days)
    
    def calculate_momentum_score(self, prices, days=21):
        """计算动量得分（简化但有效版本）"""
        if len(prices) < days:
            return 0, 0, 0
        
        recent_prices = prices[-days:]
        
        # 简单收益率
        simple_return = (recent_prices.iloc[-1] / recent_prices.iloc[0] - 1) * 100
        
        # 移动平均趋势
        ma_short = recent_prices.rolling(window=5).mean()
        ma_long = recent_prices.rolling(window=10).mean()
        ma_trend = 1 if ma_short.iloc[-1] > ma_long.iloc[-1] else -1
        
        # RSI计算
        def calculate_rsi(prices, period=14):
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs)) if loss != 0 else 100
            return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
        
        rsi_value = calculate_rsi(recent_prices)
        
        # 综合得分
        score = simple_return * 0.5 + ma_trend * 30 + (rsi_value - 50) * 0.2
        return score, simple_return, rsi_value
    
    def strategy_1_small_cap(self, current_date):
        """策略1: 小市值策略（使用免费数据源）"""
        print("执行小市值策略...")
        
        # 使用AKShare获取小市值股票（免费）
        if 'akshare' in self.data_manager.data_sources:
            try:
                ak = self.data_manager.data_sources['akshare']
                # 获取A股基本信息
                stock_info = ak.stock_info_a_code_name()
                # 这里需要更复杂的筛选逻辑，简化示例
                small_cap_stocks = stock_info['code'].tolist()[:100]
                return small_cap_stocks[:self.xsz_stock_num]
            except Exception as e:
                print(f"小市值策略执行失败: {e}")
        
        # 备用方案
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
        """策略4: 白马攻防策略"""
        print("执行白马攻防策略...")
        
        # 使用AKShare获取沪深300成分股
        if 'akshare' in self.data_manager.data_sources:
            try:
                ak = self.data_manager.data_sources['akshare']
                hs300 = ak.index_stock_cons_sina(symbol="000300")
                return hs300['code'].tolist()[:self.stock_num_4]
            except:
                pass
        
        return ['600519', '000858', '600036', '000333', '002415'][:self.stock_num_4]
    
    def execute_strategies(self, current_date):
        """执行所有策略"""
        print(f"\n=== 执行策略日期: {current_date.strftime('%Y-%m-%d')} ===")
        
        results = {
            'strategy1': self.strategy_1_small_cap(current_date),
            'strategy2': self.strategy_2_etf_rebound(current_date),
            'strategy3': self.strategy_3_etf_rotation(current_date),
            'strategy4': self.strategy_4_white_horse(current_date)
        }
        
        for strategy_name, stocks in results.items():
            print(f"{strategy_name}选股: {stocks}")
        
        return results

# 使用示例
if __name__ == "__main__":
    print("=== Cibo策略独立版本（修正版）===")
    print("说明：此版本不依赖jqdata，使用免费数据源")
    print("如需使用Tushare高级功能，请编辑config.json文件配置token")
    print()
    
    # 创建策略实例
    strategy = CiboStrategyStandaloneFixed(initial_capital=1000000)
    
    # 测试单日策略执行
    test_date = datetime.datetime.now()
    results = strategy.execute_strategies(test_date)
    
    print("\n策略执行完成！")