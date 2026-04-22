"""交易日历测试"""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from app.services.trading_calendar import (
    is_trading_day,
    is_trading_time,
    is_holiday,
    get_next_trading_day,
    get_previous_trading_day,
    get_trading_days_between,
    CHINESE_CALENDAR_AVAILABLE,
)


class TestIsTradingDay:
    """交易日判断测试"""

    def test_saturday_not_trading_day(self):
        """周六不是交易日"""
        saturday = datetime(2024, 3, 16)
        assert is_trading_day(saturday) is False

    def test_sunday_not_trading_day(self):
        """周日不是交易日"""
        sunday = datetime(2024, 3, 17)
        assert is_trading_day(sunday) is False

    def test_monday_is_trading_day(self):
        """周一（非节假日）是交易日"""
        monday = datetime(2024, 3, 18)
        assert is_trading_day(monday) is True

    def test_friday_is_trading_day(self):
        """周五（非节假日）是交易日"""
        friday = datetime(2024, 3, 15)
        assert is_trading_day(friday) is True

    def test_default_to_today(self):
        """默认使用今天"""
        result = is_trading_day()
        assert isinstance(result, bool)

    @pytest.mark.skipif(
        not CHINESE_CALENDAR_AVAILABLE,
        reason="chinese_calendar 库未安装"
    )
    def test_spring_festival_not_trading_day(self):
        """春节假期不是交易日"""
        # 2024年春节：2月10-17日
        spring_festival_day = datetime(2024, 2, 12)
        assert is_trading_day(spring_festival_day) is False

    @pytest.mark.skipif(
        not CHINESE_CALENDAR_AVAILABLE,
        reason="chinese_calendar 库未安装"
    )
    def test_national_day_not_trading_day(self):
        """国庆假期不是交易日"""
        national_day = datetime(2024, 10, 3)
        assert is_trading_day(national_day) is False

    @pytest.mark.skipif(
        not CHINESE_CALENDAR_AVAILABLE,
        reason="chinese_calendar 库未安装"
    )
    def test_makeup_workday_is_trading_day(self):
        """调休工作日是交易日"""
        # 2024年4月7日（周日）调休上班
        makeup_day = datetime(2024, 4, 7)
        assert is_trading_day(makeup_day) is True


class TestIsHoliday:
    """节假日判断测试"""

    def test_weekend_is_holiday(self):
        """周末是假期（基础判断）"""
        saturday = datetime(2024, 3, 16)
        assert is_holiday(saturday) is True

    @pytest.mark.skipif(
        not CHINESE_CALENDAR_AVAILABLE,
        reason="chinese_calendar 库未安装"
    )
    def test_spring_festival_2024(self):
        """2024年春节是节假日"""
        spring_festival_day = datetime(2024, 2, 12)
        assert is_holiday(spring_festival_day) is True

    @pytest.mark.skipif(
        not CHINESE_CALENDAR_AVAILABLE,
        reason="chinese_calendar 库未安装"
    )
    def test_spring_festival_2025(self):
        """2025年春节是节假日"""
        spring_festival_day = datetime(2025, 1, 30)
        assert is_holiday(spring_festival_day) is True

    def test_regular_day_not_holiday(self):
        """普通工作日不是节假日"""
        regular_day = datetime(2024, 3, 15)
        assert is_holiday(regular_day) is False

    @pytest.mark.skipif(
        not CHINESE_CALENDAR_AVAILABLE,
        reason="chinese_calendar 库未安装"
    )
    def test_national_day_2024(self):
        """2024年国庆是节假日"""
        national_day = datetime(2024, 10, 3)
        assert is_holiday(national_day) is True


class TestIsTradingTime:
    """交易时间判断测试"""

    def test_morning_trading_time(self):
        """上午交易时间"""
        dt = datetime(2024, 3, 15, 10, 30)
        assert is_trading_time(dt) is True

    def test_afternoon_trading_time(self):
        """下午交易时间"""
        dt = datetime(2024, 3, 15, 14, 30)
        assert is_trading_time(dt) is True

    def test_just_at_open_time(self):
        """开盘时间（9:30）"""
        dt = datetime(2024, 3, 15, 9, 30)
        assert is_trading_time(dt) is True

    def test_just_at_close_time(self):
        """收盘时间（15:00）"""
        dt = datetime(2024, 3, 15, 15, 0)
        assert is_trading_time(dt) is True

    def test_before_open_time(self):
        """开盘前不是交易时间"""
        dt = datetime(2024, 3, 15, 9, 0)
        assert is_trading_time(dt) is False

    def test_after_close_time(self):
        """收盘后不是交易时间"""
        dt = datetime(2024, 3, 15, 15, 30)
        assert is_trading_time(dt) is False

    def test_weekend_not_trading_time(self):
        """周末不是交易时间"""
        saturday = datetime(2024, 3, 16, 10, 30)
        assert is_trading_time(saturday) is False

    @pytest.mark.skipif(
        not CHINESE_CALENDAR_AVAILABLE,
        reason="chinese_calendar 库未安装"
    )
    def test_holiday_not_trading_time(self):
        """节假日不是交易时间"""
        spring_festival = datetime(2024, 2, 12, 10, 30)
        assert is_trading_time(spring_festival) is False


class TestGetNextTradingDay:
    """下一个交易日测试"""

    def test_from_friday(self):
        """周五的下一个交易日是周一"""
        friday = datetime(2024, 3, 15)
        next_day = get_next_trading_day(friday)

        assert next_day.weekday() == 0
        assert next_day > friday

    def test_from_monday(self):
        """周一的下一个交易日是周二"""
        monday = datetime(2024, 3, 18)
        next_day = get_next_trading_day(monday)

        assert next_day.weekday() == 1

    def test_default_to_now(self):
        """默认使用当前时间"""
        result = get_next_trading_day()
        assert isinstance(result, datetime)

    @pytest.mark.skipif(
        not CHINESE_CALENDAR_AVAILABLE,
        reason="chinese_calendar 库未安装"
    )
    def test_from_before_holiday(self):
        """节假日前一天的下一个交易日是节后首日"""
        # 2024年春节：2月10-17日
        day_before_holiday = datetime(2024, 2, 9)
        next_day = get_next_trading_day(day_before_holiday)

        # 应该跳过春节假期
        assert next_day >= datetime(2024, 2, 18)


class TestGetPreviousTradingDay:
    """上一个交易日测试"""

    def test_from_monday(self):
        """周一的上一个交易日是周五"""
        monday = datetime(2024, 3, 18)
        prev_day = get_previous_trading_day(monday)

        assert prev_day.weekday() == 4
        assert prev_day < monday

    def test_from_tuesday(self):
        """周二的上一个交易日是周一"""
        tuesday = datetime(2024, 3, 19)
        prev_day = get_previous_trading_day(tuesday)

        assert prev_day.weekday() == 0

    def test_default_to_now(self):
        """默认使用当前时间"""
        result = get_previous_trading_day()
        assert isinstance(result, datetime)


class TestGetTradingDaysBetween:
    """交易日区间测试"""

    def test_one_week(self):
        """一周内的交易日"""
        start = datetime(2024, 3, 18)  # 周一
        end = datetime(2024, 3, 22)    # 周五

        trading_days = get_trading_days_between(start, end)

        # 应该有5个交易日
        assert len(trading_days) == 5

    def test_including_weekend(self):
        """包含周末的日期范围"""
        start = datetime(2024, 3, 15)  # 周五
        end = datetime(2024, 3, 18)    # 下周一

        trading_days = get_trading_days_between(start, end)

        # 只有周五和周一
        assert len(trading_days) == 2

    def test_same_day(self):
        """同一天"""
        day = datetime(2024, 3, 18)

        trading_days = get_trading_days_between(day, day)

        assert len(trading_days) == 1

    def test_start_after_end(self):
        """开始日期晚于结束日期"""
        start = datetime(2024, 3, 22)  # 周五
        end = datetime(2024, 3, 18)    # 周一

        trading_days = get_trading_days_between(start, end)

        # 应该返回空列表
        assert len(trading_days) == 0
