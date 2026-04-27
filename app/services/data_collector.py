"""数据采集器"""
import httpx
import time
import logging
import re
import json
from typing import Optional, Dict, Any, Callable
from datetime import datetime

from app.services.http_client import get_http_client

logger = logging.getLogger(__name__)

# 重试配置
MAX_RETRIES = 5
RETRY_DELAY = 2.0  # 秒

# 数据源配置
QUOTE_SOURCES = {
    "eastmoney": "https://push2.eastmoney.com/api/qt/stock/get",
    "sina": "https://hq.sinajs.cn/list=sh{code}",
    "yahoo": "https://query1.finance.yahoo.com/v8/finance/chart/{code}",
}

NAV_SOURCES = {
    "eastmoney": "https://fund.eastmoney.com/pingzhl{code}.html",
    "fundf10": "https://fundf10.eastmoney.com/jjjz_{code}.html",
}


def fetch_quote(code: str) -> Optional[Dict[str, Any]]:
    """
    获取基金行情数据（买1/卖1价格）

    按优先级依次尝试数据源，直到成功获取数据

    Args:
        code: 基金代码

    Returns:
        包含bid、ask、price、timestamp的字典，或None
    """
    # 优先使用新浪数据源（买卖盘数据准确）
    result = _fetch_with_retry(_fetch_quote_sina, code, "新浪行情")
    if result:
        return result

    # 尝试东方财富数据源
    result = _fetch_with_retry(_fetch_quote_eastmoney, code, "东方财富行情")
    if result:
        return result

    # 尝试 Yahoo Finance 数据源（国际访问友好）
    result = _fetch_with_retry(_fetch_quote_yahoo, code, "Yahoo行情")
    if result:
        return result

    logger.warning(f"获取 {code} 行情数据失败，所有数据源均不可用")
    return None


def fetch_nav(code: str) -> Optional[Dict[str, Any]]:
    """
    获取基金净值数据

    按优先级依次尝试数据源，直到成功获取数据

    Args:
        code: 基金代码

    Returns:
        包含nav、date的字典，或None
    """
    result = _fetch_with_retry(_fetch_nav_eastmoney, code, "东方财富净值")
    if result:
        return result

    result = _fetch_with_retry(_fetch_nav_fundf10, code, "FundF10净值")
    if result:
        return result

    # 尝试 Yahoo Finance 数据源（国际访问友好）
    result = _fetch_with_retry(_fetch_nav_yahoo, code, "Yahoo净值")
    if result:
        return result

    logger.warning(f"获取 {code} 净值数据失败，所有数据源均不可用")
    return None


def _fetch_with_retry(
    fetch_func: Callable[[str], Optional[Dict[str, Any]]],
    code: str,
    source_name: str
) -> Optional[Dict[str, Any]]:
    """
    带重试机制的获取函数

    Args:
        fetch_func: 数据获取函数
        code: 基金代码
        source_name: 数据源名称（用于日志）

    Returns:
        获取结果或 None
    """
    last_error: Optional[Exception] = None

    for attempt in range(MAX_RETRIES):
        try:
            result = fetch_func(code)
            if result:
                logger.debug(f"从 {source_name} 获取 {code} 数据成功")
                return result
        except httpx.TimeoutException as e:
            last_error = e
            logger.warning(
                f"从 {source_name} 获取 {code} 数据超时 (尝试 {attempt + 1}/{MAX_RETRIES})"
            )
        except httpx.HTTPStatusError as e:
            last_error = e
            logger.warning(
                f"从 {source_name} 获取 {code} HTTP错误 {e.response.status_code} "
                f"(尝试 {attempt + 1}/{MAX_RETRIES})"
            )
        except httpx.RequestError as e:
            last_error = e
            logger.warning(
                f"从 {source_name} 获取 {code} 网络错误: {e} "
                f"(尝试 {attempt + 1}/{MAX_RETRIES})"
            )
        except (ValueError, KeyError, IndexError) as e:
            last_error = e
            logger.warning(
                f"从 {source_name} 解析 {code} 数据失败: {e} "
                f"(尝试 {attempt + 1}/{MAX_RETRIES})"
            )
        except Exception as e:
            last_error = e
            logger.error(
                f"从 {source_name} 获取 {code} 数据未知错误: {e} "
                f"(尝试 {attempt + 1}/{MAX_RETRIES})"
            )

        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY)

    if last_error:
        logger.error(f"从 {source_name} 获取 {code} 数据最终失败: {last_error}")
    return None


def _fetch_quote_eastmoney(code: str) -> Optional[Dict[str, Any]]:
    """
    从东方财富获取行情数据

    注意：东方财富API只返回当前价，无买卖盘数据
    """
    secid = f"1.{code}"
    url = QUOTE_SOURCES["eastmoney"]
    params = {
        "secid": secid,
        "fields": "f43,f44,f45,f46",  # 最新价、最高、最低、今开
        "ut": "fa5fd1943c7b386f172d6893dbfba10b",
    }
    headers = {
        "Referer": "https://quote.eastmoney.com/",
    }

    client = get_http_client()
    resp = client.get(url, params=params, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    if data and "data" in data and data["data"]:
        d = data["data"]
        current_price = d.get("f43")

        if current_price:
            # 东方财富不提供买卖盘数据，使用当前价近似
            price = current_price / 1000
            return {
                "bid": price,  # 近似
                "ask": price,  # 近似
                "price": price,
                "timestamp": datetime.now().isoformat(),
            }
    return None


def _fetch_quote_sina(code: str) -> Optional[Dict[str, Any]]:
    """从新浪获取行情数据"""
    url = QUOTE_SOURCES["sina"].format(code=code)
    headers = {
        "Referer": "https://finance.sina.com.cn/",
    }

    client = get_http_client()
    resp = client.get(url, headers=headers)
    resp.raise_for_status()
    resp.encoding = "gbk"
    data = resp.text
    logger.debug(f"新浪行情响应: {data[:200] if data else 'empty'}...")

    if data and 'var hq_str' in data:
        # 解析数据：var hq_str_sh511880="..."
        match = re.search(r'="([^"]+)"', data)
        if match:
            parts = match.group(1).split(",")
            if len(parts) >= 30:
                # 新浪数据格式：
                # 索引 0: 名称, 1: 今开, 2: 昨收, 3: 当前价
                # 索引 11: 买1价, 21: 卖1价
                bid_price = parts[11]
                ask_price = parts[21]
                current_price = parts[3]

                if bid_price and ask_price and float(bid_price) > 0:
                    return {
                        "bid": float(bid_price),
                        "ask": float(ask_price),
                        "price": float(current_price) if current_price else None,
                        "timestamp": datetime.now().isoformat(),
                    }
    return None


def _fetch_nav_eastmoney(code: str) -> Optional[Dict[str, Any]]:
    """从东方财富获取货币基金净值数据"""
    url = f"https://fundgz.eastmoney.com/pingzhl{code}.html"
    headers = {
        "Referer": "https://fund.eastmoney.com/",
    }

    client = get_http_client()
    resp = client.get(url, headers=headers)
    resp.raise_for_status()
    text = resp.text
    logger.debug(f"东方财富净值响应长度: {len(text)}")

    # 尝试解析JSONP响应
    jsonp_match = re.search(r'jsonp\((.*)\)', text)
    if jsonp_match:
        try:
            data = json.loads(jsonp_match.group(1))
            if "Data" in data and data["Data"]:
                latest = data["Data"][0]
                nav = latest.get("DWJZ")
                date = latest.get("FSRQ")
                if nav and date:
                    return {
                        "nav": float(nav),
                        "date": date,
                    }
        except json.JSONDecodeError as e:
            logger.debug(f"JSONP解析失败: {e}")

    # 备用：从HTML解析
    nav_match = re.search(r'单位净值[：:]\s*([\d.]+)', text)
    date_match = re.search(r'净值日期[：:]\s*(\d{4}-\d{2}-\d{2})', text)
    if nav_match and date_match:
        return {
            "nav": float(nav_match.group(1)),
            "date": date_match.group(1),
        }

    return None


def _fetch_nav_fundf10(code: str) -> Optional[Dict[str, Any]]:
    """从FundF10获取净值数据（备用源）"""
    url = f"https://fundf10.eastmoney.com/jjjz_{code}.html"
    headers = {
        "Referer": "https://fund.eastmoney.com/",
    }

    client = get_http_client()
    resp = client.get(url, headers=headers)
    resp.raise_for_status()
    text = resp.text

    # 尝试从页面内嵌的JSON数据获取
    json_match = re.search(r'data:\s*(\[.*?\])', text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            if data and len(data) > 0:
                latest = data[0]
                return {
                    "nav": float(latest.get("DWJZ", 0)),
                    "date": latest.get("FSRQ", ""),
                }
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.debug(f"FundF10 JSON解析失败: {e}")

    return None


def _fetch_quote_yahoo(code: str) -> Optional[Dict[str, Any]]:
    """从 Yahoo Finance 获取行情数据（国际数据源）"""
    # Yahoo Finance 上中国 ETF 代码格式：511990.SH, 511880.SH
    yahoo_code = f"{code}.SS"
    url = QUOTE_SOURCES["yahoo"].format(code=yahoo_code)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    client = get_http_client()
    resp = client.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    if data and "chart" in data and data["chart"]["result"]:
        result = data["chart"]["result"][0]
        meta = result.get("meta", {})
        price = meta.get("regularMarketPrice")
        if price:
            return {
                "bid": price,
                "ask": price,
                "price": price,
                "timestamp": datetime.now().isoformat(),
            }
    return None


def _fetch_nav_yahoo(code: str) -> Optional[Dict[str, Any]]:
    """从 Yahoo Finance 获取净值数据（国际数据源）"""
    # Yahoo Finance 上中国 ETF 代码格式：511990.SS, 511880.SS
    yahoo_code = f"{code}.SS"
    url = QUOTE_SOURCES["yahoo"].format(code=yahoo_code)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    client = get_http_client()
    resp = client.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    if data and "chart" in data and data["chart"]["result"]:
        result = data["chart"]["result"][0]
        meta = result.get("meta", {})
        price = meta.get("regularMarketPrice")
        # 货币基金净值日期（Yahoo 不提供独立净值日期，使用交易日）
        if price:
            return {
                "nav": price,
                "date": datetime.now().strftime("%Y-%m-%d"),
            }
    return None


def fetch_nav_yhj(code: str) -> Optional[Dict[str, Any]]:
    """
    获取货币基金净值数据（备用）

    对于货币ETF，净值等于最新价
    """
    quote = fetch_quote(code)
    if quote and quote.get("price"):
        return {
            "nav": quote["price"],
            "date": datetime.now().strftime("%Y-%m-%d"),
        }
    return None
