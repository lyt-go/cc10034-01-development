"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

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
