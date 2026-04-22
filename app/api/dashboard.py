"""仪表盘 API"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.data_service import fund_service, get_fund_data
from app.config import settings

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """主页"""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "data": get_fund_data()}
    )


@router.get("/api/data")
async def get_data():
    """获取实时数据"""
    response = get_fund_data()
    response["alert_threshold"] = settings.alert_threshold
    return response
