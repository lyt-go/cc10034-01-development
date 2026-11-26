"""样本预览 / 批次确认 / 分级分类放行下载接口。

为兼容不同调用习惯，同一组能力同时挂在 ``/api/mask_rule/previews`` 与
``/api/mask-previews`` 等路径下；业务判断全部在 mask_preview 服务中完成。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse, StreamingResponse

from app.schemas import ActionResult
from app.services.mask_preview import (
    bootstrap_scenario_rules,
    preview_service,
    publish_version,
)
from app.store import store

router = APIRouter(prefix="/api", tags=["样本预览与放行"])


def _as_ticket_id(value: str) -> int | None:
    if value in ("active", "latest", "current"):
        ticket = preview_service.active_ticket()
        return int(ticket["id"]) if ticket else None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# —— 创建 / 列出预览单 ——
@router.post("/mask_rule/previews", response_model=ActionResult)
@router.post("/mask_rule/preview", response_model=ActionResult)
@router.post("/mask-previews", response_model=ActionResult)
@router.post("/mask_preview", response_model=ActionResult)
@router.post("/previews", response_model=ActionResult)
def create_preview(payload: dict[str, Any] = Body(default_factory=dict)) -> ActionResult:
    ticket, missing = preview_service.create_preview(payload)
    if ticket is None:
        return ActionResult(ok=False, message="；".join(missing) or "预览生成失败")
    message = (
        f"已按规则版本 {ticket.get('rule_version') or '解析版本'} 生成 "
        f"{ticket.get('batch_no')}：{ticket.get('column_count')} 列 × "
        f"{ticket.get('row_count')} 行，"
        + ("全部字段处理通过" if ticket.get("all_passed") else "存在字段处理失败，必需字段失败时不能放行或下载")
    )
    return ActionResult(ok=True, message=message, entry=ticket)


@router.get("/mask_rule/previews")
@router.get("/mask_rule/preview")
@router.get("/mask-previews")
@router.get("/mask_preview/list")
@router.get("/previews")
def list_previews() -> dict[str, Any]:
    items = preview_service.list_tickets()
    active = preview_service.active_ticket()
    return {"items": items, "total": len(items), "active_id": active.get("id") if active else None}


@router.get("/mask_rule/previews/active")
@router.get("/mask-previews/active")
def active_preview() -> dict[str, Any]:
    ticket = preview_service.active_ticket()
    return {"ok": ticket is not None, "ticket": ticket, "active_id": ticket.get("id") if ticket else None}


# —— 分级分类放行闸门（固定路径必须在 {ticket_id} 之前注册） ——
@router.get("/classify_tag/release")
@router.get("/classify_tag/gate")
@router.get("/release-ticket")
def classify_release_state() -> dict[str, Any]:
    return preview_service.classify_gate()


@router.post("/classify_tag/release/confirm", response_model=ActionResult)
@router.post("/classify_tag/release")
def classify_release_confirm(payload: dict[str, Any] = Body(default_factory=dict)) -> ActionResult:
    ticket_id = payload.get("ticket_id") or payload.get("id")
    if ticket_id is not None:
        ticket, message = preview_service.activate(int(ticket_id))
        if ticket is None:
            return ActionResult(ok=False, message=message)

    gate = preview_service.classify_gate()
    if not gate.get("has_ticket"):
        return ActionResult(ok=False, message="还没有脱敏预览单，无法据此确认分级与开放下载")
    if not gate.get("can_confirm"):
        return ActionResult(ok=False, message=gate.get("message") or "预览批次未满足放行条件")

    entry_id = payload.get("entry_id") or payload.get("classify_entry_id")
    if entry_id is None:
        rows = store.rows("classify_tag")
        pending = next((row for row in rows if row.get("status") == "待分级"), rows[0] if rows else None)
        entry_id = pending.get("id") if pending else None

    from app.services.classify_tag import ClassifyTagService

    entry, message = ClassifyTagService().run_action(int(entry_id), "确认分级") if entry_id is not None else (None, "缺少分级标签对象")
    return ActionResult(ok=entry is not None, message=message, entry=entry)


@router.get("/classify_tag/release/download")
@router.get("/classify_tag/delivery")
def classify_release_download(ticket_id: str | None = None) -> Any:
    target_id = ticket_id
    if target_id is None:
        ticket = preview_service.active_ticket()
        target = ticket
    else:
        resolved = _as_ticket_id(str(target_id))
        target = preview_service.get_ticket(resolved) if resolved is not None else None
    if target is None:
        return JSONResponse(status_code=404, content={"ok": False, "message": "没有可下载的预览批次"})
    return _download_ticket(int(target["id"]))


# —— 演练规则补齐 / 版本发布 ——
@router.post("/mask_rule/scenario/bootstrap")
@router.post("/mask-rules/bootstrap-scenario")
def bootstrap_scenario() -> dict[str, Any]:
    result = bootstrap_scenario_rules()
    return {"ok": True, "message": f"已补齐 {result['created']} 条演练规则", **result}


@router.post("/mask_rule/versions/publish", response_model=ActionResult)
@router.post("/mask-rules/publish-version", response_model=ActionResult)
def publish_rule_version(payload: dict[str, Any] = Body(default_factory=dict)) -> ActionResult:
    version = str(payload.get("version") or payload.get("rule_version") or payload.get("规则版本") or "").strip()
    if not version:
        return ActionResult(ok=False, message="缺少要发布的规则版本")
    updated, message = publish_version(version)
    return ActionResult(ok=True, message=message, entry={"updated": len(updated), "rules": updated})


# —— 预览单详情 / 确认 / 激活 / 下载（动态 id 路由放最后） ——
@router.get("/mask_rule/previews/{ticket_id}")
@router.get("/mask-previews/{ticket_id}")
@router.get("/previews/{ticket_id}")
def get_preview(ticket_id: str) -> dict[str, Any]:
    resolved = _as_ticket_id(ticket_id)
    ticket = preview_service.get_ticket(resolved) if resolved is not None else None
    if ticket is None:
        return JSONResponse(status_code=404, content={"ok": False, "message": f"预览单 {ticket_id} 不存在"})
    return {"ok": True, "ticket": ticket, "entry": ticket}


@router.post("/mask_rule/previews/{ticket_id}/confirm", response_model=ActionResult)
@router.post("/mask-previews/{ticket_id}/confirm", response_model=ActionResult)
@router.post("/previews/{ticket_id}/confirm", response_model=ActionResult)
def confirm_preview(ticket_id: str) -> ActionResult:
    resolved = _as_ticket_id(ticket_id)
    ticket, message = preview_service.confirm_preview(resolved) if resolved is not None else (None, f"预览单 {ticket_id} 不存在")
    return ActionResult(ok=ticket is not None, message=message, entry=ticket)


@router.post("/mask_rule/previews/{ticket_id}/activate", response_model=ActionResult)
@router.post("/mask-previews/{ticket_id}/activate", response_model=ActionResult)
def activate_preview(ticket_id: str) -> ActionResult:
    resolved = _as_ticket_id(ticket_id)
    ticket, message = preview_service.activate(resolved) if resolved is not None else (None, f"预览单 {ticket_id} 不存在")
    return ActionResult(ok=ticket is not None, message=message, entry=ticket)


def _download_ticket(ticket_pk: int) -> Any:
    ticket = preview_service.get_ticket(ticket_pk)
    if ticket is None:
        return JSONResponse(status_code=404, content={"ok": False, "message": f"预览单 {ticket_pk} 不存在"})
    if not ticket.get("can_download"):
        message = "下载被拒绝：" + "；".join(ticket.get("blocking_reasons", []))
        return JSONResponse(status_code=409, content={"ok": False, "message": message, "detail": message})
    content = preview_service.delivery_csv(ticket)
    filename = f"masked-{ticket.get('batch_no')}-{ticket.get('confirmed_version') or ticket.get('rule_version')}.csv"
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/mask_rule/previews/{ticket_id}/download")
@router.get("/mask-previews/{ticket_id}/download")
@router.get("/previews/{ticket_id}/download")
def download_preview(ticket_id: str) -> Any:
    resolved = _as_ticket_id(ticket_id)
    if resolved is None:
        return JSONResponse(status_code=404, content={"ok": False, "message": f"预览单 {ticket_id} 不存在"})
    return _download_ticket(resolved)
