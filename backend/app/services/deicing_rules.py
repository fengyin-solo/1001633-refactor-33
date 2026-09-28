"""除冰单字段校验的唯一口径。

登记、动作状态流转、示例数据初始化三处都调用本模块，避免必填字段与取值范围
各抄一份后对负数用量给出互相矛盾的结论。这里刻意不依赖 app.store，保证
seed/store 初始化阶段也能导入，不会形成循环引用。
"""
from __future__ import annotations

from typing import Any

REQUIRED_FIELDS = ("除冰单号", "关联航班", "除冰方式")
AMOUNT_FIELD = "除冰液用量"


def _as_number(value: Any) -> float | None:
    """把用量尝试解析成数值；解析不了（如示例里的文本占位值）返回 None 跳过。"""
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None
    return None


def validate_deicing_fields(values: dict[str, Any], *, required: bool) -> list[str]:
    """按统一口径校验除冰单字段，返回成型的失败说明；空列表表示通过。

    required=True 时检查必填字段（登记与初始化口径）；除冰液用量只要出现且
    能解析成数值就必须不小于 0，无法解析的文本占位值按历史口径放行。
    """
    errors: list[str] = []
    if required:
        missing = [
            name for name in REQUIRED_FIELDS
            if not str(values.get(name) or "").strip()
        ]
        if missing:
            errors.append(f"缺少必填字段：{'、'.join(missing)}")
    if AMOUNT_FIELD in values:
        amount = _as_number(values[AMOUNT_FIELD])
        if amount is not None and amount < 0:
            errors.append(f"{AMOUNT_FIELD}取值不合法：不能为负数，取值需不小于 0")
    return errors


def format_errors(errors: list[str]) -> str:
    """把同一套失败说明拼成接口/启动日志共用的一句话。"""
    return "；".join(errors)
