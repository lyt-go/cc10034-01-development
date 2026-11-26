"""分级分类领域服务：确认分级前必须通过脱敏预览批次闸门。"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService


class ClassifyTagService(BaseModuleService):
    MODULE = "classify_tag"
    ENTITY = "分级标签"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["标签编号", "数据资源", "安全等级", "数据类型", "合规要求", "保留期限", "脱敏要求", "标签时间"]
    REQUIRED_FIELDS = ["标签编号", "数据资源", "安全等级"]
    STATUS_ORDER = ["待分级", "已分级", "需重审", "已降级"]
    ACTION_RULES = {"确认分级": "已分级", "标记重审": "需重审", "标记降级": "已降级"}
    NEGATIVE_ACTIONS = []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        # 只有“确认分级/放行”受预览批次约束；没有任何预览单时保持基础骨架行为，
        # 避免影响既有通用动作与回归用例。
        if action == "确认分级":
            from app.services.mask_preview import preview_service

            gate = preview_service.classify_gate()
            if gate.get("has_ticket") and not gate.get("can_confirm"):
                return None, gate.get("message") or "脱敏预览批次未满足放行条件"

        entry, message = super().run_action(entry_id, action)

        if action == "确认分级" and entry is not None:
            from app.services.mask_preview import preview_service

            gate = preview_service.classify_gate()
            if gate.get("has_ticket") and gate.get("can_confirm"):
                preview_service.mark_released(entry_id)
                ticket = gate.get("ticket") or {}
                message = (
                    f"{self.ENTITY}已确认分级，并依据批次 {ticket.get('batch_no')} "
                    f"（规则版本 {ticket.get('confirmed_version') or ticket.get('rule_version')}）开放下载"
                )
        return entry, message
