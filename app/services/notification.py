"""通知服务"""
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.config import settings, MONITORED_FUNDS
from app.services.data_service import get_fund_data
from app.services.trading_calendar import is_trading_time
from app.services.http_client import get_http_client

logger = logging.getLogger(__name__)


def check_and_notify():
    """检查并发送通知"""
    if not is_trading_time():
        logger.debug("当前非交易时间，跳过通知")
        return

    fund_data = get_fund_data()
    alerts = []
    for code in MONITORED_FUNDS:
        data = fund_data.get(code, {})
        annualized_return = data.get("annualized_return")
        threshold = settings.alert_threshold

        if annualized_return is not None and annualized_return >= threshold:
            logger.info(f"{data.get('name')} 年化收益率 {annualized_return:.2f}% 超过阈值 {threshold}%")
            alerts.append({
                "name": data.get("name"),
                "code": code,
                "annualized_return": annualized_return,
                "threshold": threshold,
                "ask_price": data.get("ask_price"),
                "estimated_nav": data.get("estimated_nav"),
                "holding_days": data.get("holding_days"),
            })

    if alerts:
        logger.info(f"发现 {len(alerts)} 个套利机会，发送通知")
        send_notification(alerts)
    else:
        logger.debug("当前无套利机会")


def send_notification(alerts: List[Dict[str, Any]]):
    """发送通知到所有配置的渠道"""
    message = format_alert_message(alerts)

    # 微信推送 - Bark
    if settings.bark_url:
        send_bark_notification(message)

    # 微信推送 - Server酱
    if settings.serverchan_key:
        send_serverchan_notification(message)

    # 邮件通知
    if settings.email_smtp and settings.email_user and settings.email_to:
        send_email_notification(message)


def format_alert_message(alerts: List[Dict[str, Any]]) -> str:
    """格式化告警消息"""
    lines = ["【套利机会提醒】", ""]
    for alert in alerts:
        lines.append(f"基金: {alert['name']} ({alert['code']})")
        lines.append(f"年化收益率: {alert['annualized_return']:.2f}%")
        lines.append(f"阈值: {alert['threshold']:.2f}%")
        lines.append(f"卖1价格: {alert['ask_price']:.4f}")
        lines.append(f"估算净值: {alert['estimated_nav']:.4f}")
        lines.append(f"占用天数: {alert['holding_days']}天")
        lines.append("-" * 30)
    lines.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return "\n".join(lines)


def send_bark_notification(message: str):
    """发送 Bark 通知"""
    import urllib.parse

    try:
        title = urllib.parse.quote("套利机会提醒")
        body = urllib.parse.quote(message)
        url = f"{settings.bark_url.rstrip('/')}/{title}/{body}"
        client = get_http_client()
        resp = client.get(url)
        if resp.status_code == 200:
            logger.info("Bark 通知发送成功")
        else:
            logger.warning(f"Bark 通知发送失败: {resp.status_code}")
    except Exception as e:
        logger.error(f"Bark 通知发送异常: {e}")


def send_serverchan_notification(message: str):
    """发送 Server酱 通知"""
    try:
        url = f"https://sctapi.ftqq.com/{settings.serverchan_key}.send"
        client = get_http_client()
        resp = client.post(url, data={
            "title": "套利机会提醒",
            "desp": message
        })
        if resp.status_code == 200:
            result = resp.json()
            if result.get("code") == 0:
                logger.info("Server酱 通知发送成功")
            else:
                logger.warning(f"Server酱 通知发送失败: {result.get('message')}")
        else:
            logger.warning(f"Server酱 通知发送失败: {resp.status_code}")
    except Exception as e:
        logger.error(f"Server酱 通知发送异常: {e}")


def send_email_notification(message: str):
    """发送邮件通知"""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    try:
        msg = MIMEMultipart()
        msg["From"] = settings.email_user
        msg["To"] = settings.email_to
        msg["Subject"] = "套利机会提醒"
        msg.attach(MIMEText(message, "plain", "utf-8"))

        with smtplib.SMTP(settings.email_smtp, settings.email_port) as server:
            server.starttls()
            server.login(settings.email_user, settings.email_password)
            server.sendmail(settings.email_user, settings.email_to, msg.as_string())
        logger.info("邮件通知发送成功")
    except Exception as e:
        logger.error(f"邮件通知发送异常: {e}")
