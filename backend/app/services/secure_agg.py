"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class SecureAggService(BaseModuleService):
    MODULE = "secure_agg"
    ENTITY = "聚合任务"
    OPERATION_TERM = "聚合"
    LIST_FIELDS = ["任务编号", "数据源列表", "聚合函数", "参与方数量", "最小阈值", "聚合结果", "执行时间", "验证状态"]
    REQUIRED_FIELDS = ["任务编号", "数据源列表", "聚合函数"]
    STATUS_ORDER = ["待执行", "执行中", "已完成", "验证失败"]
    ACTION_RULES = {"发起聚合": "执行中", "标记完成": "已完成", "标记失败": "验证失败"}
    NEGATIVE_ACTIONS = []
