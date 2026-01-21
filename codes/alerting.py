from __future__ import annotations

import json
import logging
import os
import re
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


def send_dingtalk(text: str, webhook: str, secret: str | None = None) -> None:
    """发送钉钉告警消息
    
    Args:
        text: 告警文本内容
        webhook: 钉钉机器人 webhook URL
        secret: 钉钉机器人加签密钥（可选，当前不加签）
    
    注意：当前版本不使用加签功能（secret 参数保留但不使用）
    """
    if secret:
        logger.warning("DingTalk secret signing is not supported in current version, ignoring secret parameter")
    
    payload = {
        "msgtype": "text",
        "text": {
            "content": text
        }
    }
    
    data = json.dumps(payload).encode("utf-8")
    req = Request(
        webhook,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    
    with urlopen(req, timeout=10) as response:
        result = response.read().decode("utf-8")
        logger.info(f"DingTalk notification sent successfully: {result}")


def send_email(
    subject: str,
    body: str,
    smtp_host: str,
    smtp_port: int,
    username: str,
    password: str,
    to_addrs: list[str],
    from_addr: str | None = None
) -> None:
    """发送邮件告警
    
    Args:
        subject: 邮件主题
        body: 邮件正文
        smtp_host: SMTP 服务器地址
        smtp_port: SMTP 端口（465 for SSL, 587 for STARTTLS）
        username: SMTP 用户名
        password: SMTP 密码（QQ 邮箱使用授权码）
        to_addrs: 收件人列表
        from_addr: 发件人地址（可选，默认使用 username）
    
    支持 QQ 邮箱的 465 端口（SSL）和 587 端口（STARTTLS）
    """
    if not from_addr:
        from_addr = username
    
    # 创建邮件
    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)
    msg["Subject"] = subject
    
    # 添加邮件正文
    msg.attach(MIMEText(body, "plain", "utf-8"))
    
    # 根据端口选择连接方式
    if smtp_port == 465:
        # SSL 连接（QQ 邮箱推荐）
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=10) as server:
            server.login(username, password)
            server.sendmail(from_addr, to_addrs, msg.as_string())
            logger.info(f"Email sent successfully via SSL to {to_addrs}")
    elif smtp_port == 587:
        # STARTTLS 连接
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(username, password)
            server.sendmail(from_addr, to_addrs, msg.as_string())
            logger.info(f"Email sent successfully via STARTTLS to {to_addrs}")
    else:
        # 尝试不加密连接（不推荐）
        logger.warning(f"Using non-standard port {smtp_port}, attempting plain SMTP connection")
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.login(username, password)
            server.sendmail(from_addr, to_addrs, msg.as_string())
            logger.info(f"Email sent successfully to {to_addrs}")


def _sanitize_dict(data: dict[str, Any]) -> dict[str, Any]:
    """脱敏字典中的敏感信息
    
    将包含 key、secret、password、token 等关键字的字段值替换为 ***
    
    Args:
        data: 需要脱敏的字典
        
    Returns:
        脱敏后的字典副本
    """
    sensitive_patterns = [
        r"key",
        r"secret",
        r"password",
        r"token",
        r"passwd",
        r"pwd",
        r"credential"
    ]
    pattern = re.compile("|".join(sensitive_patterns), re.IGNORECASE)
    
    sanitized = {}
    for key, value in data.items():
        if pattern.search(key):
            sanitized[key] = "***"
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_dict(value)
        elif isinstance(value, str) and len(value) > 50:
            # 长字符串可能包含敏感信息，截断显示
            sanitized[key] = value[:50] + "..."
        else:
            sanitized[key] = value
    
    return sanitized


def notify_failure(context_dict: dict[str, Any]) -> None:
    """发送失败告警通知
    
    根据环境变量配置，发送钉钉和/或邮件告警。
    本函数内部捕获所有异常，不会影响主流程。
    
    Args:
        context_dict: 告警上下文信息（包含 keyword、error、run_id 等）
    
    环境变量：
        DINGTALK_WEBHOOK_URL: 钉钉 webhook URL（必需）
        DINGTALK_SECRET: 钉钉加签密钥（可选，当前不使用）
        SMTP_HOST: SMTP 服务器地址
        SMTP_PORT: SMTP 端口
        SMTP_USERNAME: SMTP 用户名
        SMTP_PASSWORD: SMTP 密码
        SMTP_TO: 收件人列表（逗号分隔）
        SMTP_FROM: 发件人地址（可选，默认使用 username）
    """
    try:
        # 脱敏处理
        sanitized_context = _sanitize_dict(context_dict)
        
        # 构造告警消息
        keyword = sanitized_context.get("keyword", "未知")
        error = sanitized_context.get("error", "未知错误")
        run_id = sanitized_context.get("run_id", "N/A")
        
        alert_text = f"""【Radar 采集失败告警】
关键词: {keyword}
运行ID: {run_id}
错误信息: {error}
详细上下文: {json.dumps(sanitized_context, ensure_ascii=False, indent=2)}
"""
        
        # 发送钉钉告警
        dingtalk_webhook = os.getenv("DINGTALK_WEBHOOK_URL")
        if dingtalk_webhook:
            try:
                dingtalk_secret = os.getenv("DINGTALK_SECRET")
                send_dingtalk(alert_text, dingtalk_webhook, dingtalk_secret)
                logger.info("DingTalk alert sent successfully")
            except Exception as e:
                logger.error(f"Failed to send DingTalk alert: {e}", exc_info=True)
        else:
            logger.debug("DINGTALK_WEBHOOK_URL not configured, skipping DingTalk notification")
        
        # 发送邮件告警
        smtp_host = os.getenv("SMTP_HOST")
        smtp_port_str = os.getenv("SMTP_PORT")
        smtp_username = os.getenv("SMTP_USERNAME")
        smtp_password = os.getenv("SMTP_PASSWORD")
        smtp_to = os.getenv("SMTP_TO")
        
        if all([smtp_host, smtp_port_str, smtp_username, smtp_password, smtp_to]):
            try:
                smtp_port = int(smtp_port_str)
                smtp_from = os.getenv("SMTP_FROM", smtp_username)
                to_addrs = [addr.strip() for addr in smtp_to.split(",")]
                
                subject = f"[Radar 告警] {keyword} 采集失败"
                send_email(
                    subject=subject,
                    body=alert_text,
                    smtp_host=smtp_host,
                    smtp_port=smtp_port,
                    username=smtp_username,
                    password=smtp_password,
                    to_addrs=to_addrs,
                    from_addr=smtp_from
                )
                logger.info("Email alert sent successfully")
            except Exception as e:
                logger.error(f"Failed to send email alert: {e}", exc_info=True)
        else:
            missing = []
            if not smtp_host:
                missing.append("SMTP_HOST")
            if not smtp_port_str:
                missing.append("SMTP_PORT")
            if not smtp_username:
                missing.append("SMTP_USERNAME")
            if not smtp_password:
                missing.append("SMTP_PASSWORD")
            if not smtp_to:
                missing.append("SMTP_TO")
            logger.debug(f"Email configuration incomplete (missing: {', '.join(missing)}), skipping email notification")
    
    except Exception as e:
        # 确保告警逻辑本身的异常不会影响主流程
        logger.error(f"Critical error in notify_failure: {e}", exc_info=True)
