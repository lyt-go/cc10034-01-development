"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class RiskScanService(BaseModuleService):
    MODULE = "risk_scan"
    ENTITY = "扫描任务"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["任务编号", "扫描范围", "扫描规则", "风险等级", "检出数量", "误报数量", "扫描时间", "处理状态"]
    REQUIRED_FIELDS = ["任务编号", "扫描范围", "扫描规则"]
    STATUS_ORDER = ["待执行", "扫描中", "已完成", "已确认"]
    ACTION_RULES = {"发起扫描": "扫描中", "标记完成": "已完成", "确认风险": "已确认"}
    NEGATIVE_ACTIONS = []
