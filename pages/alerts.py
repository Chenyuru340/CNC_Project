# pages/alerts.py
import dash_bootstrap_components as dbc
from api_client import get_alerts, get_mock_data, get_tools
from utils.data_adapter import normalize_tool
import pandas as pd
from dash import html, dcc, dash_table, Input, Output, State, callback, no_update
import config

# ========== 公共函数：获取预警/危险刀具的报警列表 ==========
def get_filtered_alerts(limit=None):
    """返回过滤后的报警DataFrame，仅包含当前状态为预警或危险的刀具的报警"""
    # 1. 获取所有刀具，找出预警/危险刀具ID
    tools_data = get_tools(page=1, page_size=500)
    tools = [normalize_tool(t) for t in tools_data] if tools_data else []
    tools_df = pd.DataFrame(tools)
    if tools_df.empty and config.USE_MOCK:
        data = get_mock_data()
        tools_df = data["tools"].copy()
    if tools_df.empty:
        return pd.DataFrame()
    warning_danger_tools = tools_df[tools_df['status'].isin(['warning', 'danger'])]['tool_id'].tolist()

    # 2. 获取所有报警（如果后端没有实现，get_alerts 会返回空列表）
    alerts = get_alerts(page=1, page_size=500)
    alerts_df = pd.DataFrame(alerts) if alerts else pd.DataFrame()
    # 如果真实报警为空且处于 Mock 模式，则使用 Mock 数据
    if alerts_df.empty and config.USE_MOCK:
        data = get_mock_data()
        alerts_df = data["alerts"].copy()
    if alerts_df.empty:
        return pd.DataFrame()

    # 3. 过滤
    alerts_df = alerts_df[alerts_df['tool_id'].isin(warning_danger_tools)]

    # 4. 映射中英文（如果列中存在中文字段则映射为前端需要的英文值）
    if not alerts_df.empty:
        # level 映射
        if 'level' in alerts_df.columns:
            # 如果已经是英文则保持不变
            level_map = {"危险": "danger", "警告": "warning", "信息": "info"}
            alerts_df['level'] = alerts_df['level'].map(level_map).fillna(alerts_df['level'])
        # handle_status 映射
        if 'handle_status' in alerts_df.columns:
            status_map = {"未处理": "unprocessed", "处理中": "processing", "已处理": "processed"}
            alerts_df['handle_status'] = alerts_df['handle_status'].map(status_map).fillna(alerts_df['handle_status'])

    if limit:
        alerts_df = alerts_df.head(limit)
    return alerts_df

def create_alerts_page():
    return html.Div([
        html.H2("报警中心", className="mb-4"),
        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("处理状态"),
                        dbc.Select(
                            id="alert-handle-status",
                            options=[
                                {"label": "全部", "value": "all"},
                                {"label": "未处理", "value": "unprocessed"},
                                {"label": "处理中", "value": "processing"},
                                {"label": "已处理", "value": "processed"}
                            ],
                            value="all"
                        )
                    ], width=3),
                    dbc.Col([
                        html.Label("报警级别"),
                        dbc.Select(
                            id="alert-level",
                            options=[
                                {"label": "全部", "value": "all"},
                                {"label": "危险", "value": "danger"},
                                {"label": "预警", "value": "warning"},
                                {"label": "提示", "value": "info"}
                            ],
                            value="all"
                        )
                    ], width=3),
                    dbc.Col([
                        html.Label("开始时间"),
                        dcc.Input(id="alert-start-time", type="text", placeholder="yyyy-MM-dd HH:mm:ss")
                    ], width=3),
                    dbc.Col([
                        html.Label("结束时间"),
                        dcc.Input(id="alert-end-time", type="text", placeholder="yyyy-MM-dd HH:mm:ss")
                    ], width=3),
                ]),
                dbc.Row([
                    dbc.Col(dbc.Button("查询", id="alert-query", color="primary", className="mt-3"), width=2)
                ])
            ])
        ], className="mb-4"),
        dbc.Row(id="alert-stats", className="mb-4"),
        dbc.Spinner(html.Div(id="alert-table-container"))
    ])

def register_alerts_callbacks(app):
    def fetch_alerts(handle_status, level, start_time, end_time):
        alerts_df = get_filtered_alerts()  # 获取完整过滤数据
        if alerts_df.empty:
            return alerts_df

        # 时间列处理：确保为 datetime 类型
        if 'time' in alerts_df.columns:
            alerts_df['time'] = pd.to_datetime(alerts_df['time'], errors='coerce')
            # 应用时间筛选
            if start_time:
                start_dt = pd.to_datetime(start_time, errors='coerce')
                if start_dt:
                    alerts_df = alerts_df[alerts_df['time'] >= start_dt]
            if end_time:
                end_dt = pd.to_datetime(end_time, errors='coerce')
                if end_dt:
                    alerts_df = alerts_df[alerts_df['time'] <= end_dt]
            # 格式化回字符串用于显示
            alerts_df['time'] = alerts_df['time'].dt.strftime('%Y-%m-%d %H:%M:%S')
        # 应用其他筛选
        if handle_status != "all":
            alerts_df = alerts_df[alerts_df['handle_status'] == handle_status]
        if level != "all":
            alerts_df = alerts_df[alerts_df['level'] == level]

        return alerts_df

    def build_stats_and_table(alerts_df):
        required_columns = [
            'id', 'time', 'tool_id', 'machine', 'alert_type', 'level', 'description', 'handle_status'
        ]
        for col in required_columns:
            if col not in alerts_df.columns:
                alerts_df[col] = ""
        try:
            if alerts_df.empty:
                stats = dbc.Row([
                    dbc.Col(dbc.Card(dbc.CardBody([html.H4(0), html.P("危险报警")]), className="text-center"), width=3),
                    dbc.Col(dbc.Card(dbc.CardBody([html.H4(0), html.P("未处理")]), className="text-center"), width=3),
                ])
                table = dbc.Alert("暂无报警记录", color="info")
            else:
                danger_cnt = len(alerts_df[alerts_df['level'] == 'danger'])
                unprocessed_cnt = len(alerts_df[alerts_df['handle_status'] == 'unprocessed'])
                stats = dbc.Row([
                    dbc.Col(dbc.Card(dbc.CardBody([html.H4(danger_cnt, className="text-danger"), html.P("危险报警")]), className="text-center"), width=3),
                    dbc.Col(dbc.Card(dbc.CardBody([html.H4(unprocessed_cnt), html.P("未处理")]), className="text-center"), width=3),
                ])
                level_cn = {'danger': '危险', 'warning': '预警', 'info': '提示'}
                status_cn = {'unprocessed': '未处理', 'processing': '处理中', 'processed': '已处理'}
                alerts_df = alerts_df.copy()
                alerts_df['level_cn'] = alerts_df['level'].apply(lambda x: level_cn.get(x, x))
                alerts_df['handle_status_cn'] = alerts_df['handle_status'].apply(lambda x: status_cn.get(x, x))
                table = dash_table.DataTable(
                    data=alerts_df.to_dict('records'),
                    columns=[
                        {"name": "ID", "id": "id"},
                        {"name": "时间", "id": "time"},
                        {"name": "刀具ID", "id": "tool_id"},
                        {"name": "机床", "id": "machine"},
                        {"name": "报警类型", "id": "alert_type"},
                        {"name": "级别", "id": "level_cn"},
                        {"name": "描述", "id": "description"},
                        {"name": "处理状态", "id": "handle_status_cn"}
                    ],
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'left'},
                    filter_action='native',
                    sort_action='native',
                    page_size=10
                )
            return stats, table
        except Exception as e:
            error_alert = dbc.Alert(f"加载失败: {str(e)}", color="danger")
            empty_stats = dbc.Row([
                dbc.Col(dbc.Card(dbc.CardBody([html.H4(0), html.P("危险报警")]), className="text-center"), width=3),
                dbc.Col(dbc.Card(dbc.CardBody([html.H4(0), html.P("未处理")]), className="text-center"), width=3),
            ])
            return empty_stats, error_alert

    @app.callback(
        [Output("alert-stats", "children"),
         Output("alert-table-container", "children")],
        [Input("url", "pathname")]
    )
    def initial_load(pathname):
        if pathname == "/alerts":
            alerts_df = fetch_alerts("all", "all", None, None)
            return build_stats_and_table(alerts_df)
        return no_update, no_update

    @app.callback(
        [Output("alert-stats", "children", allow_duplicate=True),
         Output("alert-table-container", "children", allow_duplicate=True)],
        [Input("alert-query", "n_clicks")],
        [State("alert-handle-status", "value"),
         State("alert-level", "value"),
         State("alert-start-time", "value"),
         State("alert-end-time", "value")],
        prevent_initial_call=True
    )
    def query_alerts(n_clicks, handle_status, level, start_time, end_time):
        alerts_df = fetch_alerts(handle_status, level, start_time, end_time)
        return build_stats_and_table(alerts_df)