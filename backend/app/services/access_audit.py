"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class AccessAuditService(BaseModuleService):
    MODULE = "access_audit"
    ENTITY = "审计记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["记录编号", "访问主体", "目标资源", "访问操作", "访问时间", "请求IP", "访问结果", "敏感等级"]
    REQUIRED_FIELDS = ["记录编号", "访问主体", "目标资源"]
    STATUS_ORDER = ["已记录", "需复核", "已异常"]
    ACTION_RULES = {"标记复核": "需复核", "标记异常": "已异常"}
    NEGATIVE_ACTIONS = []
