"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class FederatedTrainService(BaseModuleService):
    MODULE = "federated_train"
    ENTITY = "训练任务"
    OPERATION_TERM = "聚合"
    LIST_FIELDS = ["任务编号", "参与节点", "模型类型", "聚合算法", "全局轮次", "全局准确率", "开始时间", "训练状态"]
    REQUIRED_FIELDS = ["任务编号", "参与节点", "模型类型"]
    STATUS_ORDER = ["初始化", "训练中", "已收敛", "已终止"]
    ACTION_RULES = {"启动训练": "训练中", "标记收敛": "已收敛", "终止任务": "已终止"}
    NEGATIVE_ACTIONS = []
