# api_client.py
import requests
from typing import Optional, Dict
import config
from data.mock_data import generate_mock_data
import pandas as pd
from datetime import datetime

BASE_URL = config.BASE_URL

_mock_data_cache = None

def normalize_alert(alert: Dict) -> Dict:
    level_map = {"危险": "danger", "预警": "warning", "信息": "info"}
    status_map = {"未处理": "unprocessed", "处理中": "processing", "已处理": "processed"}
    alert["level"] = level_map.get(alert.get("level"), alert.get("level"))
    alert["handle_status"] = status_map.get(alert.get("handle_status"), alert.get("handle_status"))
    return alert

def get_mock_data():
    global _mock_data_cache
    if _mock_data_cache is None:
        _mock_data_cache = generate_mock_data()
    return _mock_data_cache

def _request(method: str, endpoint: str, params=None, json_data=None):
    url = f"{BASE_URL}{endpoint}"
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
            print("返回结果不是 JSON")
            return None

        # 后端业务错误
        if isinstance(body, dict) and "code" in body and body["code"] != 200:
            print(f"API error: {body.get('message', 'unknown')}")
            return None

        # 响应结构统一适配
        if isinstance(body, dict):
            if "data" in body:
                return body["data"]
            if "items" in body:
                return body["items"]
        return body

    except requests.Timeout:
        print("接口超时")
        return None
    except requests.ConnectionError:
        print("后端连接失败")
        return None
    except Exception as e:
        print(f"接口错误: {e}")
        return None

def normalize_tool(tool: Dict):
    status_map = {"正常": "normal", "预警": "warning", "危险": "danger"}
    return {
        "tool_id": tool.get("tool_id") or tool.get("id"),
        "machine": tool.get("machine", ""),
        "type": tool.get("type", ""),
        "vibration": float(tool.get("vibration", 0) or 0),
        "health_score": float(tool.get("health_score", 0) or 0),
        "status": status_map.get(tool.get("status"), tool.get("status", "normal")),
        "current_usage": float(tool.get("current_usage", 0) or 0),
        "rul": float(tool.get("rul", 0) or 0)
    }

# =========================================================
# 1. 刀具列表
# =========================================================
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
        "status": status, "machine": machine,
        "sort_by": sort_by, "order": order,
        "page": page, "page_size": page_size
    })
    if not res:
        return []
    if not isinstance(res, list):
        return []
    return [normalize_tool(t) for t in res]

# =========================================================
# 2. 聚合统计
# =========================================================
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
    return _request("GET", "/api/tools/aggregates") or {}

# =========================================================
# 3. 特征曲线（保留原有接口）
# =========================================================
def get_features(tool_id=None, days=30, features=None):
    if config.USE_MOCK:
        data = get_mock_data()
        df = data["features"]
        if tool_id:
            df = df[df["tool_id"] == tool_id]
        df = df.sort_values("timestamp")
        return [{"date": str(row["timestamp"]), "health_score": row.get("health_score", 0),
                 "vibration": row.get("vibration", 0)} for _, row in df.iterrows()]
    params = {"tool_id": tool_id, "days": days}
    return _request("GET", "/api/features", params=params) or []

# =========================================================
# 4. 报警
# =========================================================
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
        "handle_status": handle_status, "level": level,
        "page": page, "page_size": page_size
    })
    if res:
        if not isinstance(res, list):
            return []
        return [normalize_alert(a) for a in res]
    return []

# =========================================================
# 5. 刀具详情
# =========================================================
def get_tool_detail(tool_id):
    if config.USE_MOCK:
        data = get_mock_data()
        tool = data["tools"][data["tools"]["tool_id"] == tool_id]
        return tool.to_dict("records")[0] if not tool.empty else {}
    res = _request("GET", f"/api/tools/{tool_id}")
    return normalize_tool(res) if res else {}

def get_tool_by_id(tool_id):
    return get_tool_detail(tool_id)

# =========================================================
# 6. 新增刀具
# =========================================================
def add_tool(tool_data):
    if config.USE_MOCK:
        data = get_mock_data()
        df = data["tools"]
        data["tools"] = pd.concat([df, pd.DataFrame([tool_data])], ignore_index=True)
        return tool_data
    res = _request("POST", "/api/tools", json_data={"tool_id": tool_data.get("tool_id"),
                                                    "machine": tool_data.get("machine")})
    return normalize_tool(res) if res else {}

# =========================================================
# 7. 删除刀具
# =========================================================
def delete_tool(tool_id):
    if config.USE_MOCK:
        data = get_mock_data()
        data["tools"] = data["tools"][data["tools"]["tool_id"] != tool_id]
        return {"message": "删除成功"}
    res = _request("DELETE", f"/api/tools/{tool_id}")
    return res if res else {"message": "删除失败"}

# =========================================================
# 8. 刀具诊断
# =========================================================
def get_tool_diagnosis(tool_id):
    if config.USE_MOCK:
        return {"tool_id": tool_id, "wear_rate": "48%",
                "maintenance_suggestion": "正常使用", "abnormal_info": "无异常"}
    return _request("GET", f"/api/tools/{tool_id}/diagnosis") or {}

# =========================================================
# 9. PHM 智能体
# =========================================================
def post_agent(tool_id, question, file_info=None):
    if config.USE_MOCK:
        from utils.helpers import agent_response
        return agent_response(question, file_info)
    url = f"{BASE_URL}/api/phm/agent"
    headers = {"Content-Type": "application/json"}
    data = {"tool_id": tool_id, "question": question}
    files = None
    if file_info and file_info.get("content"):
        files = {"file": (file_info["filename"], file_info["content"])}
        resp = requests.post(url, data=data, files=files, timeout=30)
    else:
        resp = requests.post(url, json=data, headers=headers, timeout=30)
    try:
        resp.raise_for_status()
        result = resp.json()
        return result.get("answer", ""), result.get("figure", None)
    except Exception as e:
        print(f"post_agent 错误: {e}")
        return "接口异常", None

# =========================================================
# 10. 频谱
# =========================================================
def get_spectrum(tool_id):
    if config.USE_MOCK:
        return {"frequencies": [], "amplitudes": []}
    res = _request("GET", f"/api/tools/{tool_id}/spectrum") or []
    return {"frequencies": [r["freq"] for r in res], "amplitudes": [r["amp"] for r in res]}

# =========================================================
# 11. 系统设置
# =========================================================
def get_settings():
    return _request("GET", "/api/settings") or {"refresh_interval": 30, "alert_threshold": 40}

def save_settings(refresh_interval, alert_threshold):
    return _request("POST", "/api/settings", json_data={
        "refresh_interval": refresh_interval, "alert_threshold": alert_threshold
    }) or {}

# =========================================================
# 12. 知识库
# =========================================================
_mock_docs = [
    {"filename": "刀具磨损故障分析.md", "updated_at": "2026-05-14 10:00",
     "chunks": 18, "content": "# 刀具磨损故障分析\n\n## 故障特征\n\n- 振动增加\n- 切削力增大\n- 表面粗糙度恶化\n\n## 解决方案\n\n1. 调整切削参数\n2. 检查主轴\n3. 更换刀具\n"},
    {"filename": "PHM2010数据集使用指南.md", "updated_at": "2026-05-14 15:20",
     "chunks": 22, "content": "# PHM2010数据集\n\n包含：\n\n- 振动信号\n- 电流信号\n- 声发射信号\n"}
]

def search_docs(query):
    if config.USE_MOCK:
        results = []
        for doc in _mock_docs:
            if query.lower() in doc["content"].lower():
                results.append({"filename": doc["filename"], "content": doc["content"][:1000]})
        if not results:
            results = [{"filename": doc["filename"], "content": doc["content"][:1000]} for doc in _mock_docs[:2]]
        return results
    res = _request("GET", "/api/docs/search", params={"q": query, "top_k": 5}) or []
    if res:
        return [{"filename": r.get("filename", ""), "content": r.get("snippet", "")} for r in res]
    return []

def get_docs_list():
    if config.USE_MOCK:
        return [{"filename": doc["filename"], "updated_at": doc["updated_at"],
                 "chunks": doc["chunks"]} for doc in _mock_docs]
    res = _request("GET", "/api/docs/list") or []
    return [{"filename": r.get("filename", ""), "size": r.get("size", 0),
             "updated_at": r.get("updated_at", "")} for r in res]

def get_doc_detail(filename):
    if config.USE_MOCK:
        for doc in _mock_docs:
            if doc["filename"] == filename:
                return {"filename": doc["filename"], "content": doc["content"]}
        return {"filename": "", "content": ""}
    res = _request("GET", "/api/docs/detail", params={"filename": filename})
    return {"filename": res.get("filename", ""), "content": res.get("content", "")} if res else {"filename": "", "content": ""}

def add_doc(filename, content):
    if config.USE_MOCK:
        global _mock_docs
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        found = False
        for doc in _mock_docs:
            if doc["filename"] == filename:
                doc["content"] = content
                doc["updated_at"] = now
                found = True
                break
        if not found:
            _mock_docs.append({"filename": filename, "updated_at": now,
                               "chunks": max(1, len(content) // 200), "content": content})
        return {"message": "保存成功"}
    return _request("POST", "/api/docs/add", json_data={"filename": filename, "content": content}) or {}

def delete_doc(filename):
    if config.USE_MOCK:
        global _mock_docs
        _mock_docs = [doc for doc in _mock_docs if doc["filename"] != filename]
        return {"message": "删除成功"}
    return _request("POST", "/api/docs/delete", json_data={"filename": filename}) or {}

# =========================================================
# 13. 故障诊断
# =========================================================
def post_diagnosis_analysis(file_base64, filename, channel, analysis_type, params):
    if config.USE_MOCK:
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_annotation(text="模拟分析结果（请关闭 USE_MOCK 以调用真实接口）", x=0.5, y=0.5, showarrow=False)
        return {"figure": fig.to_dict()}
    url = f"{BASE_URL}/api/diagnosis/analyze"
    try:
        resp = requests.post(url, json={
            "file_base64": file_base64, "filename": filename,
            "channel": channel, "analysis_type": analysis_type, "params": params
        }, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"故障诊断接口错误: {e}")
        return {"error": str(e)}

def get_monitoring_status():
    aggregates = get_aggregates()
    alerts = get_alerts(handle_status="unprocessed", page=1, page_size=100)
    aggregates["unprocessed_alerts"] = len(alerts) if alerts else 0
    return aggregates

# =========================================================
# 14. 刀具历史健康指标（新增）
# =========================================================
def get_tool_history(tool_id: str, days: int = 30):
    """
    获取刀具历史健康指标（时间, HI）
    返回格式: {"time": [日期字符串列表], "hi": [健康指标数值列表]}
    """
    if config.USE_MOCK:
        data = get_mock_data()
        features = data["features"]
        tool_features = features[features["tool_id"] == tool_id].sort_values("timestamp")
        if not tool_features.empty:
            times = tool_features["timestamp"].tolist()
            # 模拟 HI = health_score / 100（范围 0~1）
            hi_vals = (tool_features["health_score"] / 100).tolist()
            return {"time": times, "hi": hi_vals}
        else:
            return {"time": [], "hi": []}
    else:
        # 真实后端接口
        res = _request("GET", f"/api/tools/{tool_id}/history", params={"days": days})
        if res and isinstance(res, dict):
            return {"time": res.get("time", []), "hi": res.get("hi", [])}
        # 如果后端未实现该接口，可以回退到 get_features 临时处理
        # 但这里直接返回空
        return {"time": [], "hi": []}