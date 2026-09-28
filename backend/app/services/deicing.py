"""除冰作业业务规则：状态流转、字段校验与筛选口径都收在这里。

字段必填与取值范围只有 deicing_rules 一份口径，登记与动作都直接调用，
不再各自判断负数用量。
"""
from __future__ import annotations

from typing import Any

from app.services.deicing_rules import (
    REQUIRED_FIELDS,
    format_errors,
    validate_deicing_fields,
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

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        # 登记口径：必填字段与取值范围都走同一份校验。
        errors = validate_deicing_fields(values, required=True)
        if errors:
            return None, errors
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in REQUIRED_FIELDS})
        entry["status"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return entry, []

    def run_action(self, entry_id: int, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"除冰单 {entry_id} 不存在或已归档"
        # 动作口径：单据上的必填项已在登记/初始化时确认，这里只复核随动作提交
        # 的取值范围（如除冰液用量不能为负），说明文案与登记完全同一套。
        errors = validate_deicing_fields(values, required=False)
        if errors:
            return None, format_errors(errors)
        action = str(values.get("action") or "").strip()
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于除冰作业可执行范围"
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return entry, f"除冰单已{action}"
