"""Private notification destination settings for ordinary Web accounts."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src import web_accounts
from src.services import web_notification_channels

router = APIRouter()


class ChannelBody(BaseModel):
    channel: str
    destination: str
    label: str = ""
    enabled: bool = True


class ScheduledTaskBody(BaseModel):
    id: int | None = None
    name: str
    schedule_time: str
    stock_codes: list[str]
    channel: str
    destination: str
    include_ai_analysis: bool = True
    include_news_summary: bool = False
    enabled: bool = True


def _user_id(request: Request) -> str:
    identity = getattr(request.state, "web_user", None)
    if not web_accounts.enabled() or identity is None:
        raise HTTPException(status_code=403, detail="请先登录后配置个人通知")
    return identity.id


@router.get("")
def list_channels(request: Request):
    return {"channels": web_notification_channels.list_channels(_user_id(request))}


@router.put("")
def save_channel(request: Request, body: ChannelBody):
    user_id = _user_id(request)
    try:
        return web_notification_channels.save_channel(
            user_id, body.channel, body.destination, body.label, body.enabled)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{channel_id}")
def delete_channel(request: Request, channel_id: int):
    user_id = _user_id(request)
    try:
        web_notification_channels.remove_channel(user_id, channel_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="通知渠道不存在") from exc
    return {"deleted": True}


@router.get("/scheduled")
def list_scheduled(request: Request):
    return {"tasks": web_notification_channels.list_scheduled_tasks(_user_id(request))}


@router.put("/scheduled")
def save_scheduled(request: Request, body: ScheduledTaskBody):
    try:
        return web_notification_channels.save_scheduled_task(
            _user_id(request),
            task_id=body.id,
            name=body.name,
            schedule_time=body.schedule_time,
            stock_codes=body.stock_codes,
            channel=body.channel,
            destination=body.destination,
            include_ai_analysis=body.include_ai_analysis,
            include_news_summary=body.include_news_summary,
            enabled=body.enabled,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/scheduled/{task_id}")
def delete_scheduled(request: Request, task_id: int):
    try:
        web_notification_channels.remove_scheduled_task(_user_id(request), task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"deleted": True}
