"""
推送通知工具 - 企业微信/钉钉 Webhook
"""
import hashlib
import hmac
import base64
import time
import urllib.parse
from typing import Optional

import requests
from langchain_core.tools import tool


@tool
def send_wechat_webhook(webhook_url: str, message: str) -> bool:
    """通过企业微信 Webhook 发送 Markdown 消息。

    Args:
        webhook_url: 企业微信机器人 Webhook 地址
        message: Markdown 格式的消息内容

    Returns:
        是否发送成功
    """
    if not webhook_url:
        print("[notification] 企业微信 Webhook URL 未配置，跳过推送")
        return False

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "content": message
        }
    }
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        result = resp.json()
        if result.get('errcode') == 0:
            print("[notification] 企业微信推送成功")
            return True
        else:
            print(f"[notification] 企业微信推送失败: {result}")
            return False
    except Exception as e:
        print(f"[notification] 企业微信推送异常: {e}")
        return False


@tool
def send_dingtalk_webhook(webhook_url: str, message: str,
                          secret: Optional[str] = None, title: str = "ETF策略分析") -> bool:
    """通过钉钉 Webhook 发送 Markdown 消息。

    Args:
        webhook_url: 钉钉机器人 Webhook 地址
        message: Markdown 格式的消息内容
        secret: 钉钉机器人签名密钥（可选）
        title: 消息标题

    Returns:
        是否发送成功
    """
    if not webhook_url:
        print("[notification] 钉钉 Webhook URL 未配置，跳过推送")
        return False

    # 签名处理
    url = webhook_url
    if secret:
        timestamp = str(round(time.time() * 1000))
        string_to_sign = f'{timestamp}\n{secret}'
        hmac_code = hmac.new(secret.encode('utf-8'),
                             string_to_sign.encode('utf-8'),
                             digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": message
        }
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        result = resp.json()
        if result.get('errcode') == 0:
            print("[notification] 钉钉推送成功")
            return True
        else:
            print(f"[notification] 钉钉推送失败: {result}")
            return False
    except Exception as e:
        print(f"[notification] 钉钉推送异常: {e}")
        return False


def get_notification_tools():
    """返回所有通知工具列表"""
    return [send_wechat_webhook, send_dingtalk_webhook]
