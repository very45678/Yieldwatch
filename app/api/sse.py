"""SSE (Server-Sent Events) 实时推送"""
import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.services.data_service import get_fund_data_async, update_fund_data, _get_redis_async
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

REDIS_CHANNEL = "fund_data_update"

_pubsub_client = None


async def _get_pubsub_async():
    """获取异步 Redis PubSub 客户端"""
    global _pubsub_client
    if _pubsub_client is None:
        r = await _get_redis_async()
        if r is None:
            return None
        _pubsub_client = r.pubsub()
    return _pubsub_client


async def event_generator(request: Request) -> AsyncGenerator[str, None]:
    client_id = id(request)
    pubsub = await _get_pubsub_async()

    logger.info(f"SSE 客户端连接: {client_id}")

    try:
        initial_data = await get_fund_data_async()
        initial_data["alert_threshold"] = settings.alert_threshold
        yield f"data: {json.dumps(initial_data, ensure_ascii=False)}\n\n"

        if pubsub is None:
            logger.info("Redis 不可用，使用轮询模式（60秒间隔）")
            while True:
                await asyncio.sleep(60)
                try:
                    update_fund_data()
                    data = await get_fund_data_async()
                    data["alert_threshold"] = settings.alert_threshold
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"轮询更新失败: {e}")
                    yield f"data: {json.dumps({'heartbeat': True, 'ts': datetime.now().isoformat()}, ensure_ascii=False)}\n\n"

        await pubsub.subscribe(REDIS_CHANNEL)
        logger.info(f"已订阅 Redis 频道: {REDIS_CHANNEL}")

        last_heartbeat = datetime.now()
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
            if message and message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                except Exception as e:
                    logger.error(f"解析 Redis 消息失败: {e}")

            if (datetime.now() - last_heartbeat).seconds > 25:
                yield f"data: {json.dumps({'heartbeat': True, 'ts': datetime.now().isoformat()}, ensure_ascii=False)}\n\n"
                last_heartbeat = datetime.now()

            await asyncio.sleep(0.1)

    except asyncio.CancelledError:
        pass
    finally:
        try:
            if pubsub:
                await pubsub.unsubscribe(REDIS_CHANNEL)
        except Exception:
            pass
        logger.info(f"SSE 客户端断开: {client_id}")


@router.get("/api/sse")
async def sse_stream(request: Request):
    return StreamingResponse(
        event_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
