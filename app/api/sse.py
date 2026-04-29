"""SSE (Server-Sent Events) 实时推送"""
import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.services.data_service import get_fund_data_async, update_fund_data
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# 轮询间隔（秒），避免触发外部 API 限流
POLL_INTERVAL = 30


async def event_generator(request: Request) -> AsyncGenerator[str, None]:
    client_id = id(request)

    logger.info(f"SSE 客户端连接: {client_id}")

    try:
        # 在线程池中执行首次数据更新
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, update_fund_data)

        # 发送初始数据
        initial_data = await get_fund_data_async()
        initial_data["alert_threshold"] = settings.alert_threshold
        yield f"data: {json.dumps(initial_data, ensure_ascii=False)}\n\n"
        logger.info(f"SSE 初始数据已发送: {initial_data.get('last_update')}")

        # 轮询模式
        while True:
            await asyncio.sleep(POLL_INTERVAL)
            try:
                # 在线程池中执行同步更新
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, update_fund_data)
                data = await get_fund_data_async()
                data["alert_threshold"] = settings.alert_threshold
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                logger.info(f"SSE 轮询数据已发送: {data.get('last_update')}")
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"轮询更新失败: {e}")
                yield f"data: {json.dumps({'heartbeat': True, 'ts': datetime.now().isoformat()}, ensure_ascii=False)}\n\n"

    except asyncio.CancelledError:
        pass
    finally:
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
