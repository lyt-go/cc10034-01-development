"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class GrantApprovalService(BaseModuleService):
    MODULE = "grant_approval"
    ENTITY = "授权申请"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["申请编号", "申请人", "目标数据", "使用目的", "有效期起", "有效期止", "访问级别", "审批状态"]
    REQUIRED_FIELDS = ["申请编号", "申请人", "目标数据"]
    STATUS_ORDER = ["待审批", "已批准", "已拒绝", "已过期"]
    ACTION_RULES = {"批准申请": "已批准", "拒绝申请": "已拒绝", "标记过期": "已过期"}
    NEGATIVE_ACTIONS = ["拒绝申请"]
