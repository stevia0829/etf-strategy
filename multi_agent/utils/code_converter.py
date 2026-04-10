"""
股票代码格式互转工具
支持 JoinQuant / AKShare / Baostock / 纯数字 之间的转换
"""


def _detect_exchange(code: str) -> str:
    """根据代码判断交易所: 'sh' 或 'sz'"""
    bare = code.split('.')[0]
    if bare.startswith(('6', '9')):
        return 'sh'
    return 'sz'


def jq_to_akshare(code: str) -> str:
    """JoinQuant -> AKShare: '000001.XSHE' -> '000001.SZ'"""
    bare = code.split('.')[0]
    return f"{bare}.{_detect_exchange(code).upper()}"


def akshare_to_jq(code: str) -> str:
    """AKShare -> JoinQuant: '000001.SZ' -> '000001.XSHE'"""
    bare, suffix = code.split('.')
    if suffix.upper() == 'SZ':
        return f"{bare}.XSHE"
    return f"{bare}.XSHG"


def jq_to_baostock(code: str) -> str:
    """JoinQuant -> Baostock: '000001.XSHE' -> 'sz.000001'"""
    bare = code.split('.')[0]
    return f"{_detect_exchange(code)}.{bare}"


def baostock_to_jq(code: str) -> str:
    """Baostock -> JoinQuant: 'sz.000001' -> '000001.XSHE'"""
    prefix, bare = code.split('.')
    if prefix == 'sz':
        return f"{bare}.XSHE"
    return f"{bare}.XSHG"


def jq_to_bare(code: str) -> str:
    """JoinQuant -> 纯数字: '000001.XSHE' -> '000001'"""
    return code.split('.')[0]


def bare_to_jq(code: str) -> str:
    """纯数字 -> JoinQuant: '000001' -> '000001.XSHE'"""
    if code.startswith(('6', '9')):
        return f"{code}.XSHG"
    return f"{code}.XSHE"
