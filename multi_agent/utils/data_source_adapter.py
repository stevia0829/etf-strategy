"""
数据源适配器 - 包装现有 DataSourceManager
处理代码格式转换和 DataFrame 序列化
"""
import sys
import os
import json
from typing import Dict, List, Optional, Any

import pandas as pd

# 将父目录加入 path 以便 import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from multi_agent.utils.code_converter import jq_to_bare, jq_to_akshare, jq_to_baostock


class DataSourceAdapter:
    """统一数据源接口，包装现有 DataSourceManager"""

    _instance = None

    def __new__(cls, config_path: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path: Optional[str] = None):
        if self._initialized:
            return
        self._initialized = True
        self._init_data_sources(config_path)

    def _init_data_sources(self, config_path: Optional[str] = None):
        """初始化可用数据源（AKShare / Baostock / Tushare）"""
        self.data_sources = {}

        # 加载 tushare token
        self.tushare_token = None
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.tushare_token = config.get('tushare_token')
            except Exception:
                pass

        # AKShare（优先）
        try:
            import akshare as ak
            self.data_sources['akshare'] = ak
        except ImportError:
            pass

        # Baostock
        try:
            import baostock as bs
            lg = bs.login()
            if lg.error_code == '0':
                self.data_sources['baostock'] = bs
        except ImportError:
            pass

        # Tushare
        try:
            import tushare as ts
            if self.tushare_token:
                ts.set_token(self.tushare_token)
                self.data_sources['tushare'] = ts.pro_api()
            else:
                self.data_sources['tushare'] = ts
        except ImportError:
            pass

    def get_stock_data(self, jq_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取股票历史数据（输入输出均为 JoinQuant 代码格式）"""
        errors = []

        # Baostock
        if 'baostock' in self.data_sources:
            try:
                bs = self.data_sources['baostock']
                bs_code = jq_to_baostock(jq_code)
                rs = bs.query_history_k_data_plus(
                    bs_code, "date,open,high,low,close,volume",
                    start_date=start_date, end_date=end_date,
                    frequency="d", adjustflag="3"
                )
                data = []
                while (rs.error_code == '0') and rs.next():
                    data.append(rs.get_row_data())
                if data:
                    df = pd.DataFrame(data, columns=rs.fields)
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                    return df
            except Exception as e:
                errors.append(f"baostock: {e}")

        # AKShare
        if 'akshare' in self.data_sources:
            try:
                ak = self.data_sources['akshare']
                bare = jq_to_bare(jq_code)
                symbol = bare[:6]
                df = ak.stock_zh_a_hist(
                    symbol=symbol, period="daily",
                    start_date=start_date.replace('-', ''),
                    end_date=end_date.replace('-', ''),
                    adjust="hfq"
                )
                if not df.empty:
                    col_map = {'日期': 'date', '开盘': 'open', '最高': 'high',
                               '最低': 'low', '收盘': 'close', '成交量': 'volume'}
                    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
                    return df
            except Exception as e:
                errors.append(f"akshare: {e}")

        if errors:
            print(f"[DataSourceAdapter] 获取 {jq_code} 数据失败: {'; '.join(errors)}")
        return pd.DataFrame()

    def get_etf_data(self, jq_code: str, days: int = 30) -> pd.DataFrame:
        """获取 ETF 历史数据"""
        bare = jq_to_bare(jq_code)

        # AKShare 优先获取 ETF
        if 'akshare' in self.data_sources:
            try:
                ak = self.data_sources['akshare']
                df = ak.fund_etf_hist_sina(symbol=bare)
                if df is not None and not df.empty:
                    col_map = {'date': 'date', 'open': 'open', 'high': 'high',
                               'low': 'low', 'close': 'close', 'volume': 'volume'}
                    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
                    return df.tail(days)
            except Exception:
                pass

        # 回退到股票数据接口
        from datetime import datetime, timedelta
        end = datetime.now().strftime('%Y-%m-%d')
        start = (datetime.now() - timedelta(days=days * 2)).strftime('%Y-%m-%d')
        return self.get_stock_data(jq_code, start, end)

    def get_current_prices(self, jq_codes: List[str]) -> Dict[str, float]:
        """获取最新价格"""
        prices = {}
        if 'akshare' not in self.data_sources:
            return prices

        ak = self.data_sources['akshare']
        try:
            df = ak.stock_zh_a_spot_em()
            for jq_code in jq_codes:
                bare = jq_to_bare(jq_code)
                match = df[df['代码'] == bare]
                if not match.empty:
                    prices[jq_code] = float(match['最新价'].values[0])
        except Exception as e:
            print(f"[DataSourceAdapter] 获取最新价格失败: {e}")
        return prices

    def get_market_index_data(self, jq_codes: List[str]) -> Dict[str, Any]:
        """获取市场指数数据"""
        result = {}
        if 'akshare' not in self.data_sources:
            return result

        ak = self.data_sources['akshare']
        from datetime import datetime, timedelta
        end = datetime.now().strftime('%Y%m%d')
        start = (datetime.now() - timedelta(days=10)).strftime('%Y%m%d')

        for jq_code in jq_codes:
            bare = jq_to_bare(jq_code)
            try:
                df = ak.index_zh_a_hist(symbol=bare, period="daily",
                                        start_date=start, end_date=end)
                if not df.empty:
                    last = df.iloc[-1]
                    prev = df.iloc[-2] if len(df) > 1 else last
                    result[jq_code] = {
                        'close': float(last['收盘']),
                        'change_pct': round((float(last['收盘']) - float(prev['收盘'])) / float(prev['收盘']) * 100, 2),
                        'date': str(last['日期']),
                    }
            except Exception as e:
                print(f"[DataSourceAdapter] 获取指数 {jq_code} 失败: {e}")
        return result

    @staticmethod
    def serialize_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
        """将 DataFrame 序列化为 JSON 兼容 dict"""
        if df.empty:
            return {}
        return {col: df[col].tolist() for col in df.columns}
