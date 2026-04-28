"""数据采集器"""
import httpx
import time
import logging
import re
import json
from typing import Optional, Dict, Any, Callable
from datetime import datetime
import pandas as pd

from app.services.http_client import get_http_client

logger = logging.getLogger(__name__)

# AKShare 全市场 ETF 行情缓存（一次拉取所有 ETF，避免重复请求）
_akshare_etf_spot_cache: Dict[str, Any] = {"data": None, "timestamp": 0.0}
AKSHARE_ETF_CACHE_TTL = 30  # 缓存有效期（秒）

# AKShare 懒加载状态
_akshare_available = None  # None=未检测, True=可用, False=不可用


def _ensure_akshare() -> bool:
    """检测 AKShare 是否可用（仅检测一次）"""
    global _akshare_available
    if _akshare_available is not None:
        return _akshare_available
    try:
        import akshare as _
        _akshare_available = True
        logger.info("AKShare 可用，将作为主数据源")
    except ImportError:
        _akshare_available = False
        logger.warning("AKShare 不可用，将使用直接 HTTP 数据源")
    return _akshare_available


def _get_akshare_etf_spot() -> Optional[Any]:
    """获取带缓存的全市场 ETF 实时行情（来自 AKShare）"""
    if not _ensure_akshare():
        return None
    try:
        import akshare as ak
        import time as time_module
        now = time_module.time()
        if _akshare_etf_spot_cache["data"] is None or (now - _akshare_etf_spot_cache["timestamp"]) > AKSHARE_ETF_CACHE_TTL:
            logger.debug("从 AKShare 获取全市场 ETF 行情")
            _akshare_etf_spot_cache["data"] = ak.fund_etf_spot_em()
            _akshare_etf_spot_cache["timestamp"] = now
        return _akshare_etf_spot_cache["data"]
    except Exception as e:
        logger.warning(f"AKShare ETF 行情获取失败: {e}")
        return None


def _get_quote_akshare(code: str) -> Optional[Dict[str, Any]]:
    """从 AKShare 获取单只 ETF 行情（买一/卖一/最新价）"""
    df = _get_akshare_etf_spot()
    if df is None:
        return None
    try:
        code_str = str(code).zfill(6)
        row = df[df["代码"] == code_str]
        if row.empty:
            logger.debug(f"AKShare 未找到基金代码 {code}")
            return None
        bid = row["买一"].values[0]
        ask = row["卖一"].values[0]
        price = row["最新价"].values[0]
        if bid is None or ask is None or price is None:
            return None
        if float(bid) <= 0:
            return None
        return {
            "bid": float(bid),
            "ask": float(ask),
            "price": float(price),
            "source": "akshare",
            "timestamp": datetime.now().isoformat(),
        }
    except (KeyError, IndexError, ValueError) as e:
        logger.warning(f"AKShare 解析基金 {code} 数据失败: {e}")
        return None


def _get_nav_akshare(code: str) -> Optional[Dict[str, Any]]:
    """从 AKShare 获取单只 ETF 历史净值（最新一条）"""
    if not _ensure_akshare():
        return None
    try:
        import akshare as ak
        from datetime import datetime, timedelta
        code_str = str(code).zfill(6)
        # 只拉取最近 30 天数据，避免遍历大量历史分页（ETF 净值每日更新，30天足够）
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        df = ak.fund_etf_fund_info_em(
            fund=code_str,
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d"),
        )
        if df is None or df.empty:
            logger.debug(f"AKShare 未找到基金代码 {code} 的净值数据")
            return None
        latest = df.iloc[-1]  # API 返回升序数据，取最后一条为最新
        nav = latest.get("单位净值")
        date = latest.get("净值日期")
        if nav is None or pd.isna(nav):
            return None
        if date is None or pd.isna(date):
            return None
        if isinstance(date, str):
            date_str = date[:10] if len(date) > 10 else date
        else:
            date_str = date.strftime("%Y-%m-%d")
        return {
            "nav": float(nav),
            "date": date_str,
            "source": "akshare",
        }
    except Exception as e:
        logger.warning(f"AKShare 获取基金 {code} 净值失败: {e}")
        return None

MAX_RETRIES = 5
RETRY_DELAY = 1.0

QUOTE_SOURCES = {
    "sina": "https://hq.sinajs.cn/list=sh{code}",
    "eastmoney": "https://push2.eastmoney.com/api/qt/stock/get",
    "tencent": "https://qt.gtimg.cn/q=sh{code}",
}

NAV_SOURCES = {
    "eastmoney_api": "https://api.fund.eastmoney.com/f10/lsjz",
    "eastmoney_f10": "https://fundf10.eastmoney.com/FundArchivesDatas.aspx",
}


def fetch_quote(code: str) -> Optional[Dict[str, Any]]:
    # 主数据源：AKShare
    result = _fetch_with_retry(_get_quote_akshare, code, "AKShare行情")
    if result:
        return result

    # 备用数据源 1：新浪财经
    result = _fetch_with_retry(_fetch_quote_sina, code, "新浪行情")
    if result:
        return result

    # 备用数据源 2：腾讯行情
    result = _fetch_with_retry(_fetch_quote_tencent, code, "腾讯行情")
    if result:
        return result

    # 备用数据源 3：东方财富
    result = _fetch_with_retry(_fetch_quote_eastmoney, code, "东方财富行情")
    if result:
        return result

    logger.warning(f"获取 {code} 行情数据失败，所有数据源均不可用")
    return None


def fetch_nav(code: str) -> Optional[Dict[str, Any]]:
    # 主数据源：AKShare
    result = _fetch_with_retry(_get_nav_akshare, code, "AKShare净值")
    if result:
        return result

    # 备用数据源 1：东方财富净值 API
    result = _fetch_with_retry(_fetch_nav_eastmoney, code, "东方财富净值API")
    if result:
        return result

    # 备用数据源 2：东方财富 F10 页面
    result = _fetch_with_retry(_fetch_nav_fundf10, code, "东方财富F10净值")
    if result:
        return result

    logger.warning(f"获取 {code} 净值数据失败，所有数据源均不可用")
    return None


def _fetch_with_retry(
    fetch_func: Callable[[str], Optional[Dict[str, Any]]],
    code: str,
    source_name: str
) -> Optional[Dict[str, Any]]:
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


def _fetch_quote_sina(code: str) -> Optional[Dict[str, Any]]:
    url = QUOTE_SOURCES["sina"].format(code=code)
    headers = {
        "Referer": "https://finance.sina.com.cn/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    client = get_http_client()
    resp = client.get(url, headers=headers)
    resp.raise_for_status()
    resp.encoding = "gbk"
    data = resp.text

    if data and 'var hq_str' in data:
        match = re.search(r'="([^"]+)"', data)
        if match:
            parts = match.group(1).split(",")
            if len(parts) >= 30:
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


def _fetch_quote_tencent(code: str) -> Optional[Dict[str, Any]]:
    url = QUOTE_SOURCES["tencent"].format(code=code)
    headers = {
        "Referer": "https://gu.qq.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    client = get_http_client()
    resp = client.get(url, headers=headers)
    resp.raise_for_status()
    resp.encoding = "gbk"
    data = resp.text

    if data and f"v_sh{code}" in data:
        match = re.search(r'="([^"]+)"', data)
        if match:
            parts = match.group(1).split("~")
            if len(parts) >= 10:
                current_price = parts[3]
                bid_price = parts[9]
                ask_price = parts[10]

                if current_price and float(current_price) > 0:
                    return {
                        "bid": float(bid_price) if bid_price and float(bid_price) > 0 else float(current_price),
                        "ask": float(ask_price) if ask_price and float(ask_price) > 0 else float(current_price),
                        "price": float(current_price),
                        "timestamp": datetime.now().isoformat(),
                    }
    return None


def _fetch_quote_eastmoney(code: str) -> Optional[Dict[str, Any]]:
    secid = f"1.{code}"
    url = QUOTE_SOURCES["eastmoney"]
    params = {
        "secid": secid,
        "fields": "f43,f44,f45,f46",
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
            price = current_price / 1000
            return {
                "bid": price,
                "ask": price,
                "price": price,
                "timestamp": datetime.now().isoformat(),
            }
    return None


def _fetch_nav_eastmoney(code: str) -> Optional[Dict[str, Any]]:
    url = NAV_SOURCES["eastmoney_api"]
    headers = {
        "Referer": "https://fund.eastmoney.com/",
    }
    params = {
        "fundCode": code,
        "pageIndex": 1,
        "pageSize": 1,
    }

    client = get_http_client()
    resp = client.get(url, params=params, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    if data and "Data" in data and data["Data"]:
        lsjz_list = data["Data"].get("LSJZList")
        if lsjz_list and len(lsjz_list) > 0:
            latest = lsjz_list[0]
            nav = latest.get("DWJZ")
            date = latest.get("FSRQ")
            if nav and date:
                return {
                    "nav": float(nav),
                    "date": date,
                }

    return None


def _fetch_nav_fundf10(code: str) -> Optional[Dict[str, Any]]:
    url = NAV_SOURCES["eastmoney_f10"]
    headers = {
        "Referer": f"https://fundf10.eastmoney.com/jjjz_{code}.html",
    }
    params = {
        "type": "lsjz",
        "code": code,
        "per": 1,
        "page": 1,
    }

    client = get_http_client()
    resp = client.get(url, params=params, headers=headers)
    resp.raise_for_status()
    text = resp.text

    nav_match = re.search(r'class="tor bold">([\d.]+)', text)
    date_match = re.search(r'class="tdxdate">(\d{4}-\d{2}-\d{2})', text)
    if nav_match and date_match:
        return {
            "nav": float(nav_match.group(1)),
            "date": date_match.group(1),
        }

    nav_match2 = re.search(r'>([\d]{2,3}\.\d+)<', text)
    date_match2 = re.search(r'(\d{4}-\d{2}-\d{2})', text)
    if nav_match2 and date_match2:
        try:
            return {
                "nav": float(nav_match2.group(1)),
                "date": date_match2.group(1),
            }
        except ValueError:
            pass

    return None


def fetch_nav_yhj(code: str) -> Optional[Dict[str, Any]]:
    quote = fetch_quote(code)
    if quote and quote.get("price"):
        return {
            "nav": quote["price"],
            "date": datetime.now().strftime("%Y-%m-%d"),
        }
    return None
