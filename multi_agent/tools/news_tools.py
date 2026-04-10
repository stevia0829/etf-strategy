"""
新闻聚合工具 - 多源新闻获取 + LLM 地缘风险分析
"""
import time
from typing import Dict, List, Any

from langchain_core.tools import tool


@tool
def fetch_financial_news(limit: int = 20) -> List[Dict[str, str]]:
    """获取 A 股财经新闻（AKShare 东方财富源）。

    Args:
        limit: 获取条数，默认 20

    Returns:
        [{title, content, source, date}]
    """
    news_list = []
    try:
        import akshare as ak
        # 全球财经新闻
        df = ak.stock_info_global_em()
        if df is not None and not df.empty:
            for _, row in df.head(limit).iterrows():
                news_list.append({
                    'title': str(row.get('标题', '')),
                    'content': str(row.get('内容', '')),
                    'source': 'eastmoney_global',
                    'date': str(row.get('发布时间', '')),
                })
    except Exception as e:
        print(f"[news] 获取全球新闻失败: {e}")

    time.sleep(0.5)

    try:
        import akshare as ak
        # A 股市场新闻
        df = ak.stock_news_em(symbol="A股")
        if df is not None and not df.empty:
            for _, row in df.head(limit).iterrows():
                news_list.append({
                    'title': str(row.get('新闻标题', '')),
                    'content': str(row.get('新闻内容', '')),
                    'source': 'eastmoney_stock',
                    'date': str(row.get('发布时间', '')),
                })
    except Exception as e:
        print(f"[news] 获取A股新闻失败: {e}")

    return news_list


@tool
def fetch_sector_news(sector_keywords: Dict[str, List[str]], limit: int = 5) -> Dict[str, List[Dict[str, str]]]:
    """按板块关键词搜索相关新闻。

    Args:
        sector_keywords: {板块名: [关键词列表]}
        limit: 每个板块获取条数

    Returns:
        {板块名: [{title, content, source, date}]}
    """
    result = {}
    try:
        import akshare as ak
        df = ak.stock_info_global_em()
        if df is None or df.empty:
            return result

        for sector, keywords in sector_keywords.items():
            sector_news = []
            for _, row in df.iterrows():
                title = str(row.get('标题', ''))
                content = str(row.get('内容', ''))
                text = title + content
                if any(kw in text for kw in keywords):
                    sector_news.append({
                        'title': title,
                        'content': content[:200],
                        'source': 'eastmoney',
                        'date': str(row.get('发布时间', '')),
                    })
                    if len(sector_news) >= limit:
                        break
            result[sector] = sector_news
            time.sleep(0.3)
    except Exception as e:
        print(f"[news] 板块新闻获取失败: {e}")

    return result


@tool
def search_web(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """网络搜索工具（用于获取最新地缘政治风险信息）。

    Args:
        query: 搜索关键词
        max_results: 最大结果数

    Returns:
        [{title, content, source}]
    """
    results = []
    try:
        from langchain_community.tools import DuckDuckGoSearchResults
        search = DuckDuckGoSearchResults(max_results=max_results)
        raw = search.invoke(query)
        # DuckDuckGoSearchResults 返回格式化的字符串
        results.append({
            'title': query,
            'content': raw,
            'source': 'duckduckgo',
        })
    except ImportError:
        # 尝试 tavily
        try:
            from tavily import TavilyClient
            import os
            client = TavilyClient(api_key=os.environ.get('TAVILY_API_KEY', ''))
            response = client.search(query, max_results=max_results)
            for item in response.get('results', []):
                results.append({
                    'title': item.get('title', ''),
                    'content': item.get('content', ''),
                    'source': 'tavily',
                })
        except Exception as e:
            print(f"[news] 网络搜索失败（duckduckgo 和 tavily 均不可用）: {e}")
    except Exception as e:
        print(f"[news] 网络搜索失败: {e}")

    return results


def get_news_tools():
    """返回所有新闻工具列表"""
    return [fetch_financial_news, fetch_sector_news, search_web]
