"""基金数据服务（线程安全 + Redis 异步持久化）"""
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from threading import RLock
import logging
import json
import os

from app.config import MONITORED_FUNDS, FUND_NAMES

logger = logging.getLogger(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", os.getenv("REDIS_URL", "localhost"))
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_KEY = "fund_data"

_redis_client = None


async def _get_redis_async():
    """获取异步 Redis 客户端（延迟初始化）"""
    global _redis_client
    if _redis_client is None:
        try:
            import redis.asyncio as redis_async
            _redis_client = redis_async.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=2,
            )
            await _redis_client.ping()
            logger.info(f"Redis 连接成功: {REDIS_HOST}:{REDIS_PORT}")
        except Exception as e:
            logger.warning(f"Redis 连接失败: {e}，使用内存存储")
            _redis_client = None
    return _redis_client


class FundDataService:
    """线程安全的基金数据服务"""

    def __init__(self):
        self._lock = RLock()
        self._data: Dict[str, Any] = {}
        self._initialize_data()

    def _initialize_data(self):
        """初始化数据结构"""
        with self._lock:
            for code in MONITORED_FUNDS:
                self._data[code] = {
                    "name": FUND_NAMES.get(code, code),
                    "code": code,
                    "bid_price": None,
                    "ask_price": None,
                    "nav": None,
                    "nav_date": None,
                    "estimated_nav": None,
                    "annualized_return": None,
                    "holding_days": None,
                    "updated_at": None,
                }
            self._data["last_update"] = None

    def _get_memory_data(self) -> Dict[str, Any]:
        """获取内存数据副本（线程安全）"""
        with self._lock:
            result = {}
            for key, value in self._data.items():
                if isinstance(value, dict):
                    result[key] = dict(value)
                else:
                    result[key] = value
            return result

    async def get_data(self) -> Dict[str, Any]:
        """获取数据副本（优先从 Redis 读取，兼容 Serverless）"""
        r = await _get_redis_async()
        if r is not None:
            try:
                raw = await r.get(REDIS_KEY)
                if raw:
                    data = json.loads(raw)
                    logger.debug("从 Redis 读取基金数据")
                    return data
            except Exception as e:
                logger.warning(f"Redis 读取失败，回退到内存: {e}")

        # 回退：使用内存数据
        return self._get_memory_data()

    def get_fund(self, code: str) -> Optional[Dict[str, Any]]:
        """获取单个基金数据"""
        with self._lock:
            if code in MONITORED_FUNDS and code in self._data:
                return dict(self._data[code])
            return None

    def update_fund_field(self, code: str, field: str, value: Any):
        """更新单个字段"""
        with self._lock:
            if code in self._data and field in self._data[code]:
                self._data[code][field] = value

    def update_all(self):
        """更新所有基金数据（同步版本，用于定时任务）"""
        from app.services.data_collector import fetch_quote, fetch_nav
        from app.services.calculator import calculate_annualized_return

        with self._lock:
            for code in MONITORED_FUNDS:
                try:
                    self._update_single_fund_sync(code)
                except Exception as e:
                    logger.error(f"更新基金 {code} 数据失败: {e}")

            self._data["last_update"] = datetime.now().isoformat()

        # 异步保存到 Redis（忽略失败，不阻塞主流程）
        try:
            loop = asyncio.get_running_loop()
            # 已在事件循环中，使用 create_task 避免阻塞
            asyncio.create_task(self._save_to_redis_async())
        except RuntimeError:
            # 不在事件循环中，不执行异步保存（避免嵌套事件循环问题）
            pass
        except Exception as e:
            logger.warning(f"Redis 异步保存失败: {e}")

    def _update_single_fund_sync(self, code: str):
        """更新单个基金数据（同步版本）"""
        from app.services.data_collector import fetch_quote, fetch_nav
        from app.services.calculator import calculate_annualized_return

        # 获取行情数据
        quote = fetch_quote(code)
        if quote:
            self._data[code]["bid_price"] = quote.get("bid")
            self._data[code]["ask_price"] = quote.get("ask")

        # 获取净值数据
        nav_info = fetch_nav(code)
        if nav_info:
            self._data[code]["nav"] = nav_info.get("nav")
            self._data[code]["nav_date"] = nav_info.get("date")

        # 货币ETF净值处理
        if code == "511990":
            # 华宝添益净值固定为100
            self._data[code]["nav"] = 100.0
        elif code == "511880":
            # 银华日利净值从实时价格估算
            if not self._data[code]["nav"] and self._data[code]["ask_price"]:
                self._data[code]["nav"] = self._data[code]["ask_price"]

        # 计算年化收益率
        if self._data[code]["ask_price"] and self._data[code]["nav"]:
            result = calculate_annualized_return(
                self._data[code]["ask_price"],
                self._data[code]["nav"],
                self._data[code]["nav_date"]
            )
            self._data[code]["estimated_nav"] = result.get("estimated_nav")
            self._data[code]["annualized_return"] = result.get("annualized_return")
            self._data[code]["holding_days"] = result.get("holding_days")

        self._data[code]["updated_at"] = datetime.now().isoformat()

    async def _save_to_redis_async(self):
        """异步保存数据到 Redis 并通知 SSE 客户端"""
        r = await _get_redis_async()
        if r is None:
            return
        try:
            with self._lock:
                data_copy = {}
                for key, value in self._data.items():
                    if isinstance(value, dict):
                        data_copy[key] = dict(value)
                    else:
                        data_copy[key] = value
            await r.set(REDIS_KEY, json.dumps(data_copy, ensure_ascii=False))
            logger.debug(f"数据已同步到 Redis: {REDIS_KEY}")

            # 通过 Redis Pub/Sub 通知 SSE 客户端
            try:
                await r.publish("fund_data_update", json.dumps(data_copy, ensure_ascii=False))
                logger.debug("Redis Pub/Sub 通知已发布")
            except Exception as e:
                logger.warning(f"Redis Pub/Sub 通知失败: {e}")
        except Exception as e:
            logger.warning(f"Redis 写入失败: {e}")


# 全局服务实例
fund_service = FundDataService()


def update_fund_data():
    """更新基金数据（兼容旧接口）"""
    fund_service.update_all()


async def get_fund_data_async() -> Dict[str, Any]:
    """获取基金数据（异步版本，推荐在 FastAPI 路由中使用）"""
    return await fund_service.get_data()


def get_fund_data() -> Dict[str, Any]:
    """获取基金数据（同步版本，兼容旧接口）"""
    # 同步版本：优先尝试从内存读取，避免阻塞
    with fund_service._lock:
        result = {}
        for key, value in fund_service._data.items():
            if isinstance(value, dict):
                result[key] = dict(value)
            else:
                result[key] = value
        return result
