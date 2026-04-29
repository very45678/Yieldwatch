"""SSE (Server-Sent Events) 实时推送"""
import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.services.data_service import get_fund_data_async
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

REDIS_CHANNEL = "fund_data_update"


async def event_generator(request: Request) -> AsyncGenerator[str, None]:
    client_id = id(request)
    logger.info(f"SSE 客户端连接: {client_id}")

    try:
        initial_data = await get_fund_data_async()
        initial_data["alert_threshold"] = settings.alert_threshold
        yield f"data: {json.dumps(initial_data, ensure_ascii=False)}\n\n"

        # 使用轮询模式，每 30 秒更新一次
        logger.info("SSE 使用轮询模式（30秒间隔）")
        while True:
            await asyncio.sleep(30)
            try:
                # 不再调用 update_fund_data()，只读取已有数据
                data = await get_fund_data_async()
                data["alert_threshold"] = settings.alert_threshold
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"SSE 数据更新失败: {e}")
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
