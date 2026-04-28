"""腾讯云 SCF 定时函数入口"""
import sys
import os
import json
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# /opt 路径在 SCF 运行时由 Layer 挂载，本地开发时忽略
for p in ["/opt", "/opt/python"]:
    if p not in sys.path:
        sys.path.insert(0, p)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def main_handler(event, context):
    """腾讯云 SCF 定时触发器入口"""
    from app.services.trading_calendar import is_trading_day, is_trading_time

    if not is_trading_day():
        logger.info("今日非交易日，跳过执行")
        return {"statusCode": 200, "body": json.dumps({"message": "非交易日"})}

    if not is_trading_time():
        logger.info("当前非交易时段，跳过执行")
        return {"statusCode": 200, "body": json.dumps({"message": "非交易时段"})}

    try:
        from app.services.data_service import update_fund_data
        from app.services.notification import check_and_notify
        from app.services.http_client import close_http_client

        logger.info("开始执行定时任务：更新基金数据")
        update_fund_data()
        logger.info("基金数据更新完成")

        logger.info("开始检查套利机会并发送通知")
        check_and_notify()
        logger.info("通知检查完成")

        close_http_client()
        return {"statusCode": 200, "body": json.dumps({"message": "执行成功"})}

    except Exception as e:
        logger.error(f"定时任务执行失败: {e}", exc_info=True)
        try:
            from app.services.http_client import close_http_client
            close_http_client()
        except Exception:
            pass
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
