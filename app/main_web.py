"""Web 函数专用 FastAPI 入口（无调度器）"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import router
from app.api import sse
from app.services.http_client import close_http_client
from app.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Web 函数启动中...")
    yield
    logger.info("Web 函数关闭中...")
    close_http_client()
    logger.info("Web 函数已停止")


app = FastAPI(
    title=settings.app_name,
    description="银华日利(511880)和华宝添益(511990)折价套利监控系统",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(sse.router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")
