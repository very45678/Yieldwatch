"""数据采集器测试"""
import pytest
from unittest.mock import patch, MagicMock
import httpx

from app.services.data_collector import (
    fetch_quote,
    fetch_nav,
    _fetch_quote_sina,
    _fetch_quote_eastmoney,
    _fetch_nav_eastmoney,
)


class TestFetchQuoteSina:
    """新浪行情获取测试"""

    @patch('app.services.data_collector.get_http_client')
    def test_successful_fetch(self, mock_get_client):
        """成功获取行情数据"""
        # 模拟响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = 'var hq_str_sh511880="银华日利,100.00,99.95,99.98,100.00,99.90,99.98,100.00,100.01,100.02,100.03,100.04,99.95,99.96,99.97,99.98,99.99,100.00,100.01,100.02,100.03,100.04,100.05,100.06,100.07,100.08,100.09,100.10,100.11,100.12,100.13";'
        mock_response.encoding = "gbk"

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = _fetch_quote_sina("511880")

        assert result is not None
        assert "bid" in result
        assert "ask" in result
        assert "price" in result
        assert "timestamp" in result

    @patch('app.services.data_collector.get_http_client')
    def test_empty_response(self, mock_get_client):
        """空响应返回None"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = 'var hq_str_sh511880="";'

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = _fetch_quote_sina("511880")
        assert result is None

    @patch('app.services.data_collector._fetch_with_retry')
    def test_http_error(self, mock_retry):
        """HTTP错误返回None"""
        mock_retry.return_value = None

        result = fetch_quote("511880")
        assert result is None

    @patch('app.services.data_collector._fetch_with_retry')
    def test_timeout_error(self, mock_retry):
        """超时错误返回None"""
        mock_retry.return_value = None

        result = fetch_quote("511880")
        assert result is None


class TestFetchQuoteEastmoney:
    """东方财富行情获取测试"""

    @patch('app.services.data_collector.get_http_client')
    def test_successful_fetch(self, mock_get_client):
        """成功获取行情数据"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "f43": 99980  # 当前价格 * 1000
            }
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = _fetch_quote_eastmoney("511880")

        assert result is not None
        assert result["price"] == 99.980

    @patch('app.services.data_collector.get_http_client')
    def test_no_data(self, mock_get_client):
        """无数据返回None"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = _fetch_quote_eastmoney("511880")
        assert result is None


class TestFetchNavEastmoney:
    """东方财富净值获取测试"""

    @patch('app.services.data_collector.get_http_client')
    def test_jsonp_response(self, mock_get_client):
        """JSONP响应解析"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = 'jsonp({"Data":[{"DWJZ":100.0,"FSRQ":"2024-03-14"}]})'

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = _fetch_nav_eastmoney("511880")

        assert result is not None
        assert result["nav"] == 100.0
        assert result["date"] == "2024-03-14"

    @patch('app.services.data_collector.get_http_client')
    def test_html_parsing_fallback(self, mock_get_client):
        """HTML解析备用方案"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '''
        <html>
        <body>
        单位净值：100.50
        净值日期：2024-03-14
        </body>
        </html>
        '''

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = _fetch_nav_eastmoney("511880")

        assert result is not None
        assert result["nav"] == 100.50
        assert result["date"] == "2024-03-14"


class TestFetchQuote:
    """行情获取主函数测试"""

    @patch('app.services.data_collector._fetch_quote_sina')
    def test_sina_priority(self, mock_sina):
        """优先使用新浪数据源"""
        mock_sina.return_value = {"bid": 99.95, "ask": 100.00}

        result = fetch_quote("511880")

        assert result == {"bid": 99.95, "ask": 100.00}

    @patch('app.services.data_collector._fetch_quote_eastmoney')
    @patch('app.services.data_collector._fetch_quote_sina')
    def test_fallback_to_eastmoney(self, mock_sina, mock_eastmoney):
        """新浪失败时使用东方财富"""
        mock_sina.return_value = None
        mock_eastmoney.return_value = {"bid": 99.95, "ask": 100.00}

        result = fetch_quote("511880")

        assert result == {"bid": 99.95, "ask": 100.00}

    @patch('app.services.data_collector._fetch_quote_eastmoney')
    @patch('app.services.data_collector._fetch_quote_sina')
    def test_all_sources_failed(self, mock_sina, mock_eastmoney):
        """所有数据源都失败时返回None"""
        mock_sina.return_value = None
        mock_eastmoney.return_value = None

        result = fetch_quote("511880")

        assert result is None


class TestFetchNav:
    """净值获取主函数测试"""

    @patch('app.services.data_collector._fetch_nav_eastmoney')
    def test_eastmoney_priority(self, mock_eastmoney):
        """优先使用东方财富数据源"""
        mock_eastmoney.return_value = {"nav": 100.0, "date": "2024-03-14"}

        result = fetch_nav("511880")

        assert result == {"nav": 100.0, "date": "2024-03-14"}

    @patch('app.services.data_collector._fetch_nav_fundf10')
    @patch('app.services.data_collector._fetch_nav_eastmoney')
    def test_fallback_to_fundf10(self, mock_eastmoney, mock_fundf10):
        """东方财富失败时使用FundF10"""
        mock_eastmoney.return_value = None
        mock_fundf10.return_value = {"nav": 100.0, "date": "2024-03-14"}

        result = fetch_nav("511880")

        assert result == {"nav": 100.0, "date": "2024-03-14"}

    @patch('app.services.data_collector._fetch_nav_fundf10')
    @patch('app.services.data_collector._fetch_nav_eastmoney')
    def test_all_sources_failed(self, mock_eastmoney, mock_fundf10):
        """所有数据源都失败时返回None"""
        mock_eastmoney.return_value = None
        mock_fundf10.return_value = None

        result = fetch_nav("511880")

        assert result is None
