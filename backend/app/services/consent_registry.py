"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class ConsentRegistryService(BaseModuleService):
    MODULE = "consent_registry"
    ENTITY = "同意记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["记录编号", "数据主体", "处理目的", "同意范围", "同意时间", "撤回时间", "法律依据", "生效状态"]
    REQUIRED_FIELDS = ["记录编号", "数据主体", "处理目的"]
    STATUS_ORDER = ["已同意", "已撤回", "已过期"]
    ACTION_RULES = {"撤回同意": "已撤回", "标记过期": "已过期"}
    NEGATIVE_ACTIONS = []
