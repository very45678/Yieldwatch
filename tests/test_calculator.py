"""年化收益率计算器测试"""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from app.services.calculator import (
    calculate_annualized_return,
    calculate_holding_days,
    ANNUAL_RATE
)


class TestCalculateAnnualizedReturn:
    """年化收益率计算测试"""

    def test_basic_calculation_with_discount(self):
        """折价情况下的基本计算测试"""
        # 卖1价格低于净值，存在折价
        result = calculate_annualized_return(
            ask_price=99.50,
            nav=100.0,
            nav_date="2024-03-14"
        )

        assert result["estimated_nav"] is not None
        assert result["annualized_return"] is not None
        assert result["holding_days"] is not None
        # 折价时应为正收益
        assert result["annualized_return"] > 0

    def test_missing_ask_price(self):
        """缺失卖1价格时返回None"""
        result = calculate_annualized_return(
            ask_price=None,
            nav=100.0,
            nav_date="2024-03-14"
        )

        assert result["estimated_nav"] is None
        assert result["annualized_return"] is None
        assert result["holding_days"] is None

    def test_missing_nav(self):
        """缺失净值时返回None"""
        result = calculate_annualized_return(
            ask_price=99.50,
            nav=None,
            nav_date="2024-03-14"
        )

        assert result["estimated_nav"] is None
        assert result["annualized_return"] is None
        assert result["holding_days"] is None

    def test_zero_price(self):
        """零价格时返回None"""
        result = calculate_annualized_return(
            ask_price=0,
            nav=100.0,
            nav_date="2024-03-14"
        )

        assert result["annualized_return"] is None

    def test_invalid_date_format(self):
        """无效日期格式时使用默认天数1"""
        result = calculate_annualized_return(
            ask_price=99.50,
            nav=100.0,
            nav_date="invalid-date"
        )

        # 应该使用默认1天而不是报错
        assert result["holding_days"] is not None
        assert result["holding_days"] >= 1

    def test_missing_date_uses_default(self):
        """缺失日期时使用默认天数1"""
        result = calculate_annualized_return(
            ask_price=99.50,
            nav=100.0,
            nav_date=None
        )

        assert result["holding_days"] is not None
        assert result["holding_days"] >= 1

    def test_future_nav_date(self):
        """未来净值日期时使用最小天数1"""
        result = calculate_annualized_return(
            ask_price=99.50,
            nav=100.0,
            nav_date="2030-01-01"  # 未来日期
        )

        assert result["holding_days"] >= 1

    def test_estimated_nav_calculation(self):
        """估算净值计算正确性"""
        nav = 100.0
        nav_date = datetime.now().strftime("%Y-%m-%d")

        result = calculate_annualized_return(
            ask_price=99.50,
            nav=nav,
            nav_date=nav_date
        )

        # 估算净值应该略高于原始净值（累加了每日收益）
        # 当天净值日期时，days=1，估算净值 = nav * (1 + 0.01/365 * 1)
        expected = nav * (1 + ANNUAL_RATE / 365 * 1)
        assert abs(result["estimated_nav"] - expected) < 0.0001

    def test_result_precision(self):
        """结果精度测试"""
        result = calculate_annualized_return(
            ask_price=99.50,
            nav=100.0,
            nav_date="2024-03-14"
        )

        # 估算净值保留4位小数
        assert result["estimated_nav"] == round(result["estimated_nav"], 4)
        # 年化收益率保留2位小数
        assert result["annualized_return"] == round(result["annualized_return"], 2)

    def test_return_calculation_logic(self):
        """测试收益率计算逻辑"""
        # 使用一个具体场景验证计算
        ask_price = 99.50
        nav = 100.0
        nav_date = datetime.now().strftime("%Y-%m-%d")

        result = calculate_annualized_return(ask_price, nav, nav_date)

        # 验证：折价买入应该有正收益
        # estimated_nav = 100.0 * (1 + 0.01/365) ≈ 100.0027
        # discount_rate = (100.0027 - 99.50) / 100.0027 ≈ 0.50%
        # annualized_return 应该是正数
        assert result["annualized_return"] > 0


class TestCalculateHoldingDays:
    """占用天数计算测试"""

    @patch('app.services.calculator.datetime')
    @patch('app.services.trading_calendar.get_next_trading_day')
    def test_minimum_one_day(self, mock_next_day, mock_datetime):
        """占用天数最少为1天"""
        # 设置当前时间
        now = datetime(2024, 3, 15, 10, 0)
        mock_datetime.now.return_value = now

        # 下一个交易日为明天
        mock_next_day.return_value = datetime(2024, 3, 18)  # 周一

        from app.services.calculator import calculate_holding_days

        result = calculate_holding_days()
        assert result >= 1

    def test_holding_days_positive(self):
        """占用天数为正数"""
        from app.services.calculator import calculate_holding_days

        result = calculate_holding_days()
        assert result >= 1
