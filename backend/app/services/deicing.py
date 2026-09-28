"""除冰作业业务规则：状态流转、字段校验与筛选口径都收在这里。

字段校验不在本文件各写一份，统一调用 deicing_validation 里的唯一口径，
登记、动作、示例数据初始化依次复用同一组规则与失败说明。
"""
from __future__ import annotations

from typing import Any

from app.services.deicing_validation import (
    REQUIRED_FIELDS,
    format_validation_errors,
    validate_deicing_entry,
)
from app.store import store

MODULE = "deicing"
STATUS_ORDER = ["待作业", "作业中", "已完成", "已取消"]
ACTION_RULES = {"安排作业": "作业中", "确认完成": "已完成", "取消作业": "已取消"}
NEGATIVE_ACTIONS = []


class DeicingService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("除冰单号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        """登记一条除冰单；不合规时返回 (None, 统一失败说明)。"""
        errors = validate_deicing_entry(values)
        if errors:
            return None, format_validation_errors(errors)
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in REQUIRED_FIELDS})
        entry["status"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return entry, ""

    def run_action(
        self, entry_id: int, action: str, values: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any] | None, str]:
        """对单条除冰单执行动作；动作若携带字段（如除冰液用量），按同一份口径校验。"""
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"除冰单 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于除冰作业可执行范围"
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        # 动作请求里若带了字段，则与单据既有字段合并后走同一份校验口径；
        # 不带字段时退化为只看单据自身，因此既有的安排/完成/取消结果不变。
        if values:
            merged = {**entry, **values}
            errors = validate_deicing_entry(merged)
            if errors:
                return None, format_validation_errors(errors)
        entry["status"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return entry, f"除冰单已{action}"
