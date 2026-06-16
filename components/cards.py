import dash_bootstrap_components as dbc
from dash import html

# =========================
# 统计卡片
# =========================
def stat_card(title, value, icon, color):
    return dbc.Card(
        dbc.CardBody([
            html.Div([
                html.Div([
                    html.H6(title, className="text-muted mb-2", style={"fontFamily": "Microsoft YaHei"}),
                    html.H3(str(value), className="fw-bold mb-0", style={"fontFamily": "Microsoft YaHei"})
                ]),
                html.Div(
                    html.I(className=f"fas fa-{icon} fa-2x text-{color}"),
                    className="ms-auto"
                )
            ], className="d-flex align-items-center")
        ]),
        className="shadow-sm h-100"
    )

# =========================
# LED颜色
# =========================
def get_health_led(health_score, alert_threshold=40):
    try:
        health_score = float(health_score)
    except:
        health_score = 0
    if health_score >= 80:
        return "led-green"
    elif health_score >= alert_threshold + 10:
        return "led-yellow"
    elif health_score >= alert_threshold:
        return "led-orange"
    else:
        return "led-red"

# =========================
# 卡片边框颜色
# =========================
def get_card_border_class(health_score, alert_threshold=40):
    try:
        health_score = float(health_score)
    except:
        health_score = 0
    if health_score >= 80:
        return ""
    elif health_score >= alert_threshold + 10:
        return "tool-card-warning"
    elif health_score >= alert_threshold:
        return "tool-card-orange"
    else:
        return "tool-card-danger"

# =========================
# 状态配置
# =========================
def get_status_config(health, alert_threshold=40):
    try:
        health = float(health)
    except:
        health = 0
    if health >= 80:
        return "健康", "success"
    elif health >= alert_threshold + 10:
        return "轻度磨损", "warning"
    elif health >= alert_threshold:
        return "中度磨损", "orange"
    else:
        return "重度磨损", "danger"

# =========================
# 完整刀具卡片（保留原样，可能其他页面使用）
# =========================
def tool_card(tool, alert_threshold=40):
    health = float(tool.get("health_score", 0))
    led_class = get_health_led(health, alert_threshold)
    border_class = get_card_border_class(health, alert_threshold)
    status_text, status_color = get_status_config(health, alert_threshold)
    rul = int(tool.get("rul", 0))
    if rul >= 60:
        rul_display = f"{rul // 60}小时{rul % 60}分"
    else:
        rul_display = f"{rul}分钟"

    return dbc.Col(
        dbc.Card([
            dbc.CardHeader([
                html.Div([
                    html.Span(className=led_class),
                    html.Strong(tool.get("tool_id", "未知刀具"), className="me-2", style={"fontFamily": "Microsoft YaHei"}),
                    dbc.Badge(status_text, color=status_color, className="me-1"),
                    dbc.Badge(tool.get("type", "未知"), color="info")
                ], className="d-flex align-items-center")
            ]),
            dbc.CardBody([
                html.P(f"机床: {tool.get('machine') or '未知机床'}", className="mb-2 small", style={"fontFamily": "Microsoft YaHei"}),
                html.P(f"剩余寿命: {rul_display}", className="mb-2 small", style={"fontFamily": "Microsoft YaHei"}),
                html.Small(f"健康度: {health:.1f} 分", className="text-muted", style={"fontFamily": "Microsoft YaHei"})
            ])
        ], className=f"shadow-sm h-100 {border_class}"),
        width=3,
        className="mb-4"
    )

# =========================
# 精简刀具卡片（Dashboard 用）
# =========================
def tool_card_simple(tool, alert_threshold=40):
    health = float(tool.get("health_score", 0))
    border_class = get_card_border_class(health, alert_threshold)
    rul = int(tool.get("rul", 0))
    if rul >= 60:
        rul_display = f"{rul // 60}小时{rul % 60}分"
    else:
        rul_display = f"{rul}分钟"
    machine_display = tool.get("machine") or "未知机床"
    tool_type = tool.get("type") or "未知"

    return dbc.Col(
        dbc.Card([
            dbc.CardHeader([
                html.Strong(tool.get("tool_id", "未知刀具"), style={"fontFamily": "Microsoft YaHei"})
            ]),
            dbc.CardBody([
                html.P(f"机床：{machine_display}", className="small mb-2", style={"fontFamily": "Microsoft YaHei"}),
                html.P(f"类型：{tool_type}", className="small mb-2", style={"fontFamily": "Microsoft YaHei"}),
                html.P(f"健康度：{health:.1f} 分", className="small mb-2", style={"fontFamily": "Microsoft YaHei"}),
                html.P(f"剩余寿命：{rul_display}", className="small mb-0", style={"fontFamily": "Microsoft YaHei"})
            ])
        ], className=f"shadow-sm h-100 {border_class}"),
        width=3,
        className="mb-4"
    )