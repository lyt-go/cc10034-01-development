"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class KAnonymityService(BaseModuleService):
    MODULE = "k_anonymity"
    ENTITY = "匿名检查"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["检查编号", "数据集名称", "准标识符列", "K值要求", "等价类数量", "最小等价类大小", "匿名化措施", "检查结论"]
    REQUIRED_FIELDS = ["检查编号", "数据集名称", "准标识符列"]
    STATUS_ORDER = ["待检查", "已通过", "未通过", "已处理"]
    ACTION_RULES = {"发起检查": "已通过", "标记通过": "未通过", "标记未通过": "已处理"}
    NEGATIVE_ACTIONS = []
