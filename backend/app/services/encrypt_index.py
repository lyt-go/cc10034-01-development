"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class EncryptIndexService(BaseModuleService):
    MODULE = "encrypt_index"
    ENTITY = "索引条目"
    OPERATION_TERM = "存储"
    LIST_FIELDS = ["条目编号", "加密域", "索引类型", "陷门哈希", "可搜索标记", "存储位置", "创建时间", "索引版本"]
    REQUIRED_FIELDS = ["条目编号", "加密域", "索引类型"]
    STATUS_ORDER = ["有效", "重建中", "已失效"]
    ACTION_RULES = {"发起重建": "重建中", "标记失效": "已失效"}
    NEGATIVE_ACTIONS = []
