"""API路由"""
from fastapi import APIRouter

from app.api import dashboard, config, health

router = APIRouter()
router.include_router(dashboard.router, tags=["dashboard"])
router.include_router(config.router, tags=["config"])
router.include_router(health.router, tags=["health"])
