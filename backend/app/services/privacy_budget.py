"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class PrivacyBudgetService(BaseModuleService):
    MODULE = "privacy_budget"
    ENTITY = "隐私预算"
    OPERATION_TERM = "查询"
    LIST_FIELDS = ["预算编号", "数据集名称", "总预算Epsilon", "已消耗Epsilon", "消耗记录", "预算周期", "重置时间", "超额策略"]
    REQUIRED_FIELDS = ["预算编号", "数据集名称", "总预算Epsilon"]
    STATUS_ORDER = ["正常", "预警", "已耗尽", "已重置"]
    ACTION_RULES = {"标记预警": "预警", "锁定查询": "已耗尽", "重置预算": "已重置"}
    NEGATIVE_ACTIONS = []
