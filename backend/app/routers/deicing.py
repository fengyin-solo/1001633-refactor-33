"""除冰作业接口：维护除冰单，覆盖安排作业、确认完成、取消作业等动作。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.deicing import DeicingService
from app.services.deicing_rules import format_errors

router = APIRouter(prefix="/api/deicing", tags=["除冰作业"])

service = DeicingService()

LIST_FIELDS = ["除冰单号", "关联航班", "除冰方式", "除冰液用量", "作业车辆", "作业人员", "完成时刻", "除冰状态"]
STATUSES = ["待作业", "作业中", "已完成", "已取消"]


@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按除冰单号检索"),
    status: str | None = Query(default=None, description="待作业、作业中、已完成、已取消"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按除冰单号与状态过滤除冰作业列表；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_entries(keyword=keyword, status=status, page=page, size=size)
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条除冰单明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"除冰单 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条除冰单，缺字段或取值越界时用统一说明告知原因，而不是静默丢弃。"""
    entry, errors = service.create_entry(payload.values)
    if errors:
        return ActionResult(ok=False, message=format_errors(errors))
    return ActionResult(ok=True, message="除冰单已登记", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条除冰单执行安排作业、确认完成、取消作业；字段越界或动作不允许都会
    用同一套校验说明拦下。"""
    entry, message = service.run_action(entry_id, payload.values)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)


@router.get("/export")
def export_entries() -> dict[str, Any]:
    """导出除冰作业清单：返回当前过滤条件下的全量数据。"""
    items, total = service.list_entries(page=1, size=10000)
    return {"module": "deicing", "total": total, "items": items}
