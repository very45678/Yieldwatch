"""年化收益率计算器"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from app.services.trading_calendar import is_trading_day


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
        nav_date: 净值日期 (YYYY-MM-DD)，未使用，保留兼容性

    Returns:
        包含估算净值、年化收益率、占用天数的字典
    """
    if not ask_price or not nav:
        return {
            "estimated_nav": None,
            "annualized_return": None,
            "holding_days": None,
        }

    # 计算占用天数
    holding_days = calculate_holding_days()

    # 估算当日净值 = 最近净值 × (1 + 1% / 365 × 占用天数)
    estimated_nav = nav * (1 + ANNUAL_RATE / 365 * holding_days)

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
    计算实际资金占用天数

    T日买入（收盘前），T+1日到账
    T+1日如果是节假日/周末，延后到下一个交易日
    资金占用 = T+1日到账日 - 今天

    Returns:
        实际资金占用天数（自然日）
    """
    today = datetime.now()

    # T+1日（今天+1天）
    t_plus_1 = today + timedelta(days=1)

    # 如果T+1日是非交易日，顺延到下一个交易日
    settlement_day = t_plus_1
    for _ in range(30):
        if is_trading_day(settlement_day):
            break
        settlement_day += timedelta(days=1)

    # 计算从今天零点到到账日的自然天数
    today_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
    return (settlement_day - today_start).days
