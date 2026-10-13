"""Account-owned notification destinations.

Secrets are encrypted at rest with a dedicated persistent key. The API only
returns a masked destination and never sends the stored value to the browser.
"""

from __future__ import annotations

import re
from email.utils import parseaddr
from urllib.parse import urlparse

from sqlalchemy import select
from cryptography.fernet import Fernet

from src import auth
from src.storage import DatabaseManager, WebNotificationChannel, WebScheduledPushTask
import json
from datetime import datetime

CHANNELS = frozenset({"email", "feishu", "dingtalk", "discord", "slack"})
WEBHOOK_HOSTS = {
    "feishu": frozenset({"open.feishu.cn", "open.larksuite.com"}),
    "dingtalk": frozenset({"oapi.dingtalk.com", "oapi.dingtalk.cn"}),
    "discord": frozenset({"discord.com", "discordapp.com"}),
    "slack": frozenset({"hooks.slack.com"}),
}


def _key() -> bytes:
    key_path = auth._get_data_dir() / ".notification_secret"
    key_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with key_path.open("xb") as handle:
            handle.write(Fernet.generate_key())
        key_path.chmod(0o600)
    except FileExistsError:
        pass
    key = key_path.read_bytes()
    Fernet(key)
    return key


def _encrypt(value: str) -> str:
    return Fernet(_key()).encrypt(value.encode("utf-8")).decode("ascii")


def _decrypt(value: str) -> str:
    return Fernet(_key()).decrypt(value.encode("ascii")).decode("utf-8")


def _scheduled_task_destination(row: WebScheduledPushTask) -> str:
    return _decrypt(row.destination_encrypted)


def _validate(channel: str, destination: str) -> str:
    channel = channel.strip().lower()
    destination = destination.strip()
    if channel not in CHANNELS:
        raise ValueError("不支持的通知渠道")
    if channel == "email":
        _, address = parseaddr(destination)
        if address != destination or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", address) or len(address) > 254:
            raise ValueError("请输入有效的邮箱地址")
    else:
        parsed = urlparse(destination)
        if (parsed.scheme != "https" or parsed.hostname not in WEBHOOK_HOSTS[channel]
                or parsed.username or parsed.password or parsed.port not in (None, 443)
                or not parsed.path or len(destination) > 2048):
            raise ValueError("请输入该渠道官方域名的 HTTPS Webhook")
    return channel


def _mask(destination: str) -> str:
    if "@" in destination:
        local, domain = destination.split("@", 1)
        return f"{(local[:2] + '***') if len(local) > 2 else '***'}@{domain}"
    parsed = urlparse(destination)
    return f"{parsed.scheme}://{parsed.hostname}/…"


def _public(row: WebNotificationChannel, destination: str | None = None) -> dict:
    return {"id": row.id, "channel": row.channel, "label": row.label,
            "destination": _mask(destination) if destination else "已配置",
            "enabled": row.enabled}


def list_channels(user_id: str) -> list[dict]:
    with DatabaseManager.get_instance().session_scope() as session:
        rows = session.scalars(select(WebNotificationChannel).where(WebNotificationChannel.user_id == user_id)
                               .order_by(WebNotificationChannel.channel)).all()
        return [_public(row, _decrypt(row.destination_encrypted)) for row in rows]


def save_channel(user_id: str, channel: str, destination: str, label: str, enabled: bool) -> dict:
    channel = _validate(channel, destination)
    label = label.strip()[:80]
    if not isinstance(enabled, bool):
        raise ValueError("启用状态无效")
    with DatabaseManager.get_instance().session_scope() as session:
        row = session.scalar(select(WebNotificationChannel).where(
            WebNotificationChannel.user_id == user_id, WebNotificationChannel.channel == channel))
        if row is None:
            row = WebNotificationChannel(user_id=user_id, channel=channel)
            session.add(row)
        row.label = label or channel
        row.destination_encrypted = _encrypt(destination)
        row.enabled = enabled
        session.flush()
        return _public(row, destination)


def remove_channel(user_id: str, channel_id: int) -> None:
    with DatabaseManager.get_instance().session_scope() as session:
        row = session.get(WebNotificationChannel, channel_id)
        if row is None or row.user_id != user_id:
            raise LookupError("通知渠道不存在")
        session.delete(row)


def _task_public(row: WebScheduledPushTask) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "schedule_time": row.schedule_time,
        "stock_codes": json.loads(row.stock_codes_json or "[]"),
        "channel": row.channel,
        "destination": "已配置",
        "include_ai_analysis": bool(row.include_ai_analysis),
        "include_news_summary": bool(row.include_news_summary),
        "enabled": bool(row.enabled),
        "last_run_at": row.last_run_at.isoformat() if row.last_run_at else None,
        "last_error": row.last_error,
    }


def list_scheduled_tasks(user_id: str) -> list[dict]:
    with DatabaseManager.get_instance().session_scope() as session:
        rows = session.scalars(
            select(WebScheduledPushTask)
            .where(WebScheduledPushTask.user_id == user_id)
            .order_by(WebScheduledPushTask.id)
        ).all()
        return [_task_public(row) for row in rows]


def save_scheduled_task(
    user_id: str,
    *,
    task_id: int | None,
    name: str,
    schedule_time: str,
    stock_codes: list[str],
    channel: str,
    destination: str,
    include_ai_analysis: bool,
    include_news_summary: bool,
    enabled: bool,
) -> dict:
    channel = _validate(channel, destination)
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", schedule_time.strip()):
        raise ValueError("时间需使用 HH:MM 格式")
    codes = [str(code).strip() for code in stock_codes if str(code).strip()]
    if not codes or len(codes) > 50:
        raise ValueError("每个任务至少选择 1 只股票，最多 50 只")
    if not include_ai_analysis and not include_news_summary:
        raise ValueError("AI 分析和新闻摘要至少选择一项")
    name = name.strip()[:80]
    if not name:
        raise ValueError("任务名称不能为空")
    with DatabaseManager.get_instance().session_scope() as session:
        row = session.get(WebScheduledPushTask, task_id) if task_id else None
        if row is not None and row.user_id != user_id:
            raise LookupError("定时任务不存在")
        if row is None:
            row = WebScheduledPushTask(user_id=user_id)
            session.add(row)
        row.name = name
        row.schedule_time = schedule_time.strip()
        row.stock_codes_json = json.dumps(codes, ensure_ascii=False)
        row.channel = channel
        row.destination_encrypted = _encrypt(destination)
        row.include_ai_analysis = include_ai_analysis
        row.include_news_summary = include_news_summary
        row.enabled = enabled
        session.flush()
        return _task_public(row)


def remove_scheduled_task(user_id: str, task_id: int) -> None:
    with DatabaseManager.get_instance().session_scope() as session:
        row = session.get(WebScheduledPushTask, task_id)
        if row is None or row.user_id != user_id:
            raise LookupError("定时任务不存在")
        session.delete(row)


def due_scheduled_tasks(now: datetime | None = None) -> list[dict]:
    """Return enabled tasks due in the current server minute.

    The scheduler calls this once per minute. ``last_run_at`` prevents a task
    from running twice when the polling loop wakes more than once in a minute.
    """
    now = now or datetime.now()
    minute = now.strftime("%H:%M")
    today = now.date()
    with DatabaseManager.get_instance().session_scope() as session:
        rows = session.scalars(
            select(WebScheduledPushTask).where(
                WebScheduledPushTask.enabled.is_(True),
                WebScheduledPushTask.schedule_time == minute,
            )
        ).all()
        result = []
        for row in rows:
            if row.last_run_at is not None and row.last_run_at.date() == today:
                continue
            result.append({
                "id": row.id,
                "user_id": row.user_id,
                "name": row.name,
                "schedule_time": row.schedule_time,
                "stock_codes": json.loads(row.stock_codes_json or "[]"),
                "channel": row.channel,
                "destination": _scheduled_task_destination(row),
                "include_ai_analysis": bool(row.include_ai_analysis),
                "include_news_summary": bool(row.include_news_summary),
            })
        return result


def mark_scheduled_task_result(task_id: int, *, error: str | None = None) -> None:
    with DatabaseManager.get_instance().session_scope() as session:
        row = session.get(WebScheduledPushTask, task_id)
        if row is not None:
            row.last_run_at = datetime.now()
            row.last_error = error
