"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class PseudonymService(BaseModuleService):
    MODULE = "pseudonym"
    ENTITY = "假名映射"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["映射编号", "原始标识", "假名标识", "映射算法", "可逆标记", "盐值哈希", "创建时间", "失效时间"]
    REQUIRED_FIELDS = ["映射编号", "原始标识", "假名标识"]
    STATUS_ORDER = ["有效", "已失效", "已轮换"]
    ACTION_RULES = {"标记失效": "已失效", "轮换映射": "已轮换"}
    NEGATIVE_ACTIONS = []
