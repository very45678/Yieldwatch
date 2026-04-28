"""阿里云函数计算入口"""
import sys
import os

# 将 /code 目录添加到 Python 路径，确保能找到 pip 安装的依赖
sys.path.insert(0, '/code')
sys.path.insert(0, '/code/python/lib/site-packages')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 创建 ASGI 应用实例（全局，避免重复创建）
from app.main import app as asgi_app

def handler(event, context):
    """
    阿里云事件函数入口
    对于 HTTP 函数，使用 asgi 处理
    """
    return asgi_app
