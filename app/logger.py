"""日志配置"""
import logging
import sys
from app.config import settings


def setup_logging():
    """配置日志系统"""
    log_level = logging.DEBUG if settings.debug else logging.INFO

    # 创建格式器
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 移除已有的处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 添加标准输出处理器
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(log_level)
    stdout_handler.setFormatter(formatter)
    root_logger.addHandler(stdout_handler)

    # 设置第三方库日志级别
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)

    return root_logger


# 初始化日志
logger = setup_logging()
