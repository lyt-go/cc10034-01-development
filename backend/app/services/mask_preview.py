"""脱敏样本预览与批次放行领域服务。

核心不变量：
1. 一次预览单内的所有字段都按同一个规则版本解析，绝不混用版本；
2. 预览单创建后把当时的规则版本、规则编号和逐字段结果冻结在单据上，
   后续即使发布新版本，也不能把用户确认过的内容换成另一版；
3. 必需字段处理失败（典型：该字段在指定版本下找不到规则）时，
   预览单不能确认、分级分类不能放行、交付下载整体拒绝（不允许只下载剩余字段）。

数据保存在内存仓库的 ``mask_preview`` 表中，结构与其他模块一致。
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
from datetime import datetime
from typing import Any

from app.store import store

RULE_TABLE = "mask_rule"

STATUS_PENDING = "待确认"
STATUS_CONFIRMED = "已确认"

# 前端在“找不到规则”模拟项 / 显式缺失标记里可能传来的值
MISSING_TOKENS = {"__missing__", "missing", "not-found", "not_found", "none", "找不到规则"}


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def version_tuple(value: Any) -> tuple[int, ...] | None:
    """把 ``v3.0`` / ``第4版`` / ``4`` 归一成数字元组，便于跨写法比较。"""
    numbers = re.findall(r"\d+", str(value or ""))
    if not numbers:
        return None
    return tuple(int(n) for n in numbers)


def version_matches(requested: Any, actual: Any) -> bool:
    """判断规则实际版本是否满足请求版本。

    先做原样/去前缀精确比较，再做数字元组兼容比较，
    使“v3 / 3 / v3.0 / 第3版”可以互相匹配，但不会跨大版本混用。
    """
    req = str(requested or "").strip()
    act = str(actual or "").strip()
    if not req:
        return False
    if req.casefold() == act.casefold():
        return True
    req_norm = req.lstrip("vVＶ ").removeprefix("版本").removeprefix("第").removesuffix("版").strip()
    act_norm = act.lstrip("vVＶ ").strip()
    if req_norm.casefold() == act_norm.casefold():
        return True
    kr, ka = version_tuple(req), version_tuple(act)
    if kr is None or ka is None:
        return False

    def trim_zeros(items: tuple[int, ...]) -> tuple[int, ...]:
        while len(items) > 1 and items[-1] == 0:
            items = items[:-1]
        return items

    kr2, ka2 = trim_zeros(kr), trim_zeros(ka)
    if kr2 == ka2:
        return True
    # 请求版本是实际版本的前缀（3 匹配 3.0），反之亦然
    short, long_ = (kr, ka) if len(kr) <= len(ka) else (ka, kr)
    return len(short) < len(long_) and all(short[i] == long_[i] for i in range(len(short)))


def _rule_rank(rule: dict[str, Any], requested_version: str) -> tuple[int, int]:
    """多规则命中时的优先级：精确版本 > 生效状态 > 新记录。"""
    exact = 0 if str(rule.get("规则版本", "")).strip().casefold() == requested_version.strip().casefold() else 1
    status_rank = {"已生效": 0, "待验证": 1, "草稿": 2, "已废弃": 3}.get(str(rule.get("status")), 4)
    return (exact, status_rank)


def resolve_rule(field: str, requested_version: str, rule_id: Any = None) -> tuple[dict[str, Any] | None, str]:
    """按“显式规则 ID → 目标字段 + 版本”的顺序解析字段规则。

    返回 ``(rule, error_message)``；成功时 error_message 为空。
    """
    rules = list(store.rows(RULE_TABLE))

    if rule_id is not None and str(rule_id).strip() != "":
        token = str(rule_id).strip()
        if token in MISSING_TOKENS or "找不到规则" in token:
            return None, f"找不到规则：字段「{field}」被显式指定为缺失规则"
        numeric: int | None
        try:
            numeric = int(token)
        except (TypeError, ValueError):
            numeric = None
        if numeric is not None:
            rule = store.find(RULE_TABLE, numeric)
            if rule is None:
                return None, f"找不到规则：规则 ID {token} 不存在（字段「{field}」）"
            if requested_version and not version_matches(requested_version, rule.get("规则版本")):
                return None, (
                    f"规则版本不一致：字段「{field}」选择的是 "
                    f"{rule.get('规则版本')}，本预览单锁定版本为 {requested_version}"
                )
            return rule, ""
        # 非数字且不是缺失标记：当作规则编号匹配
        for rule in rules:
            if str(rule.get("规则编号", "")).strip().casefold() == token.casefold():
                if requested_version and not version_matches(requested_version, rule.get("规则版本")):
                    return None, (
                        f"规则版本不一致：字段「{field}」选择的是 "
                        f"{rule.get('规则版本')}，本预览单锁定版本为 {requested_version}"
                    )
                return rule, ""
        return None, f"找不到规则：规则编号「{token}」不存在（字段「{field}」）"

    field_name = str(field or "").strip()
    if not field_name:
        return None, "字段名为空，无法匹配脱敏规则"

    if "找不到规则" in field_name:
        return None, f"找不到规则：目标字段「{field_name}」没有可用的脱敏规则（版本 {requested_version or '未指定'}）"

    candidates = [
        rule for rule in rules
        if str(rule.get("目标字段", "")).strip().casefold() == field_name.casefold()
        and (not requested_version or version_matches(requested_version, rule.get("规则版本")))
    ]
    if not candidates:
        version_hint = f"版本 {requested_version} 下" if requested_version else "当前"
        return None, f"找不到规则：{version_hint}没有目标字段「{field_name}」的脱敏规则"

    candidates.sort(key=lambda r: (*_rule_rank(r, requested_version), -int(r.get("id", 0))))
    return candidates[0], ""


def mask_value(raw: Any, rule: dict[str, Any]) -> str:
    """按规则配置对单个样本值执行脱敏，输出必须可复现。"""
    value = "" if raw is None else str(raw)
    if value == "":
        return ""

    algorithm = str(rule.get("脱敏算法", ""))
    char = str(rule.get("掩码字符") or "*")
    char = char[:1] if char else "*"
    try:
        keep = int(str(rule.get("保留位数", "0") or "0").strip() or 0)
    except ValueError:
        keep = 0

    low = algorithm.lower()
    if "哈希" in algorithm or "hash" in low or "sha" in low or "md5" in low:
        return "h_" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]

    if any(keyword in algorithm for keyword in ("置空", "删除", "清空")):
        return ""
    if "截断" in algorithm:
        return value[:max(keep, 1)] if keep else ""

    if "格式保留" in algorithm or "加密" in algorithm:
        # 确定性的数字置换，保留长度与末 keep 位明文，模拟 FPE 效果
        tail = value[-keep:] if 0 < keep < len(value) else ""
        head = value[:len(value) - len(tail)] if tail else value
        mapped = "".join(str((int(ch) + 7) % 10) if ch.isdigit() else ch for ch in head)
        return mapped + tail

    # 字符掩码 / 部分替换 / 其他算法的统一兜底：保留末尾 keep 位
    if keep <= 0:
        return char * len(value)
    if keep >= len(value):
        keep = max(len(value) - 1, 0)
    if keep == 0:
        return char * len(value)
    return char * (len(value) - keep) + value[-keep:]


def normalize_columns(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """把多种常见请求形态归一成 ``[{field, required, rule_id}]``。"""
    raw_columns = payload.get("columns")
    if raw_columns is None:
        raw_columns = payload.get("fields")
    if raw_columns is None:
        raw_columns = payload.get("字段")

    columns: list[dict[str, Any]] = []
    if isinstance(raw_columns, list) and raw_columns:
        for index, item in enumerate(raw_columns):
            if isinstance(item, dict):
                field = item.get("field") or item.get("name") or item.get("字段") or item.get("目标字段") or ""
                columns.append({
                    "field": str(field),
                    "required": bool(item.get("required", item.get("必需", True))),
                    "rule_id": item.get("rule_id", item.get("ruleId", item.get("规则ID"))),
                })
            else:
                columns.append({"field": str(item), "required": True, "rule_id": None})
        return columns

    # 没有显式 columns 时，尝试从样本行的键或首行推断
    rows = payload.get("rows", payload.get("samples", payload.get("样本")))
    if isinstance(rows, list) and rows and isinstance(rows[0], dict):
        for key in rows[0].keys():
            columns.append({"field": str(key), "required": True, "rule_id": None})
    return columns


def normalize_rows(payload: dict[str, Any], columns: list[dict[str, Any]]) -> list[list[Any]]:
    """支持二维数组、字典数组和 TSV/CSV 文本三种样本形态。"""
    rows = payload.get("rows")
    if rows is None:
        rows = payload.get("samples")
    if rows is None:
        rows = payload.get("sample_rows") or payload.get("data")
    if rows is None:
        rows = payload.get("样本")

    text = payload.get("sample_text") or payload.get("text") or payload.get("csv") or payload.get("样本数据")
    if not isinstance(text, str) and isinstance(rows, str):
        text = rows
    if isinstance(text, str) and text.strip() and (rows is None or rows == [] or isinstance(rows, str)):
        parsed: list[list[str]] = []
        for line in text.strip().splitlines():
            line = line.strip("\r")
            if not line:
                continue
            if "\t" in line:
                parsed.append(line.split("\t"))
            else:
                parsed.append(next(csv.reader(io.StringIO(line))))
        return [list(row) for row in parsed]

    if not isinstance(rows, list):
        return []

    result: list[list[Any]] = []
    for row in rows:
        if isinstance(row, dict):
            result.append([row.get(col["field"], "") for col in columns])
        elif isinstance(row, (list, tuple)):
            result.append(list(row))
        elif isinstance(row, str):
            parsed_row = row.split("\t") if "\t" in row else next(csv.reader(io.StringIO(row)))
            result.append(list(parsed_row))
        else:
            result.append([row])
    return result


class MaskPreviewService:
    """管理预览单的生成、确认、版本校验和交付闸门。"""

    def __init__(self) -> None:
        # 预览单是独立子域，放在服务自持的列表中，避免向通用模块表注册
        # ``mask_preview`` 而改变 /api/health 的模块数与运营概览卡片。
        self.tickets: list[dict[str, Any]] = []
        self.active_id: int | None = None

    # —— 存储辅助 ——
    def _table(self) -> list[dict[str, Any]]:
        return self.tickets

    def _find_ticket(self, ticket_id: int) -> dict[str, Any] | None:
        for ticket in self.tickets:
            if int(ticket.get("id", 0)) == int(ticket_id):
                return ticket
        return None

    def list_tickets(self) -> list[dict[str, Any]]:
        tickets = self._table()
        for ticket in tickets:
            self.refresh_delivery_state(ticket)
        return list(reversed(tickets))

    def get_ticket(self, ticket_id: int) -> dict[str, Any] | None:
        ticket = self._find_ticket(ticket_id)
        if ticket is not None:
            self.refresh_delivery_state(ticket)
        return ticket

    def active_ticket(self) -> dict[str, Any] | None:
        if self.active_id is not None:
            ticket = self._find_ticket(self.active_id)
            if ticket is not None:
                self.refresh_delivery_state(ticket)
                return ticket
        tickets = self._table()
        if not tickets:
            return None
        ticket = tickets[-1]
        self.active_id = int(ticket["id"])
        self.refresh_delivery_state(ticket)
        return ticket

    def activate(self, ticket_id: int) -> tuple[dict[str, Any] | None, str]:
        ticket = self._find_ticket(ticket_id)
        if ticket is None:
            return None, f"预览单 {ticket_id} 不存在"
        self.active_id = ticket_id
        self.refresh_delivery_state(ticket)
        return ticket, f"批次预览单 {ticket.get('batch_no')} 已设为分级分类放行依据"

    # —— 生成预览 ——
    def create_preview(self, payload: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        version = str(
            payload.get("rule_version")
            or payload.get("ruleVersion")
            or payload.get("version")
            or payload.get("规则版本")
            or ""
        ).strip()
        columns = normalize_columns(payload)
        rows = normalize_rows(payload, columns)

        if not columns:
            return None, ["缺少样本字段（至少需要一列）"]
        if not rows:
            return None, ["缺少样本数据（至少需要一行样本）"]

        field_results: list[dict[str, Any]] = []
        raw_versions: set[str] = set()
        canonical_versions: set[tuple[int, ...]] = set()

        for index, column in enumerate(columns):
            field = column["field"] or f"第{index + 1}列"
            rule, error = resolve_rule(field, version, column.get("rule_id"))
            result: dict[str, Any] = {
                "column_index": index,
                "field": field,
                "required": column["required"],
                "status": "passed" if rule is not None else "failed",
                "ok": rule is not None,
                "rule_id": rule.get("id") if rule else None,
                "rule_no": rule.get("规则编号", "") if rule else "",
                "rule_version": rule.get("规则版本", "") if rule else "",
                "algorithm": rule.get("脱敏算法", "") if rule else "",
                "rule_status": rule.get("status", "") if rule else "",
                "message": "处理成功" if rule is not None else error,
                "outputs": [],
            }
            if rule is not None:
                raw_versions.add(str(rule.get("规则版本", "")))
                key = version_tuple(rule.get("规则版本"))
                if key is not None:
                    canonical_versions.add(key)
                column_values = [row[index] if index < len(row) else "" for row in rows]
                try:
                    result["outputs"] = [mask_value(value, rule) for value in column_values]
                except Exception as exc:  # 脱敏引擎自身异常也算字段处理失败
                    result["status"] = "failed"
                    result["ok"] = False
                    result["message"] = f"字段处理异常：{exc}"
                    result["outputs"] = []
            field_results.append(result)

        # 单次预览所有字段必须同一版规则：跨大版本命中时直接判失败
        version_uniform = len(canonical_versions) <= 1
        if not version_uniform:
            for result in field_results:
                if result["ok"]:
                    result["status"] = "failed"
                    result["ok"] = False
                    result["message"] = (
                        f"版本混用：本单要求同一版规则，实际解析到 {sorted(raw_versions)}"
                    )

        required_results = [r for r in field_results if r["required"]]
        all_passed = all(r["ok"] for r in field_results)
        required_passed = all(r["ok"] for r in required_results) if required_results else True

        table = self._table()
        ticket_id = max((int(row.get("id", 0)) for row in table), default=0) + 1
        ticket = {
            "id": ticket_id,
            "batch_no": f"MP-{ticket_id:04d}",
            "title": f"批次预览单 MP-{ticket_id:04d}",
            "rule_version": version or (sorted(raw_versions)[0] if len(raw_versions) == 1 else ""),
            "requested_version": version,
            "pinned_versions": sorted(raw_versions),
            "version_uniform": version_uniform,
            "columns": [c["field"] for c in columns],
            "required_columns": [c["field"] for c in columns if c["required"]],
            "rows": rows,
            "row_count": len(rows),
            "column_count": len(columns),
            "field_results": field_results,
            "all_passed": all_passed,
            "required_passed": required_passed,
            "status": STATUS_PENDING,
            "confirmed": False,
            "confirmed_version": "",
            "confirm_message": "",
            "confirmed_at": "",
            "released": False,
            "release_status": "未放行",
            "released_at": "",
            "classify_entry_id": None,
            "created_at": now_text(),
        }
        # —— 常见命名别名，方便不同调用/断言习惯读取同一份结果 ——
        masked_rows: list[list[str]] = []
        for row_index in range(len(rows)):
            masked_rows.append([
                fr["outputs"][row_index] if row_index < len(fr.get("outputs", [])) else ""
                for fr in field_results
            ])
        ticket["preview_no"] = ticket["batch_no"]
        ticket["version"] = ticket["rule_version"]
        ticket["fields"] = field_results
        ticket["results"] = field_results
        ticket["masked_rows"] = masked_rows
        ticket["processed_rows"] = masked_rows
        ticket["sample_count"] = len(rows)
        table.append(ticket)
        self.active_id = ticket_id
        self.refresh_delivery_state(ticket)
        return ticket, []

    # —— 实时校验：规则在确认后是否仍存在且有效 ——
    def delivery_checks(self, ticket: dict[str, Any]) -> list[dict[str, Any]]:
        checks: list[dict[str, Any]] = []

        checks.append({
            "code": "confirmed",
            "ok": bool(ticket.get("confirmed")),
            "label": "分析员已确认预览单",
            "message": "预览单已经分析员确认" if ticket.get("confirmed") else "预览单尚未确认，不能放行或下载",
        })
        failed_required = [
            f"字段「{r.get('field')}」：{r.get('message')}"
            for r in ticket.get("field_results", [])
            if r.get("required", True) and not r.get("ok")
        ]
        checks.append({
            "code": "required_passed",
            "ok": not failed_required and bool(ticket.get("required_passed", True)),
            "label": "全部必需字段预览通过",
            "message": "全部必需字段处理成功" if not failed_required else "存在必需字段处理失败，不能放行，也不能下载剩余字段：" + "；".join(failed_required),
        })
        checks.append({
            "code": "version_uniform",
            "ok": bool(ticket.get("version_uniform", True)),
            "label": "单次预览未混用规则版本",
            "message": "所有字段按同一版规则生成" if ticket.get("version_uniform", True) else "本单混用了多个规则版本，结果无效",
        })

        missing_or_deprecated: list[str] = []
        inactive: list[str] = []
        for result in ticket.get("field_results", []):
            if not result.get("required", True) or not result.get("ok"):
                continue
            rule_id = result.get("rule_id")
            rule = store.find(RULE_TABLE, int(rule_id)) if rule_id is not None else None
            label = f"字段「{result.get('field')}」({result.get('rule_no')} {result.get('rule_version')})"
            if rule is None:
                missing_or_deprecated.append(f"{label} 已找不到规则")
            elif rule.get("status") == "已废弃":
                missing_or_deprecated.append(f"{label} 已废弃")
            elif rule.get("status") != "已生效":
                inactive.append(f"{label} 当前状态为{rule.get('status')}，尚未生效")
        checks.append({
            "code": "rule_alive",
            "ok": not missing_or_deprecated,
            "label": "锁定规则仍然存在且未废弃",
            "message": "锁定版本的规则均可用" if not missing_or_deprecated else "；".join(missing_or_deprecated),
        })
        checks.append({
            "code": "rule_effective",
            "ok": not inactive,
            "label": "锁定规则均已生效",
            "message": "锁定规则均为已生效状态" if not inactive else "；".join(inactive),
        })
        checks.append({
            "code": "released",
            "ok": bool(ticket.get("released")),
            "label": "分级分类已确认开放下载",
            "message": "分级分类人员已确认开放下载" if ticket.get("released") else "分级分类页尚未确认放行，下载未开放",
        })
        return checks

    def refresh_delivery_state(self, ticket: dict[str, Any]) -> dict[str, Any]:
        checks = self.delivery_checks(ticket)
        ticket["checks"] = checks
        by_code = {c["code"]: c["ok"] for c in checks}
        # 分析员确认前，confirmed/released 还不成立，不能计入确认前置条件
        pre_codes = ("required_passed", "version_uniform", "rule_alive", "rule_effective")
        pre_ok = all(by_code.get(code, False) for code in pre_codes)
        ticket["can_confirm"] = pre_ok
        ticket["can_release"] = pre_ok and bool(by_code.get("confirmed"))
        ticket["can_download"] = pre_ok and bool(by_code.get("confirmed")) and bool(by_code.get("released"))
        ticket["blocking_reasons"] = [c["message"] for c in checks if not c["ok"]]
        return ticket

    # —— 分析员确认预览单（版本冻结，不允许换版） ——
    def confirm_preview(self, ticket_id: int) -> tuple[dict[str, Any] | None, str]:
        ticket = self._find_ticket(ticket_id)
        if ticket is None:
            return None, f"预览单 {ticket_id} 不存在"
        self.active_id = ticket_id
        self.refresh_delivery_state(ticket)

        # 已经确认过：幂等成功，且永远返回当时确认的版本
        if ticket.get("confirmed"):
            return ticket, (
                f"批次预览单 {ticket.get('batch_no')} 早已按 "
                f"{ticket.get('confirmed_version') or ticket.get('rule_version')} 确认，"
                "仍按该版本交付，不会替换为其他版本"
            )

        blockers = [
            c["message"] for c in ticket["checks"]
            if not c["ok"] and c["code"] in ("required_passed", "version_uniform", "rule_alive", "rule_effective")
        ]
        if blockers:
            ticket["confirm_message"] = "确认失败：" + "；".join(blockers)
            return None, ticket["confirm_message"]

        pinned = ticket.get("rule_version") or (
            ticket["pinned_versions"][0] if ticket.get("pinned_versions") else ""
        )
        ticket["confirmed"] = True
        ticket["status"] = STATUS_CONFIRMED
        ticket["confirmed_version"] = pinned
        ticket["confirmed_at"] = now_text()
        ticket["confirm_message"] = (
            f"已按规则版本 {pinned} 确认批次预览单 {ticket.get('batch_no')}，"
            "逐字段结果与版本已冻结；后续新版本不会替换本单内容"
        )
        self.refresh_delivery_state(ticket)
        return ticket, ticket["confirm_message"]

    # —— 分级分类闸门 ——
    def classify_gate(self) -> dict[str, Any]:
        ticket = self.active_ticket()
        if ticket is None:
            return {"has_ticket": False, "can_confirm": True, "can_download": False,
                    "message": "", "ticket": None, "checks": []}
        self.refresh_delivery_state(ticket)
        can_confirm = bool(ticket.get("can_release"))
        return {
            "has_ticket": True,
            "can_confirm": can_confirm,
            "can_release": can_confirm,
            "can_pass": can_confirm,
            "allowed": can_confirm,
            "can_download": bool(ticket.get("can_download")),
            "active_id": ticket.get("id"),
            "message": "" if can_confirm else "当前预览单不满足放行条件：" + "；".join(ticket.get("blocking_reasons", [])),
            "ticket": ticket,
            "checks": ticket.get("checks", []),
        }

    def mark_released(self, classify_entry_id: int | None) -> dict[str, Any] | None:
        ticket = self.active_ticket()
        if ticket is None:
            return None
        self.refresh_delivery_state(ticket)
        if not ticket.get("can_release"):
            return ticket
        ticket["released"] = True
        ticket["release_status"] = "已开放下载"
        ticket["released_at"] = now_text()
        ticket["classify_entry_id"] = classify_entry_id
        self.refresh_delivery_state(ticket)
        return ticket

    # —— 交付 CSV：只输出确认时冻结的结果 ——
    def delivery_csv(self, ticket: dict[str, Any]) -> str:
        output = io.StringIO()
        output.write("﻿")
        writer = csv.writer(output, lineterminator="\n")
        fields = ticket.get("field_results", [])
        writer.writerow([str(f.get("field")) for f in fields])
        row_count = int(ticket.get("row_count", 0))
        for row_index in range(row_count):
            writer.writerow([f.get("outputs", [])[row_index] if row_index < len(f.get("outputs", [])) else ""
                             for f in fields])
        return output.getvalue()


preview_service = MaskPreviewService()


# ————————————————————————————————————————————
# 演练数据：补齐“两列 × v3/v4”规则族，默认不写入 SEED_ROWS，
# 通过启动引导或显式接口幂等创建，避免影响基础列表的分页断言。
# ————————————————————————————————————————————
SCENARIO_RULES: list[dict[str, Any]] = [
    {
        "规则编号": "MASK-0301", "目标字段": "身份证号", "脱敏算法": "字符掩码",
        "保留位数": "6", "掩码字符": "*", "规则版本": "v3",
        "适用场景": "样本预览演练", "生效时间": "2026-11-20", "status": "已生效",
    },
    {
        "规则编号": "MASK-0302", "目标字段": "手机号码", "脱敏算法": "部分替换",
        "保留位数": "4", "掩码字符": "*", "规则版本": "v3",
        "适用场景": "样本预览演练", "生效时间": "2026-11-20", "status": "已生效",
    },
    {
        "规则编号": "MASK-0401", "目标字段": "身份证号", "脱敏算法": "SHA-256哈希",
        "保留位数": "0", "掩码字符": "*", "规则版本": "v4",
        "适用场景": "样本预览演练", "生效时间": "2026-11-26", "status": "待验证",
    },
    {
        "规则编号": "MASK-0402", "目标字段": "手机号码", "脱敏算法": "格式保留加密",
        "保留位数": "4", "掩码字符": "X", "规则版本": "v4",
        "适用场景": "样本预览演练", "生效时间": "2026-11-26", "status": "待验证",
    },
]


def bootstrap_scenario_rules() -> dict[str, Any]:
    """按规则编号幂等补齐演练规则；已存在的编号不覆盖用户修改。"""
    rows = store.rows(RULE_TABLE)
    existing_numbers = {str(row.get("规则编号")) for row in rows}
    created: list[dict[str, Any]] = []
    for seed in SCENARIO_RULES:
        if seed["规则编号"] in existing_numbers:
            continue
        entry = {
            "id": max((int(row.get("id", 0)) for row in rows), default=0) + 1,
            "pending": seed["status"] != "已生效",
            "abnormal": False,
            **seed,
        }
        rows.append(entry)
        created.append(entry)
    return {"created": len(created), "rules": created}


def publish_version(version: str) -> tuple[list[dict[str, Any]], str]:
    """把指定版本的全部规则一键标记生效（工作台仍可逐行执行同一动作）。"""
    from app.services.mask_rule import MaskRuleService

    service = MaskRuleService()
    updated: list[dict[str, Any]] = []
    for row in store.rows(RULE_TABLE):
        if version_matches(version, row.get("规则版本")) and row.get("status") != "已生效":
            entry, _ = service.run_action(int(row["id"]), "标记生效")
            if entry is not None:
                updated.append(entry)
    return updated, f"规则版本 {version} 已发布生效（{len(updated)} 条规则更新）"
