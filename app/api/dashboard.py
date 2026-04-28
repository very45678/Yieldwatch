"""仪表盘 API"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.data_service import get_fund_data, get_fund_data_async, update_fund_data
from app.config import settings

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    data = await get_fund_data_async()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "data": data}
    )


@router.get("/api/data")
async def get_data():
    update_fund_data()
    data = await get_fund_data_async()
    data["alert_threshold"] = settings.alert_threshold
    return data


@router.post("/api/refresh")
async def refresh_data():
    update_fund_data()
    data = await get_fund_data_async()
    data["alert_threshold"] = settings.alert_threshold
    return data
