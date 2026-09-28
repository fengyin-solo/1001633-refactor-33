"""除冰单字段校验的唯一口径。

登记除冰单、动作状态流转、示例数据初始化三处都调用这里的同一组规则，
避免同一条规则各抄一份，导致负数用量在某个入口放行、某个入口拦下，
以及失败说明三处说法不一。

规则（与既有行为保持一致，不新增约束）：
- 除冰单号、关联航班、除冰方式为必填，去掉空白后不能为空；
- 除冰液用量为选填：留空允许；一旦填的是数值，就必须是非负数。
  无法解析为数值的自由文本（如示例占位文字）不视为数值，按未填报处理。
"""
from __future__ import annotations

from typing import Any

# 登记除冰单时必须非空的字段。
REQUIRED_FIELDS: tuple[str, ...] = ("除冰单号", "关联航班", "除冰方式")
# 数值型用量字段名。
AMOUNT_FIELD = "除冰液用量"


def _as_number(value: Any) -> tuple[bool, float]:
    """把输入折算成数值，返回 ``(是否为数值, 数值)``。

    数字本身以及可解析的数字字符串算数值；None、空串和无法解析为数字的
    自由文本不算数值，交回上层按“未填报数值”放行。bool 虽是 int 子类，
    但语义上不是用量，一律不视为数值。
    """
    if isinstance(value, bool):
        return False, 0.0
    if isinstance(value, (int, float)):
        return True, float(value)
    if isinstance(value, str):
        try:
            return True, float(value.strip())
        except ValueError:
            return False, 0.0
    return False, 0.0


def missing_fields(values: dict[str, Any]) -> list[str]:
    """返回缺失（去空白后为空）的必填字段，按 REQUIRED_FIELDS 的顺序。"""
    return [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]


def amount_error(values: dict[str, Any]) -> str | None:
    """校验除冰液用量；返回一句失败说明，合规或未填时返回 None。"""
    raw = values.get(AMOUNT_FIELD)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None
    is_number, number = _as_number(raw)
    if is_number and number < 0:
        return f"{AMOUNT_FIELD}必须为非负数（实际：{raw}）"
    return None


def validate_deicing_entry(values: dict[str, Any]) -> list[str]:
    """按统一口径校验一条除冰单，返回字段级失败说明列表；为空表示合规。

    登记、动作、初始化三个入口都调用本函数，保证规则与措辞只有一份。
    """
    errors: list[str] = []
    missing = missing_fields(values)
    if missing:
        errors.append(f"缺少必填字段：{'、'.join(missing)}")
    message = amount_error(values)
    if message:
        errors.append(message)
    return errors


def format_validation_errors(errors: list[str]) -> str:
    """把字段级失败说明合并成接口返回的一句话。"""
    return "；".join(errors)
