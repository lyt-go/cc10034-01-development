"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class AnomalyDetectService(BaseModuleService):
    MODULE = "anomaly_detect"
    ENTITY = "异常规则"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["规则编号", "检测维度", "检测算法", "阈值上限", "时间窗口", "告警级别", "规则版本", "触发次数"]
    REQUIRED_FIELDS = ["规则编号", "检测维度", "检测算法"]
    STATUS_ORDER = ["草稿", "待验证", "已启用", "已停用"]
    ACTION_RULES = {"提交验证": "待验证", "启用规则": "已启用", "停用规则": "已停用"}
    NEGATIVE_ACTIONS = ["停用规则"]
