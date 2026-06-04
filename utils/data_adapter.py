# utils/data_adapter.py

from typing import Dict


# =========================================================
# 状态映射
# =========================================================

STATUS_MAP = {
    "正常": "normal",
    "normal": "normal",

    "预警": "warning",
    "warning": "warning",

    "危险": "danger",
    "danger": "danger"
}


# =========================================================
# 报警等级映射
# =========================================================

LEVEL_MAP = {
    "危险": "danger",
    "danger": "danger",

    "预警": "warning",
    "warning": "warning",

    "信息": "info",
    "提示": "info",
    "info": "info"
}


# =========================================================
# 报警处理状态映射
# =========================================================

HANDLE_STATUS_MAP = {
    "未处理": "unprocessed",
    "unprocessed": "unprocessed",

    "处理中": "processing",
    "processing": "processing",

    "已处理": "processed",
    "processed": "processed"
}


# =========================================================
# 安全 float 转换
# =========================================================

def safe_float(value, default=0.0):

    try:
        if value is None:
            return default

        return float(value)

    except Exception:
        return default


# =========================================================
# 安全 int 转换
# =========================================================

def safe_int(value, default=0):

    try:
        if value is None:
            return default

        return int(float(value))

    except Exception:
        return default


# =========================================================
# 标准化刀具状态
# =========================================================

def normalize_status(tool: Dict):

    status = tool.get("status")

    if status in STATUS_MAP:
        return STATUS_MAP[status]

    # 如果没有状态
    # 根据健康度自动推断
    health = safe_float(
        tool.get("health_score", 0)
    )

    if health >= 80:
        return "normal"

    elif health >= 60:
        return "warning"

    else:
        return "danger"


# =========================================================
# 标准化刀具数据
# =========================================================

def normalize_tool(tool: Dict):

    if not isinstance(tool, dict):
        return {}

    return {

        # 基础信息
        "tool_id": (
            tool.get("tool_id")
            or tool.get("id")
            or ""
        ),

        "machine": tool.get("machine", ""),

        "type": tool.get("type", ""),

        # 传感器
        "vibration": safe_float(
            tool.get("vibration", 0)
        ),

        "current": safe_float(
            tool.get("current", 0)
        ),

        "vb": safe_float(
            tool.get("vb", 0)
        ),

        # 健康度
        "health_score": safe_float(
            tool.get("health_score", 0)
        ),

        # 状态
        "status": normalize_status(tool),

        # 使用情况
        "current_usage": safe_float(
            tool.get("current_usage", 0)
        ),

        "rul": safe_int(
            tool.get("rul", 0)
        ),
    }


# =========================================================
# 标准化报警数据
# =========================================================

def normalize_alert(alert: Dict):

    if not isinstance(alert, dict):
        return {}

    return {

        "id": alert.get("id", ""),

        "time": (
            alert.get("time")
            or alert.get("timestamp")
            or ""
        ),

        "tool_id": (
            alert.get("tool_id")
            or alert.get("id")
            or ""
        ),

        "machine": alert.get("machine", ""),

        "alert_type": (
            alert.get("alert_type")
            or alert.get("type")
            or ""
        ),

        "level": LEVEL_MAP.get(
            alert.get("level"),
            alert.get("level", "info")
        ),

        "description": (
            alert.get("description")
            or alert.get("message")
            or ""
        ),

        "handle_status": HANDLE_STATUS_MAP.get(
            alert.get("handle_status"),
            alert.get(
                "handle_status",
                "unprocessed"
            )
        )
    }