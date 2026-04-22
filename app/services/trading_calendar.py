"""交易日历

使用 chinese_calendar 库自动判断中国法定节假日，无需手动维护。
支持自定义额外假期（如临时休市）的配置。
"""
from datetime import datetime, time, timedelta
from typing import List, Tuple, Optional
import logging

try:
    import chinese_calendar as cc
    CHINESE_CALENDAR_AVAILABLE = True
except ImportError:
    CHINESE_CALENDAR_AVAILABLE = False
    logging.warning(
        "chinese_calendar 库未安装，将使用基础周末判断。"
        "建议运行: pip install chinesecalendar"
    )

logger = logging.getLogger(__name__)

# 自定义额外假期（用于临时休市等特殊情况）
# 格式：("开始日期", "结束日期")
CUSTOM_HOLIDAYS: List[Tuple[str, str]] = [
    # 示例：临时休市
    # ("2024-10-08", "2024-10-08"),
]

# 自定义额外工作日（用于周末补班）
# 格式："YYYY-MM-DD"
CUSTOM_WORKDAYS: List[str] = [
    # 示例：周末调休上班
    # "2024-04-07",
]


def is_holiday(date: datetime) -> bool:
    """
    判断是否为节假日

    Args:
        date: 日期

    Returns:
        是否为节假日
    """
    date_str = date.strftime("%Y-%m-%d")

    # 检查自定义假期
    for start, end in CUSTOM_HOLIDAYS:
        if start <= date_str <= end:
            return True

    # 检查自定义工作日（周末补班）
    if date_str in CUSTOM_WORKDAYS:
        return False

    # 使用 chinese_calendar 判断
    if CHINESE_CALENDAR_AVAILABLE:
        try:
            # is_holiday 返回是否为节假日（包括周末调休成的假期）
            # is_workday 返回是否为工作日（包括周末调休成的工作日）
            return cc.is_holiday(date.date())
        except Exception as e:
            logger.warning(f"chinese_calendar 判断失败: {e}，使用基础判断")

    # 回退：仅判断周末
    return date.weekday() >= 5


def is_trading_day(date: Optional[datetime] = None) -> bool:
    """
    判断是否为交易日

    Args:
        date: 日期，默认今天

    Returns:
        是否为交易日
    """
    if date is None:
        date = datetime.now()

    # 使用 chinese_calendar 判断工作日
    if CHINESE_CALENDAR_AVAILABLE:
        try:
            return cc.is_workday(date.date())
        except Exception as e:
            logger.warning(f"chinese_calendar 判断失败: {e}，使用基础判断")

    # 回退：周末非交易日
    return date.weekday() < 5


def is_trading_time(dt: Optional[datetime] = None) -> bool:
    """
    判断是否为交易时间（交易日 9:30-15:00）

    Args:
        dt: 日期时间，默认当前时间

    Returns:
        是否为交易时间
    """
    if dt is None:
        dt = datetime.now()

    # 先判断是否为交易日
    if not is_trading_day(dt):
        return False

    # 判断是否在交易时段
    current_time = dt.time()
    start_time = time(9, 30)
    end_time = time(15, 0)

    return start_time <= current_time <= end_time


def get_next_trading_day(date: Optional[datetime] = None) -> datetime:
    """
    获取下一个交易日

    Args:
        date: 起始日期

    Returns:
        下一个交易日（返回当天的 00:00:00）
    """
    if date is None:
        date = datetime.now()

    next_day = (date + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # 最多查找30天（防止无限循环）
    for _ in range(30):
        if is_trading_day(next_day):
            return next_day
        next_day += timedelta(days=1)

    # 极端情况：30天内无交易日，返回下一天
    logger.warning("30天内未找到交易日，返回下一天")
    return (date + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


def get_previous_trading_day(date: Optional[datetime] = None) -> datetime:
    """
    获取上一个交易日

    Args:
        date: 起始日期

    Returns:
        上一个交易日
    """
    if date is None:
        date = datetime.now()

    prev_day = (date - timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    for _ in range(30):
        if is_trading_day(prev_day):
            return prev_day
        prev_day -= timedelta(days=1)

    logger.warning("30天内未找到交易日")
    return (date - timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


def get_trading_days_between(start: datetime, end: datetime) -> List[datetime]:
    """
    获取两个日期之间的所有交易日

    Args:
        start: 开始日期
        end: 结束日期

    Returns:
        交易日列表
    """
    trading_days = []
    current = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end = end.replace(hour=0, minute=0, second=0, microsecond=0)

    while current <= end:
        if is_trading_day(current):
            trading_days.append(current)
        current += timedelta(days=1)

    return trading_days
