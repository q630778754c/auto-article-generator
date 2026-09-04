"""告警通知双通道：企业微信机器人 + SMTP 邮件（design 2.2.7）。

仅 P0/P1 触发外发，P2 仅入控制台。
"""

from __future__ import annotations

import json
import smtplib
from email.mime.text import MIMEText
from dataclasses import dataclass

import httpx

from app.core.logging import TraceLogger, mask_sensitive

logger = TraceLogger("notify")


@dataclass
class AlertMessage:
    level: str
    source: str
    title: str
    description: str
    ref: str = ""

    def to_text(self) -> str:
        return f"[{self.level}] {self.source}: {self.title}\n{self.description}\n关联: {self.ref}"


class Notifier:
    """双通道通知器。"""

    def __init__(
        self,
        *,
        wechat_webhook: str = "",
        smtp_host: str = "",
        smtp_port: int = 465,
        smtp_user: str = "",
        smtp_password: str = "",
        smtp_to: str = "",
    ):
        self._wechat_webhook = wechat_webhook
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._smtp_user = smtp_user
        self._smtp_password = smtp_password
        self._smtp_to = smtp_to

    async def send(self, alert: AlertMessage) -> dict[str, bool]:
        """发送通知，返回各通道结果。P2 不外发。"""
        results: dict[str, bool] = {}
        if alert.level not in ("P0", "P1"):
            logger.info(f"P2告警不外发: {alert.title}")
            return results

        if self._wechat_webhook:
            results["wechat"] = await self._send_wechat(alert)
        if self._smtp_host and self._smtp_user:
            results["smtp"] = self._send_smtp(alert)
        return results

    async def _send_wechat(self, alert: AlertMessage) -> bool:
        try:
            payload = {
                "msgtype": "text",
                "text": {"content": alert.to_text()},
            }
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(self._wechat_webhook, json=payload)
                return resp.status_code == 200
        except Exception as exc:
            logger.error(f"企业微信通知失败: {exc}")
            return False

    def _send_smtp(self, alert: AlertMessage) -> bool:
        try:
            msg = MIMEText(alert.to_text(), "plain", "utf-8")
            msg["Subject"] = f"[{alert.level}] {alert.title}"
            msg["From"] = self._smtp_user
            msg["To"] = self._smtp_to

            with smtplib.SMTP_SSL(self._smtp_host, self._smtp_port) as server:
                server.login(self._smtp_user, self._smtp_password)
                server.sendmail(self._smtp_user, [self._smtp_to], msg.as_string())
            return True
        except Exception as exc:
            logger.error(f"SMTP通知失败: {exc}")
            return False