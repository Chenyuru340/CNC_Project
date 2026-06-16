import requests
from typing import Dict
import config
from data.mock_data import generate_mock_data
import pandas as pd
from datetime import datetime

BASE_URL = config.BASE_URL
_mock_data_cache = None

TOOL_STATUS_TO_API = {"normal": "正常", "warning": "预警", "danger": "危险"}
ALERT_LEVEL_TO_API = {"danger": "危险", "warning": "警告", "info": "信息"}
ALERT_STATUS_TO_API = {"unprocessed": "未处理", "processing": "处理中", "processed": "已处理"}
TOOL_STATUS_FROM_API = {
    "正常": "normal",
    "健康": "normal",
    "normal": "normal",
    "轻度磨损": "warning",
    "轻微磨损": "warning",
    "预警": "warning",
    "warning": "warning",
    "中度磨损": "danger",
    "重度磨损": "danger",
    "严重磨损": "danger",
    "危险": "danger",
    "danger": "danger",
}

def normalize_alert(alert: Dict) -> Dict:
    level_map = {"危险": "danger", "警告": "warning", "预警": "warning", "信息": "info"}
    status_map = {"未处理": "unprocessed", "处理中": "processing", "已处理": "processed"}
    alert["level"] = level_map.get(alert.get("level"), alert.get("level"))
    alert["handle_status"] = status_map.get(alert.get("handle_status"), alert.get("handle_status"))
    return alert

def normalize_tool(tool: Dict):
    if not isinstance(tool, dict):
        return {}
    health_score = safe_float(
        tool.get("health_score", tool.get("health", tool.get("score", 0)))
    )
    status = TOOL_STATUS_FROM_API.get(tool.get("status"))
    if status is None:
        status = infer_status_from_health(health_score)
    return {
        "tool_id": tool.get("tool_id") or tool.get("id") or tool.get("name") or "",
        "name": tool.get("name", ""),
        "machine": tool.get("machine") or tool.get("machine_id") or "",
        "type": tool.get("type") or "铣刀",
        "vibration": safe_float(tool.get("vibration", tool.get("vib_spindle", 0))),
        "current": safe_float(tool.get("current", tool.get("smcAC", 0))),
        "vb": safe_float(tool.get("vb", tool.get("VB", 0))),
        "health_score": health_score,
        "status": status,
        "raw_status": tool.get("raw_status") or tool.get("status", ""),
        "current_usage": safe_float(tool.get("current_usage", 0)),
        "rul": safe_float(tool.get("rul", 0))
    }

def safe_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default

def infer_status_from_health(health_score):
    if health_score >= 80:
        return "normal"
    if health_score >= 50:
        return "warning"
    return "danger"

def build_aggregates_from_tools(tools):
    tools = [normalize_tool(t) for t in tools if isinstance(t, dict)]
    total_tools = len(tools)
    warning_tools = len([t for t in tools if t.get("status") == "warning"])
    danger_tools = len([t for t in tools if t.get("status") == "danger"])
    avg_health = 0
    avg_rul = 0
    if tools:
        avg_health = round(sum(t.get("health_score", 0) for t in tools) / total_tools, 1)
        avg_rul = round(sum(t.get("rul", 0) for t in tools) / total_tools, 1)
    return {
        "total_tools": total_tools,
        "warning_tools": warning_tools,
        "danger_tools": danger_tools,
        "avg_health": avg_health,
        "avg_rul": avg_rul,
    }

def build_alerts_from_tools(tools):
    alerts = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for index, tool in enumerate([normalize_tool(t) for t in tools], start=1):
        # 尝试从后端获取真实健康度
        tid = tool.get("tool_id")
        if tid:
            try:
                pred = get_tool_predict(tid)
                if pred and pred.get("health") is not None:
                    tool["health_score"] = pred["health"]
            except Exception:
                pass  # 获取失败就保持原值，不影响其他刀具

        status = tool.get("status")
        if status == "normal":
            continue
        level = "danger" if status == "danger" else "warning"
        raw_status = tool.get("raw_status") or ("危险" if level == "danger" else "预警")
        alerts.append({
            "id": index,
            "time": now,
            "tool_id": tool.get("tool_id", ""),
            "machine": tool.get("machine", ""),
            "alert_type": "刀具磨损异常",
            "level": level,
            "description": f"刀具状态为{raw_status}，健康度 {tool.get('health_score', 0):.2f} 分",
            "handle_status": "unprocessed",
        })
    return alerts

def get_mock_data():
    global _mock_data_cache
    if _mock_data_cache is None:
        _mock_data_cache = generate_mock_data()
    return _mock_data_cache

def _request(method: str, endpoint: str, params=None, json_data=None):
    url = f"{BASE_URL}{endpoint}"
    headers = {}
    if method in ("POST", "DELETE"):
        headers = {"Content-Type": "application/json"}

    if params:
        params = {k: v for k, v in params.items() if v is not None}

    try:
        if method == "GET":
            resp = requests.get(url, params=params, headers=headers, timeout=30)
        elif method == "POST":
            resp = requests.post(url, json=json_data, headers=headers, timeout=30)
        elif method == "DELETE":
            resp = requests.delete(url, headers=headers, timeout=30)
        else:
            raise ValueError("Unsupported method")

        resp.raise_for_status()
        try:
            body = resp.json()
        except Exception:
            print("接口返回非JSON格式数据")
            return None

        if isinstance(body, dict) and "code" in body and body["code"] == 500:
            print(f"接口业务错误: {body.get('message', '未知错误')}")
            return None

        return body

    except requests.Timeout:
        print(f"接口请求超时: {url}")
        return None
    except requests.ConnectionError:
        print(f"后端连接失败: {url}")
        return None
    except requests.HTTPError as e:
        print(f"HTTP异常 {e.response.status_code}: {url}")
        return None
    except Exception as e:
        print(f"接口未知异常: {str(e)}")
        return None

# GET /api/tools
def get_tools(status=None, machine=None, sort_by="health_score", order="desc", page=1, page_size=20):
    if config.USE_MOCK:
        data = get_mock_data()
        tools = data["tools"].to_dict("records")
        if status:
            tools = [t for t in tools if t["status"] == status]
        if machine:
            tools = [t for t in tools if t["machine"] == machine]
        tools.sort(key=lambda x: x.get(sort_by, 0), reverse=(order == "desc"))
        start = (page - 1) * page_size
        end = start + page_size
        return tools[start:end]
    res = _request("GET", "/api/tools", params={
        "status": TOOL_STATUS_TO_API.get(status, status), "machine": machine,
        "sort_by": sort_by, "order": order,
        "page": page, "page_size": page_size
    })
    if not res or not isinstance(res, list):
        return []
    tools = [normalize_tool(t) for t in res]
    if status:
        tools = [t for t in tools if t.get("status") == status]
    if machine:
        tools = [t for t in tools if t.get("machine") == machine]
    return tools

# GET /api/tools/aggregates （健壮性增强）
def get_aggregates():
    if config.USE_MOCK:
        data = get_mock_data()
        df = data["tools"]
        warning_count = len(df[df["status"] == "warning"])
        danger_count = len(df[df["status"] == "danger"])
        return {
            "total_tools": len(df),
            "warning_tools": warning_count,
            "danger_tools": danger_count,
            "avg_health": round(df["health_score"].mean(), 1),
            "avg_rul": round(df["rul"].mean(), 1)
        }
    res = _request("GET", "/api/tools/aggregates")
    # 健壮性校验：返回必须是dict且包含核心字段，否则自动降级
    if isinstance(res, dict) and "total_tools" in res and "avg_health" in res:
        return res
    # 降级：从刀具列表自行计算
    print("聚合接口无效，降级使用本地计算")
    tools = get_tools(page=1, page_size=1000)
    return build_aggregates_from_tools(tools)

# GET /api/features
def get_features(tool_id=None, days=30):
    if config.USE_MOCK:
        data = get_mock_data()
        df = data["features"]
        if tool_id:
            df = df[df["tool_id"] == tool_id]
        df = df.sort_values("timestamp")
        return [
            {"date": str(row["timestamp"]), "vibration": row.get("vibration", 0), "health_score": row.get("health_score", 0)}
            for _, row in df.iterrows()
        ]
    params = {"tool_id": tool_id, "days": days}
    return _request("GET", "/api/features", params=params) or []

# GET /api/alerts
def get_alerts(handle_status=None, level=None, page=1, page_size=20):
    if config.USE_MOCK:
        data = get_mock_data()
        alerts = data["alerts"].to_dict("records")
        if handle_status:
            alerts = [a for a in alerts if a["handle_status"] == handle_status]
        if level:
            alerts = [a for a in alerts if a["level"] == level]
        start = (page - 1) * page_size
        end = start + page_size
        return alerts[start:end]
    res = _request("GET", "/api/alerts", params={
        "handle_status": ALERT_STATUS_TO_API.get(handle_status, handle_status),
        "level": ALERT_LEVEL_TO_API.get(level, level),
        "page": page, "page_size": page_size
    })
    if isinstance(res, list):
        alerts = [normalize_alert(a) for a in res]
    else:
        tools = get_tools(page=1, page_size=1000)
        alerts = build_alerts_from_tools(tools)
    if handle_status:
        alerts = [a for a in alerts if a.get("handle_status") == handle_status]
    if level:
        alerts = [a for a in alerts if a.get("level") == level]
    start = (page - 1) * page_size
    end = start + page_size
    return alerts[start:end]

# GET /api/tools/{tool_id}
def get_tool_detail(tool_id):
    if config.USE_MOCK:
        data = get_mock_data()
        tool = data["tools"][data["tools"]["tool_id"] == tool_id]
        return tool.to_dict("records")[0] if not tool.empty else {}
    res = _request("GET", f"/api/tools/{tool_id}")
    return normalize_tool(res) if res else {}

def get_tool_by_id(tool_id):
    return get_tool_detail(tool_id)

# POST /api/tools
def add_tool(tool_data):
    """新增刀具，发送 tool_id, machine, type, manufacturer"""
    if config.USE_MOCK:
        data = get_mock_data()
        df = data["tools"]
        data["tools"] = pd.concat([df, pd.DataFrame([tool_data])], ignore_index=True)
        return tool_data

    payload = {
        "tool_id": tool_data.get("tool_id", ""),
        "machine": tool_data.get("machine", ""),
        "type": tool_data.get("type", "铣刀"),
        "manufacturer": tool_data.get("manufacturer", "")
    }
    res = _request("POST", "/api/tools", json_data=payload)
    return normalize_tool(res) if res else {}

# DELETE /api/tools/{tool_id}
def delete_tool(tool_id):
    if config.USE_MOCK:
        data = get_mock_data()
        data["tools"] = data["tools"][data["tools"]["tool_id"] != tool_id]
        return {"message": "删除成功"}
    res = _request("DELETE", f"/api/tools/{tool_id}")
    return res if res is not None else None

# GET /api/tools/{tool_id}/diagnosis
def get_tool_diagnosis(tool_id):
    if config.USE_MOCK:
        return {
            "tool_id": tool_id,
            "wear_rate": "48%",
            "maintenance_suggestion": "正常使用",
            "abnormal_info": "无异常"
        }
    return _request("GET", f"/api/tools/{tool_id}/diagnosis") or {}

# GET /api/tools/{tool_id}/spectrum
def get_spectrum(tool_id):
    if config.USE_MOCK:
        return {"frequencies": [], "amplitudes": []}
    res = _request("GET", f"/api/tools/{tool_id}/spectrum") or []
    return {
        "frequencies": [r["freq"] for r in res],
        "amplitudes": [r["amp"] for r in res]
    }

# GET /api/tools/{tool_id}/history
def get_tool_history(tool_id: str, start: str = "-30d"):
    """获取刀具历史健康数据
    :param tool_id: 刀具ID
    :param start: 起始时间，支持相对时间如 '-30d'，默认近30天
    """
    if config.USE_MOCK:
        data = get_mock_data()
        features = data["features"]
        tool_features = features[features["tool_id"] == tool_id].sort_values("timestamp")
        if not tool_features.empty:
            times = tool_features["timestamp"].tolist()
            hi_vals = (tool_features["health_score"] / 100).tolist()
            return {"time": times, "health": hi_vals, "hi": hi_vals, "rul": []}
        return {"time": [], "health": [], "hi": [], "rul": []}

    url = f"{BASE_URL}/api/tools/{tool_id}/history"
    try:
        resp = requests.get(url, params={"start": start}, timeout=60)
        resp.raise_for_status()
        res = resp.json()
    except Exception as e:
        print(f"历史接口请求失败: {e}")
        return {"time": [], "health": [], "hi": [], "rul": []}

    # 后面的解析逻辑不变（判断 res 包含 data）
    if isinstance(res, dict) and "data" in res:
        data = res["data"]
        times = [d.get("time", "") for d in data]
        health_vals = [d.get("health", 0) for d in data]
        hi_vals = [d.get("hi", 0) for d in data]
        rul_vals = [d.get("rul", 0) for d in data]
        return {
            "time": times,
            "health": health_vals,
            "hi": hi_vals,
            "rul": rul_vals
        }
    print(f"历史接口未返回有效数据: {res}")
    return {"time": [], "health": [], "hi": [], "rul": []}

# GET /api/tools/{tool_id}/vibration
def get_tool_vibration(tool_id: str, start_time: str = None, end_time: str = None):
    if config.USE_MOCK:
        return {"time": [], "vibration_x": [], "vibration_y": [], "vibration_z": []}
    params = {}
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time
    res = _request("GET", f"/api/tools/{tool_id}/vibration", params=params)
    if res and isinstance(res, dict):
        return res
    return {"time": [], "vibration_x": [], "vibration_y": [], "vibration_z": []}

# GET /api/tools/{tool_id}/features
def get_tool_features(tool_id: str):
    if config.USE_MOCK:
        return {"rms": [], "kurtosis": [], "mean": [], "variance": []}
    res = _request("GET", f"/api/tools/{tool_id}/features")
    if res and isinstance(res, dict):
        return res
    return {"rms": [], "kurtosis": [], "mean": [], "variance": []}

# POST /api/phm/agent
# POST /api/agent/chat （替换原来的 post_agent）
def post_agent(tool_id: str, message: str):
    """调用智能体聊天接口
    :param tool_id: 刀具ID或全局标识，例如 "global"
    :param message: 用户消息（已包含知识库上下文）
    :return: (reply_text, None)  第二个值固定为None，因为新接口不返回图表
    """
    if config.USE_MOCK:
        from utils.helpers import agent_response
        # 模拟调用，保持兼容
        return agent_response(message, None)

    url = f"{BASE_URL}/api/agent/chat"
    payload = {"message": message, "tool_id": tool_id}
    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        reply = result.get("reply", "")
        return reply, None
    except Exception as e:
        print(f"agent chat 错误: {e}")
        return "接口异常", None

# GET /api/settings
def get_settings():
    return _request("GET", "/api/settings") or {"refresh_interval": 30, "alert_threshold": 40}

# POST /api/settings
def save_settings(refresh_interval, alert_threshold):
    return _request("POST", "/api/settings", json_data={
        "refresh_interval": refresh_interval,
        "alert_threshold": alert_threshold
    }) or {}

# -------------------------- 4. 知识库接口（对齐最新后端 /api/docs） --------------------------
_mock_docs = [
    {
        "filename": "刀具磨损故障分析.md",
        "updated_at": "2026-05-14 10:00",
        "chunks": 18,
        "content": "# 刀具磨损故障分析\n\n## 故障特征\n\n- 振动增加\n- 切削力增大\n- 表面粗糙度恶化\n\n## 解决方案\n\n1. 调整切削参数\n2. 检查主轴\n3. 更换刀具\n"
    },
    {
        "filename": "PHM2010数据集使用指南.md",
        "updated_at": "2026-05-15 15:20",
        "chunks": 22,
        "content": "# PHM2010数据集\n\n包含：\n\n- 振动信号\n- 电流信号\n- 声发射信号\n"
    }
]

# GET /api/docs/search （返回格式未变）
def search_docs(query):
    if config.USE_MOCK:
        results = []
        for doc in _mock_docs:
            if query.lower() in doc["content"].lower():
                results.append({"filename": doc["filename"], "content": doc["content"][:1000]})
        if not results:
            results = [{"filename": doc["filename"], "content": doc["content"][:1000]} for doc in _mock_docs[:2]]
        return results

    res = _request("GET", "/api/docs/search", params={"q": query})
    if not res or not isinstance(res, dict):
        return []
    items = res.get("results", [])
    return [{"filename": r.get("filename", ""), "content": r.get("content", "")} for r in items]


# POST /api/docs/upload （不变）
def upload_doc(filename: str, file_content: bytes):
    """上传文件（任意格式），后端负责解析文本并入库"""
    if config.USE_MOCK:
        global _mock_docs
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        try:
            text = file_content.decode("utf-8", errors="ignore")[:2000]
        except:
            text = f"[二进制文件 {filename}]"
        for doc in _mock_docs:
            if doc["filename"] == filename:
                doc["content"] = text
                doc["updated_at"] = now
                return {"message": "保存成功"}
        _mock_docs.append({
            "filename": filename,
            "updated_at": now,
            "chunks": max(1, len(text) // 200),
            "content": text
        })
        return {"message": "上传成功"}

    url = f"{BASE_URL}/api/docs/upload"
    try:
        files = {"file": (filename, file_content)}
        resp = requests.post(url, files=files, timeout=30)
        resp.raise_for_status()
        try:
            return resp.json()
        except:
            return {"message": resp.text}
    except Exception as e:
        print(f"上传文档失败: {e}")
        return None


# GET /api/docs/list （适配新格式：{"documents":[...], "total":N}）
def get_docs_list():
    if config.USE_MOCK:
        return [
            {"filename": d["filename"], "chunks": d["chunks"]}
            for d in _mock_docs
        ]
    res = _request("GET", "/api/docs/list")
    if isinstance(res, dict) and "documents" in res:
        docs = res["documents"]
        # 提取前端需要的字段：filename, chunks（preview 暂不用）
        return [{"filename": d.get("filename", ""), "chunks": d.get("chunks", 0)} for d in docs]
    # 降级：如果后端返回格式异常或请求失败，使用 Mock
    print("文档列表接口返回格式异常，降级使用本地缓存")
    return [
        {"filename": d["filename"], "chunks": d["chunks"]}
        for d in _mock_docs
    ]


# GET /api/docs/detail （适配新格式：{filename, content, chunks}）
def get_doc_detail(filename):
    if config.USE_MOCK:
        for doc in _mock_docs:
            if doc["filename"] == filename:
                return {"filename": doc["filename"], "content": doc["content"]}
        return {"filename": "", "content": ""}
    res = _request("GET", "/api/docs/detail", params={"filename": filename})
    if isinstance(res, dict) and "content" in res:
        return {"filename": res.get("filename", filename), "content": res.get("content", "")}
    print("文档详情接口返回格式异常，尝试从缓存查找")
    for doc in _mock_docs:
        if doc["filename"] == filename:
            return {"filename": doc["filename"], "content": doc["content"]}
    return {"filename": filename, "content": ""}


# POST /api/docs/add （直接发送 JSON，不再中转 upload）
def add_doc(filename, content):
    """保存 Markdown 文本到知识库（新接口）"""
    if config.USE_MOCK:
        global _mock_docs
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        for doc in _mock_docs:
            if doc["filename"] == filename:
                doc["content"] = content
                doc["updated_at"] = now
                return {"status": "updated", "filename": filename}
        _mock_docs.append({
            "filename": filename,
            "updated_at": now,
            "chunks": max(1, len(content) // 200),
            "content": content
        })
        return {"status": "created", "filename": filename}

    payload = {"filename": filename, "content": content}
    res = _request("POST", "/api/docs/add", json_data=payload)
    if res and isinstance(res, dict) and "filename" in res:
        return res
    print("add_doc 失败")
    return None


# POST /api/docs/delete
def delete_doc(filename):
    if config.USE_MOCK:
        global _mock_docs
        _mock_docs = [d for d in _mock_docs if d["filename"] != filename]
        return {"status": "deleted", "filename": filename}
    res = _request("POST", "/api/docs/delete", json_data={"filename": filename})
    if res and isinstance(res, dict) and "filename" in res:
        return res
    print("delete_doc 失败")
    return None
# GET /api/tools/{tool_id}/predict  获取刀具预测数据（含 health, rul）
def get_tool_predict(tool_id: str):
    """调用 /api/tools/{tool_id}/predict 获取健康度和剩余寿命"""
    if config.USE_MOCK:
        # Mock 模式返回模拟数据
        return {"health": 50.0, "rul": 100.0}

    res = _request("GET", f"/api/tools/{tool_id}/predict")
    if res and isinstance(res, dict):
        return {
            "health": safe_float(res.get("health", 0)),
            "rul": safe_float(res.get("rul", 0))
        }
    return None
def get_monitoring_status():
    aggregates = get_aggregates()
    alerts = get_alerts(handle_status="unprocessed", page=1, page_size=100)
    aggregates["unprocessed_alerts"] = len(alerts) if alerts else 0
    return aggregates