"""Account-owned scheduled analysis/news push worker."""

from __future__ import annotations

import copy
import logging
import smtplib
import threading
import time
from email.mime.text import MIMEText
from typing import Any

import requests

from src import web_accounts
from src.search_service import get_search_service
from src.services.analysis_service import AnalysisService
from src.services.web_notification_channels import (
    due_scheduled_tasks,
    mark_scheduled_task_result,
)

logger = logging.getLogger(__name__)


def _send_destination(task: dict, content: str) -> None:
    channel = task["channel"]
    destination = task["destination"]
    if channel == "email":
        from src.config import get_config

        config = copy.copy(get_config())
        config.email_receivers = [destination]
        from src.notification_sender.email_sender import EmailSender

        if not EmailSender(config).send_to_email(content, subject=f"金融分析定时推送：{task['name']}"):
            raise RuntimeError("邮件发送失败，请检查管理员 SMTP 配置")
        return

    payload: dict[str, Any]
    if channel in {"discord", "slack"}:
        payload = {"content": content}
    else:
        payload = {"msg_type": "text", "content": {"text": content}}
        if channel == "dingtalk":
            payload = {"msgtype": "markdown", "markdown": {"title": task["name"], "text": content}}
        elif channel == "feishu":
            payload = {"msg_type": "text", "content": {"text": content}}
    response = requests.post(destination, json=payload, timeout=20)
    response.raise_for_status()


def _build_content(task: dict) -> str:
    sections: list[str] = [f"# {task['name']}", f"时间：{task['schedule_time']}"]
    codes = task.get("stock_codes") or []
    for code in codes:
        if task.get("include_ai_analysis"):
            result = AnalysisService().analyze_stock(
                stock_code=code,
                report_type="brief",
                send_notification=False,
                query_source="web_scheduled_push",
            )
            if result:
                report = result.get("report") if isinstance(result, dict) else None
                report_summary = report.get("summary") if isinstance(report, dict) else None
                summary = (
                    result.get("analysis_summary")
                    or (report_summary.get("analysis_summary") if isinstance(report_summary, dict) else None)
                    or "暂无分析摘要"
                )
                sections.append(f"## {code} AI 分析\n{summary}")
            else:
                sections.append(f"## {code} AI 分析\n分析失败，请稍后重试。")
        if task.get("include_news_summary"):
            search = get_search_service().search_stock_news(code, code, max_results=5)
            news = getattr(search, "results", None) or []
            lines = [f"- {getattr(item, 'title', '')}" for item in news if getattr(item, "title", "")]
            sections.append(f"## {code} 新闻摘要\n" + ("\n".join(lines) if lines else "暂无相关新闻。"))
    return "\n\n".join(sections)


def run_due_tasks() -> int:
    if not web_accounts.enabled():
        return 0
    processed = 0
    for task in due_scheduled_tasks():
        error = None
        try:
            _send_destination(task, _build_content(task))
        except Exception as exc:  # scheduled jobs must not stop the worker
            error = str(exc)
            logger.exception("Web scheduled push failed for task %s", task.get("id"))
        finally:
            mark_scheduled_task_result(task["id"], error=error)
            processed += 1
    return processed


class WebScheduledPushWorker:
    """Small independent polling worker for account-owned tasks."""

    def __init__(self, interval_seconds: int = 30) -> None:
        self.interval_seconds = max(10, interval_seconds)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="web-scheduled-push", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
        self._thread = None

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                run_due_tasks()
            except Exception:
                logger.exception("Web scheduled push polling failed")
            self._stop.wait(self.interval_seconds)
