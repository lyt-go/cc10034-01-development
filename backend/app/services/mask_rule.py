"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class MaskRuleService(BaseModuleService):
    MODULE = "mask_rule"
    ENTITY = "脱敏规则"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["规则编号", "目标字段", "脱敏算法", "保留位数", "掩码字符", "规则版本", "适用场景", "生效时间"]
    REQUIRED_FIELDS = ["规则编号", "目标字段", "脱敏算法"]
    STATUS_ORDER = ["草稿", "待验证", "已生效", "已废弃"]
    ACTION_RULES = {"提交验证": "待验证", "标记生效": "已生效", "标记废弃": "已废弃"}
    NEGATIVE_ACTIONS = []
