"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class GradientEncryptService(BaseModuleService):
    MODULE = "gradient_encrypt"
    ENTITY = "加密配置"
    OPERATION_TERM = "关联"
    LIST_FIELDS = ["配置编号", "加密方案", "密钥长度", "同态层级", "计算开销", "通信开销", "关联任务", "配置状态"]
    REQUIRED_FIELDS = ["配置编号", "加密方案", "密钥长度"]
    STATUS_ORDER = ["草稿", "待验证", "已启用", "已停用"]
    ACTION_RULES = {"提交验证": "待验证", "启用配置": "已启用", "停用配置": "已停用"}
    NEGATIVE_ACTIONS = ["停用配置"]
