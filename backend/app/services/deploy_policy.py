"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class DeployPolicyService(BaseModuleService):
    MODULE = "deploy_policy"
    ENTITY = "策略分发"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["分发编号", "策略内容", "目标节点", "下发状态", "生效时间", "冲突策略", "回滚版本", "操作时间"]
    REQUIRED_FIELDS = ["分发编号", "策略内容", "目标节点"]
    STATUS_ORDER = ["待下发", "已生效", "冲突待处理", "已回滚"]
    ACTION_RULES = {"下发策略": "已生效", "标记冲突": "冲突待处理", "回滚策略": "已回滚"}
    NEGATIVE_ACTIONS = ["回滚策略"]
