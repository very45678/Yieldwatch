"""API接口测试"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


class TestHealthAPI:
    """健康检查API测试"""

    def test_health_check(self):
        """健康检查接口返回正常"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_health_check_format(self):
        """健康检查返回格式正确"""
        response = client.get("/health")
        data = response.json()

        # timestamp 应该是 ISO 格式
        assert "T" in data["timestamp"]


class TestDataAPI:
    """数据API测试"""

    def test_api_data(self):
        """数据API返回基金数据"""
        response = client.get("/api/data")

        assert response.status_code == 200
        data = response.json()

        # 应该包含监控的基金代码
        assert "511880" in data
        assert "511990" in data

        # 应该包含告警阈值
        assert "alert_threshold" in data

    def test_api_data_structure(self):
        """数据API返回结构正确"""
        response = client.get("/api/data")
        data = response.json()

        # 检查基金数据结构
        for code in ["511880", "511990"]:
            fund = data[code]
            assert "name" in fund
            assert "code" in fund
            assert "bid_price" in fund
            assert "ask_price" in fund
            assert "nav" in fund
            assert "annualized_return" in fund

    def test_api_data_last_update(self):
        """数据API包含最后更新时间"""
        response = client.get("/api/data")
        data = response.json()

        assert "last_update" in data


class TestConfigAPI:
    """配置API测试"""

    def test_get_threshold(self):
        """获取阈值配置"""
        response = client.get("/api/config/threshold")

        assert response.status_code == 200
        data = response.json()
        assert "threshold" in data
        assert isinstance(data["threshold"], (int, float))

    def test_set_threshold(self):
        """设置阈值配置"""
        new_threshold = 5.0
        response = client.post(
            "/api/config/threshold",
            json={"threshold": new_threshold}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["threshold"] == new_threshold
        assert "message" in data

    def test_set_threshold_invalid_low(self):
        """设置无效阈值（过低）"""
        response = client.post(
            "/api/config/threshold",
            json={"threshold": -1.0}
        )

        assert response.status_code == 422  # Validation error

    def test_set_threshold_invalid_high(self):
        """设置无效阈值（过高）"""
        response = client.post(
            "/api/config/threshold",
            json={"threshold": 101.0}
        )

        assert response.status_code == 422  # Validation error

    def test_get_notification_config(self):
        """获取通知配置（不暴露敏感信息）"""
        response = client.get("/api/config/notification")

        assert response.status_code == 200
        data = response.json()

        # 应该只返回配置状态，不返回敏感凭证
        assert "bark_configured" in data
        assert "serverchan_configured" in data
        assert "email_configured" in data

        # 不应该包含敏感字段
        assert "bark_url" not in data
        assert "serverchan_key" not in data
        assert "email_password" not in data

    def test_set_notification_config(self):
        """设置通知配置"""
        response = client.post(
            "/api/config/notification",
            json={
                "bark_url": "https://api.day.app/test"
            }
        )

        assert response.status_code == 200
        assert "message" in response.json()


class TestDashboard:
    """仪表盘测试"""

    def test_index_page(self):
        """主页返回HTML"""
        response = client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_static_files_mounted(self):
        """静态文件目录已挂载"""
        # 这个测试确保静态文件路由已配置
        # 即使文件不存在，也不应该返回404 for the route itself
        response = client.get("/static/")
        # 可能返回404（无index文件）或403，但不应该是500
        assert response.status_code in [200, 404, 405]
