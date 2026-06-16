# app.py

import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc

from components.sidebar import create_sidebar

from pages import (
    dashboard,
    alerts,
    tools_management,
    settings,
    monitoring,
    phm_agent,
    knowledge_base,
    fault_diagnosis
)

from api_client import get_alerts

import traceback
import sys

# =========================
# 全局异常打印
# =========================
def excepthook(exc_type, exc_value, exc_tb):
    traceback.print_exception(exc_type, exc_value, exc_tb)

sys.excepthook = excepthook

# =========================
# Dash App
# =========================
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.CYBORG,
        dbc.icons.FONT_AWESOME
    ],
    suppress_callback_exceptions=True
)

app.title = "数控机床刀具预测性维护系统"
server = app.server

# =========================
# 获取报警数量（用于侧边栏角标）
# =========================
def get_alert_count():
    try:
        alerts_data = get_alerts(page=1, page_size=50)
        if not alerts_data:
            return 0
        return len([
            a for a in alerts_data
            if a.get("handle_status") == "unprocessed"
        ])
    except Exception:
        return 0

alert_count = get_alert_count()
sidebar = create_sidebar(alert_count)

# =========================
# 页面基础样式
# =========================
BASE_CONTENT_STYLE = {
    'marginLeft': '250px',
    'padding': '30px',
    'backgroundColor': '#0a0f1a',
    'minHeight': '100vh',
    'color': '#e0e0e0'
}

FULLSCREEN_STYLE = {
    'marginLeft': '0',
    'padding': '0',
    'backgroundColor': '#0a0f1a',
    'minHeight': '100vh',
    'color': '#e0e0e0'
}

HIDDEN_STYLE = {
    'display': 'none'
}

# =========================
# 预创建所有页面（秒开优化）
# =========================
dashboard_page = dashboard.create_dashboard()
alerts_page = alerts.create_alerts_page()
tools_page = tools_management.create_tools_page()
settings_page = settings.create_settings_page()
monitoring_page = monitoring.create_monitoring_page()
phm_page = phm_agent.create_phm_agent_page()
knowledge_page = knowledge_base.create_knowledge_base_page()
fault_page = fault_diagnosis.create_fault_diagnosis_page()

# =========================
# App Layout
# =========================
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    sidebar,
    # 页面容器（所有页面预先渲染，通过样式控制显示/隐藏）
    dcc.Store(id="global-settings-store", data={"refresh_interval": 30, "alert_threshold": 40}),
    html.Div([

        html.Div(
            dashboard_page,
            id='dashboard-page'
        ),

        html.Div(
            alerts_page,
            id='alerts-page',
            style=HIDDEN_STYLE
        ),

        html.Div(
            tools_page,
            id='tools-page',
            style=HIDDEN_STYLE
        ),

        html.Div(
            settings_page,
            id='settings-page',
            style=HIDDEN_STYLE
        ),

        html.Div(
            monitoring_page,
            id='monitoring-page',
            style=HIDDEN_STYLE
        ),

        html.Div(
            phm_page,
            id='phm-page',
            style=HIDDEN_STYLE
        ),

        html.Div(
            knowledge_page,
            id='knowledge-page',
            style=HIDDEN_STYLE
        ),

        html.Div(
            fault_page,
            id='fault-page',
            style=HIDDEN_STYLE
        )

    ], id='main-content')

])

# =========================
# 页面切换回调（核心：秒切换 + 隐藏侧边栏）
# =========================
@app.callback(

    [
        Output('dashboard-page', 'style'),
        Output('alerts-page', 'style'),
        Output('tools-page', 'style'),
        Output('settings-page', 'style'),
        Output('monitoring-page', 'style'),
        Output('phm-page', 'style'),
        Output('knowledge-page', 'style'),
        Output('fault-page', 'style'),
        Output('sidebar', 'style')
    ],

    Input('url', 'pathname')

)
def switch_page(pathname):

    hidden = {'display': 'none'}
    normal = BASE_CONTENT_STYLE
    fullscreen = FULLSCREEN_STYLE

    sidebar_show = {
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
        "color": "white"
    }

    sidebar_hide = {'display': 'none'}

    # 默认所有页面隐藏
    styles = [hidden] * 8   # 8个页面

    # 路由匹配
    if pathname == '/':
        styles[0] = normal          # dashboard
        return (*styles, sidebar_show)

    elif pathname == '/alerts':
        styles[1] = normal
    elif pathname == '/tools':
        styles[2] = normal
    elif pathname == '/settings':
        styles[3] = normal
    elif pathname == '/monitoring':
        styles[4] = normal
    elif pathname == '/phm-agent':
        styles[5] = fullscreen      # 全屏，隐藏侧边栏
        return (*styles, sidebar_hide)
    elif pathname == '/knowledge-base':
        styles[6] = normal
    elif pathname == '/fault-diagnosis':
        styles[7] = normal
    else:
        # 未知路径默认显示仪表盘
        styles[0] = normal

    return (*styles, sidebar_show)

# =========================
# 注册所有页面的回调
# =========================
monitoring.register_monitoring_callbacks(app)
settings.register_settings_callbacks(app)
alerts.register_alerts_callbacks(app)
tools_management.register_tools_callbacks(app)
dashboard.register_dashboard_callbacks(app)
phm_agent.register_phm_agent_callbacks(app)
knowledge_base.register_knowledge_base_callbacks(app)
fault_diagnosis.register_fault_diagnosis_callbacks(app)

# =========================
# 启动应用
# =========================
if __name__ == '__main__':
    try:
        app.run(
            debug=False,
            host='0.0.0.0',
            port=8050
        )
    except Exception:
        traceback.print_exc()