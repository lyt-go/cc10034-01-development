"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class DifferentialSqlService(BaseModuleService):
    MODULE = "differential_sql"
    ENTITY = "查询记录"
    OPERATION_TERM = "查询"
    LIST_FIELDS = ["查询编号", "查询语句", "查询用户", "消耗Epsilon", "噪声注入量", "返回行数", "执行时间", "预算剩余"]
    REQUIRED_FIELDS = ["查询编号", "查询语句", "查询用户"]
    STATUS_ORDER = ["已执行", "预算不足", "已拒绝", "已审计"]
    ACTION_RULES = {"标记拒绝": "已拒绝", "标记审计": "已审计"}
    NEGATIVE_ACTIONS = []
