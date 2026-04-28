# 腾讯云 SCF Python 入口文件
import sys
import os

# SCF 用户代码目录（代码包解压位置）
user_dir = '/var/user'
sys.path.insert(0, user_dir)
sys.path.insert(0, os.path.join(user_dir, 'python'))
sys.path.insert(0, os.path.join(user_dir, 'python/lib/site-packages'))

# SCF 层目录（依赖包位置）
opt_dir = '/opt'
sys.path.insert(0, os.path.join(opt_dir, 'python'))
sys.path.insert(0, os.path.join(opt_dir, 'python/lib/site-packages'))

def main_handler(event, context):
    """SCF 入口函数 - 返回 ASGI 应用"""
    from app.main_web import app
    return app
