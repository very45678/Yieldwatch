"""配置 API"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.config import settings

router = APIRouter()


class ThresholdConfig(BaseModel):
    """阈值配置"""
    threshold: float = Field(..., ge=0, le=100, description="年化收益率阈值（0-100%）")


class NotificationConfig(BaseModel):
    """通知配置"""
    bark_url: Optional[str] = None
    serverchan_key: Optional[str] = None
    email_smtp: Optional[str] = None
    email_user: Optional[str] = None
    email_password: Optional[str] = None
    email_to: Optional[str] = None


@router.get("/api/config/threshold")
async def get_threshold():
    """获取告警阈值"""
    return {"threshold": settings.alert_threshold}


@router.post("/api/config/threshold")
async def set_threshold(config: ThresholdConfig):
    """设置告警阈值"""
    settings.alert_threshold = config.threshold
    settings.save_runtime_config("alert_threshold", config.threshold)
    return {"threshold": settings.alert_threshold, "message": "阈值已更新"}


@router.get("/api/config/notification")
async def get_notification_config():
    """获取通知配置（不返回敏感凭证）"""
    return {
        "bark_configured": bool(settings.bark_url),
        "serverchan_configured": bool(settings.serverchan_key),
        "email_configured": bool(settings.email_smtp and settings.email_user),
    }


@router.post("/api/config/notification")
async def set_notification_config(config: NotificationConfig):
    """设置通知配置（敏感配置仅在内存中保存，重启后需重新配置）"""
    if config.bark_url is not None:
        settings.bark_url = config.bark_url
    if config.serverchan_key is not None:
        settings.serverchan_key = config.serverchan_key
    if config.email_smtp is not None:
        settings.email_smtp = config.email_smtp
    if config.email_user is not None:
        settings.email_user = config.email_user
    if config.email_password is not None:
        settings.email_password = config.email_password
    if config.email_to is not None:
        settings.email_to = config.email_to
    return {"message": "通知配置已更新（重启后需重新配置敏感信息）"}
