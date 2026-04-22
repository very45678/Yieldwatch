"""应用配置"""
import json
import os
from pydantic_settings import BaseSettings
from typing import Optional, List, ClassVar
from pathlib import Path


# 监控的基金代码
MONITORED_FUNDS: List[str] = ["511880", "511990"]

# 基金名称映射
FUND_NAMES = {
    "511880": "银华日利",
    "511990": "华宝添益",
}


class Settings(BaseSettings):
    """应用配置类"""

    # 应用配置
    app_name: str = "货币基金折价套利监控系统"
    debug: bool = False

    # 告警阈值（年化收益率）
    alert_threshold: float = 3.0  # 默认3%

    # 通知配置
    bark_url: Optional[str] = None
    serverchan_key: Optional[str] = None
    email_smtp: Optional[str] = None
    email_user: Optional[str] = None
    email_password: Optional[str] = None
    email_to: Optional[str] = None
    email_port: int = 587

    # 数据刷新间隔（秒）
    refresh_interval: int = 60

    # 运行时配置存储路径
    config_file: str = str(Path(__file__).parent.parent / "config_runtime.json")

    # 敏感配置键名列表（不持久化到文件）
    SENSITIVE_KEYS: ClassVar[frozenset] = frozenset([
        "bark_url", "serverchan_key", "email_smtp",
        "email_user", "email_password", "email_to"
    ])

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load_runtime_config()

    def _load_runtime_config(self):
        """加载运行时配置（优先级高于 .env）"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    # 运行时配置覆盖默认值（敏感信息不持久化）
                    if "alert_threshold" in config:
                        self.alert_threshold = config["alert_threshold"]
            except Exception as e:
                # 配置加载失败时记录日志
                import logging
                logging.getLogger(__name__).warning(f"加载运行时配置失败: {e}")

    def save_runtime_config(self, key: str, value):
        """保存运行时配置到文件（敏感信息不持久化）"""
        # 敏感配置只在内存中保存，不写入文件
        if key in self.SENSITIVE_KEYS:
            return

        config = {}
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception:
                pass

        config[key] = value

        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)


settings = Settings()
