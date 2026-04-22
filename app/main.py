"""FastAPI 应用入口"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.api import router
from app.services.scheduler import start_scheduler, stop_scheduler
from app.services.http_client import close_http_client
from app.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("应用启动中...")
    start_scheduler()
    logger.info("调度器已启动")
    yield
    # 关闭时
    logger.info("应用关闭中...")
    stop_scheduler()
    close_http_client()
    logger.info("应用已停止")


app = FastAPI(
    title=settings.app_name,
    description="银华日利(511880)和华宝添益(511990)折价套利监控系统",
    version="0.1.0",
    lifespan=lifespan,
)

# 注册路由
app.include_router(router)

# 静态文件
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 模板
templates = Jinja2Templates(directory="app/templates")
