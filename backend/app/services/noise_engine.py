"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class NoiseEngineService(BaseModuleService):
    MODULE = "noise_engine"
    ENTITY = "噪声配置"
    OPERATION_TERM = "关联"
    LIST_FIELDS = ["配置编号", "噪声机制", "Epsilon值", "敏感度", "分布类型", "输出精度", "关联字段", "配置版本"]
    REQUIRED_FIELDS = ["配置编号", "噪声机制", "Epsilon值"]
    STATUS_ORDER = ["草稿", "待验证", "已生效", "已停用"]
    ACTION_RULES = {"提交验证": "待验证", "标记生效": "已生效", "停用配置": "已停用"}
    NEGATIVE_ACTIONS = ["停用配置"]
