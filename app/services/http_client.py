"""HTTP客户端管理"""
import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 全局同步客户端实例
_sync_client: Optional[httpx.Client] = None


def get_http_client() -> httpx.Client:
    """
    获取全局HTTP客户端（延迟初始化）

    复用连接池，避免频繁创建/销毁连接

    Returns:
        httpx.Client: HTTP客户端实例
    """
    global _sync_client
    if _sync_client is None:
        _sync_client = httpx.Client(
            timeout=httpx.Timeout(10.0, connect=5.0),
            limits=httpx.Limits(
                max_connections=10,
                max_keepalive_connections=5,
                keepalive_expiry=30.0
            ),
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
            follow_redirects=True,
        )
        logger.debug("HTTP客户端已初始化")
    return _sync_client


def close_http_client():
    """关闭HTTP客户端，释放资源"""
    global _sync_client
    if _sync_client is not None:
        _sync_client.close()
        _sync_client = None
        logger.debug("HTTP客户端已关闭")
