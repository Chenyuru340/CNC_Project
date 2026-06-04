import dash_bootstrap_components as dbc
from dash import html

def create_sidebar(alert_count: int = 0):
    # 报警中心标题 + 角标
    alerts_children = [html.I(className="fas fa-bell me-2"), "报警中心"]
    if alert_count > 0:
        alerts_children.append(
            dbc.Badge(alert_count, color="danger", className="ms-2")
        )

    nav_links = [
        dbc.NavLink(
            [html.I(className="fas fa-chart-pie me-2"), "刀具健康总览"],
            href="/",
            active="exact",
            className="py-3 text-light"
        ),
        dbc.NavLink(
            [html.I(className="fas fa-eye me-2"), "状态监测"],
            href="/monitoring",
            active="exact",
            className="py-3 text-light"
        ),
        dbc.NavLink(
            alerts_children,
            href="/alerts",
            active="exact",
            className="py-3 text-light"
        ),
        dbc.NavLink(
            [html.I(className="fas fa-microchip me-2"), "PHM智能体"],
            href="/phm-agent",
            active="exact",
            className="py-3 text-light"
        ),
        dbc.NavLink(
            [html.I(className="fas fa-stethoscope me-2"), "故障诊断"],
            href="/fault-diagnosis",
            active="exact",
            className="py-3 text-light"
        ),
        dbc.NavLink(
            [html.I(className="fas fa-book me-2"), "知识库管理"],
            href="/knowledge-base",
            active="exact",
            className="py-3 text-light"
        ),
        dbc.NavLink(
            [html.I(className="fas fa-tools me-2"), "刀具管理"],
            href="/tools",
            active="exact",
            className="py-3 text-light"
        ),
        dbc.NavLink(
            [html.I(className="fas fa-cog me-2"), "系统设置"],
            href="/settings",
            active="exact",
            className="py-3 text-light"
        ),
    ]

    return html.Div(
        [
            html.H3("⚙️ PHM 系统", className="display-6 text-center mb-4 text-neon"),
            html.Hr(className="bg-neon"),
            dbc.Nav(nav_links, vertical=True, pills=True),
        ],
        id="sidebar",
        style={
            "position": "fixed",
            "top": 0,
            "left": 0,
            "bottom": 0,
            "width": "250px",
            "padding": "20px",
            "overflowY": "auto",
            "background": "linear-gradient(180deg, #0a0f1a 0%, #121826 100%)",
            "borderRight": "1px solid #2a3a5c",
            "boxShadow": "4px 0 20px rgba(0,0,0,0.5)",
            "color": "white",
        }
    )