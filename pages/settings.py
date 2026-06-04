# pages/settings.py
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
from api_client import get_settings, save_settings

def create_settings_page():
    return html.Div([
        html.H2("系统设置", className="mb-4"),
        dbc.Card([
            dbc.CardHeader("通用设置"),
            dbc.CardBody([
                dbc.Form([
                    dbc.Label("数据刷新间隔（秒）"),
                    dbc.Input(id="refresh-interval", type="number", value=30),
                    dbc.Label("报警阈值（健康度低于）"),
                    dbc.Input(id="alert-threshold", type="number", value=40),
                    dbc.Button("保存", id="save-settings", color="primary", className="mt-3"),
                    html.Div(id="settings-message", className="mt-2")
                ])
            ])
        ])
    ])

def register_settings_callbacks(app):
    # 页面加载时自动获取当前设置
    @app.callback(
        Output("refresh-interval", "value"),
        Output("alert-threshold", "value"),
        Input("url", "pathname")
    )
    def load_settings(pathname):
        if pathname == "/settings":
            settings = get_settings()  # 返回 {"refresh_interval": 30, "alert_threshold": 40}
            interval = settings.get("refresh_interval", 30)
            threshold = settings.get("alert_threshold", 40)
            return interval, threshold
        return 30, 40  # fallback

    # 保存设置
    @app.callback(
        Output("settings-message", "children"),
        Input("save-settings", "n_clicks"),
        State("refresh-interval", "value"),
        State("alert-threshold", "value"),
        prevent_initial_call=True
    )
    def save_settings_callback(n_clicks, interval, threshold):
        if n_clicks:
            try:
                result = save_settings(interval, threshold)
                if result:
                    return dbc.Alert("设置已保存", color="success", dismissable=True)
                else:
                    return dbc.Alert("保存失败，请检查后端连接", color="danger", dismissable=True)
            except Exception as e:
                return dbc.Alert(f"保存出错: {str(e)}", color="danger", dismissable=True)
        return ""