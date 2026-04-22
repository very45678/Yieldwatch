"""定时任务调度器"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from zoneinfo import ZoneInfo

# 使用上海时区
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")

scheduler = BackgroundScheduler(timezone=SHANGHAI_TZ)


def scheduled_job():
    """定时任务：更新数据并发送通知"""
    from app.services.data_service import update_fund_data
    from app.services.notification import check_and_notify
    update_fund_data()
    check_and_notify()


def start_scheduler():
    """启动调度器"""
    # 启动时立即执行一次
    scheduled_job()

    # 交易日 9:30-15:00 每5分钟执行一次
    # 使用 cron 表达式：周一到周五，每5分钟
    scheduler.add_job(
        scheduled_job,
        CronTrigger(
            day_of_week="mon-fri",
            hour="9-14",
            minute="*/5",
            second=0,
            timezone=SHANGHAI_TZ
        ),
        id="fund_monitor",
        replace_existing=True
    )
    # 15:00 执行一次
    scheduler.add_job(
        scheduled_job,
        CronTrigger(
            day_of_week="mon-fri",
            hour=15,
            minute="0-5",
            second=0,
            timezone=SHANGHAI_TZ
        ),
        id="fund_monitor_close",
        replace_existing=True
    )
    scheduler.start()


def stop_scheduler():
    """停止调度器"""
    scheduler.shutdown()
