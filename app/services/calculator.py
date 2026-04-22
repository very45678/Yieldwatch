"""年化收益率计算器"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from app.services.trading_calendar import get_next_trading_day, is_trading_day


# 年化收益率基准（货币基金年化约1%）
ANNUAL_RATE = 0.01


def calculate_annualized_return(
    ask_price: float,
    nav: float,
    nav_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    计算卖1价格买入赎回的年化收益率

    Args:
        ask_price: 卖1价格
        nav: 最近公布的净值
        nav_date: 净值日期 (YYYY-MM-DD)

    Returns:
        包含估算净值、年化收益率、占用天数的字典
    """
    if not ask_price or not nav:
        return {
            "estimated_nav": None,
            "annualized_return": None,
            "holding_days": None,
        }

    # 计算天数差（净值日期到今天）
    days = 1
    if nav_date:
        try:
            nav_datetime = datetime.strptime(nav_date, "%Y-%m-%d")
            days = max(1, (datetime.now() - nav_datetime).days)
        except ValueError:
            days = 1

    # 估算当日净值 = 最近净值 × (1 + 1% / 365 × 天数)
    estimated_nav = nav * (1 + ANNUAL_RATE / 365 * days)

    # 计算占用天数
    holding_days = calculate_holding_days()

    # 计算折价率
    discount_rate = (estimated_nav - ask_price) / estimated_nav

    # 计算年化收益率
    annualized_return = discount_rate * 365 / holding_days
    annualized_return_percent = annualized_return * 100  # 转换为百分比

    return {
        "estimated_nav": round(estimated_nav, 4),
        "annualized_return": round(annualized_return_percent, 2),
        "holding_days": holding_days,
    }


def calculate_holding_days() -> int:
    """
    计算实际占用天数

    T日买入，T+1日赎回款到账
    需要考虑周末和长假

    Returns:
        实际占用天数
    """
    today = datetime.now()

    # 使用交易日历计算下一个交易日
    next_trading_day = get_next_trading_day(today)
    holding_days = (next_trading_day - today).days

    # 最少占用1天
    return max(1, holding_days)
