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
                    html.I(
                        className=f"fas fa-{icon} fa-2x text-{color}"
                    ),
                    className="ms-auto"
                )
            ], className="d-flex align-items-center")
        ]),
        className="shadow-sm h-100"
    )


# =========================
# LED颜色
# =========================
def get_health_led(health_score):
    try:
        health_score = float(health_score)
    except Exception:
        health_score = 0

    if health_score >= 80:
        return "led-green"
    elif health_score >= 60:
        return "led-yellow"
    elif health_score >= 40:
        return "led-orange"
    else:
        return "led-red"


# =========================
# 卡片边框颜色
# =========================
def get_card_border_class(health_score):
    try:
        health_score = float(health_score)
    except Exception:
        health_score = 0

    if health_score >= 80:
        return ""
    elif health_score >= 60:
        return "tool-card-warning"
    elif health_score >= 40:
        return "tool-card-orange"
    else:
        return "tool-card-danger"


# =========================
# 状态配置
# =========================
def get_status_config(health):
    try:
        health = float(health)
    except Exception:
        health = 0

    if health >= 80:
        return "健康", "success"
    elif health >= 60:
        return "轻度磨损", "warning"
    elif health >= 40:
        return "中度磨损", "orange"
    else:
        return "重度磨损", "danger"


# =========================
# 完整刀具卡片
# =========================
def tool_card(tool):
    health = float(tool.get("health_score", 0))
    led_class = get_health_led(health)
    border_class = get_card_border_class(health)
    status_text, status_color = get_status_config(health)
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
                html.P(f"机床: {tool.get('machine', '-')}", className="mb-2 small", style={"fontFamily": "Microsoft YaHei"}),
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
def tool_card_simple(tool):
    health = float(tool.get("health_score", 0))
    status_text, status_color = get_status_config(health)
    rul = int(tool.get("rul", 0))

    if rul >= 60:
        rul_display = f"{rul // 60}小时{rul % 60}分"
    else:
        rul_display = f"{rul}分钟"

    return dbc.Col(
        dbc.Card([
            dbc.CardHeader([
                html.Strong(tool.get("tool_id", "未知刀具"), style={"fontFamily": "Microsoft YaHei"})
            ]),
            dbc.CardBody([
                dbc.Badge(status_text, color=status_color, className="mb-2"),
                html.P(f"机床：{tool.get('machine', '-')}", className="small mb-2", style={"fontFamily": "Microsoft YaHei"}),
                html.P(f"剩余寿命：{rul_display}", className="small mb-0", style={"fontFamily": "Microsoft YaHei"})
            ])
        ], className="shadow-sm h-100"),
        width=3,
        className="mb-4"
    )