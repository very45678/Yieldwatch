"""测试配置"""
import pytest
from datetime import datetime


@pytest.fixture
def mock_today():
    """固定当前日期为周五"""
    return datetime(2024, 3, 15)


@pytest.fixture
def mock_trading_time():
    """固定当前时间为交易时间"""
    return datetime(2024, 3, 15, 10, 30)


@pytest.fixture
def mock_non_trading_time():
    """固定当前时间为非交易时间"""
    return datetime(2024, 3, 15, 16, 0)
