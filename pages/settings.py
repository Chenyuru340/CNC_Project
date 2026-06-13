# pages/settings.py
from dash import html, dcc, Input, Output, State, callback, no_update
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
                    dbc.Label("报警阈值（健康度低于此值将预警）"),
                    dbc.Input(id="alert-threshold", type="number", value=40),
                    dbc.Button("保存", id="save-settings", color="primary", className="mt-3"),
                    html.Div(id="settings-message", className="mt-2")
                ])
            ])
        ])
    ])

def register_settings_callbacks(app):
    # 从全局 Store 加载当前设置到输入框
    @app.callback(
        Output("refresh-interval", "value"),
        Output("alert-threshold", "value"),
        Input("url", "pathname"),
        State("global-settings-store", "data"),
        prevent_initial_call=False
    )
    def load_settings(pathname, settings):
        if pathname == "/settings" and settings:
            return settings.get("refresh_interval", 30), settings.get("alert_threshold", 40)
        return no_update, no_update

    # 保存设置：更新全局 Store，尝试后端保存
    @app.callback(
        Output("global-settings-store", "data"),
        Output("settings-message", "children"),
        Input("save-settings", "n_clicks"),
        State("refresh-interval", "value"),
        State("alert-threshold", "value"),
        State("global-settings-store", "data"),
        prevent_initial_call=True
    )
    def save_settings_callback(n_clicks, interval, threshold, current_settings):
        if not n_clicks:
            return no_update, no_update
        # 类型校验
        try:
            interval = int(interval)
            threshold = int(threshold)
        except:
            return no_update, dbc.Alert("请输入有效的数字", color="danger")
        new_settings = {"refresh_interval": interval, "alert_threshold": threshold}
        # 尝试保存到后端（静默处理，不影响前端）
        try:
            save_settings(interval, threshold)
        except:
            pass
        return new_settings, dbc.Alert("设置已保存并生效", color="success", dismissable=True)