import dash_bootstrap_components as dbc
from api_client import get_alerts, get_mock_data, get_tools
import pandas as pd
from dash import html, dcc, dash_table, Input, Output, State, callback, no_update
import config

# ========== 公共函数：筛选预警/危险刀具对应的报警 ==========
def get_filtered_alerts():
    """
    获取报警数据，仅保留预警/危险刀具的报警
    注：后端/api/alerts接口无时间参数，时间筛选由前端本地完成
    """
    # 1. 获取所有刀具（分页拉取，当前限定最大500条）
    tools_data = get_tools(page=1, page_size=500)
    tools_df = pd.DataFrame(tools_data) if tools_data else pd.DataFrame()

    # Mock模式兜底数据
    if tools_df.empty and config.USE_MOCK:
        mock_data = get_mock_data()
        tools_df = mock_data["tools"].copy()
    if tools_df.empty:
        return pd.DataFrame()

    # 筛选预警、危险状态的刀具ID（api_client已完成中英文映射，使用英文状态值）
    warning_danger_ids = tools_df[tools_df['status'].isin(['warning', 'danger'])]['tool_id'].tolist()

    # 2. 获取全量报警数据
    alerts_data = get_alerts(page=1, page_size=500)
    alerts_df = pd.DataFrame(alerts_data) if alerts_data else pd.DataFrame()

    # Mock模式兜底数据
    if alerts_df.empty and config.USE_MOCK:
        mock_data = get_mock_data()
        alerts_df = mock_data["alerts"].copy()
    if alerts_df.empty:
        return pd.DataFrame()

    # 过滤：仅保留预警/危险刀具的报警
    alerts_df = alerts_df[alerts_df['tool_id'].isin(warning_danger_ids)]
    return alerts_df

def fetch_alerts(handle_status, level, start_time, end_time):
    """根据筛选条件过滤报警数据（时间筛选为前端本地实现）"""
    alerts_df = get_filtered_alerts()
    if alerts_df.empty:
        return alerts_df

    # 时间字段格式转换与筛选
    if 'time' in alerts_df.columns:
        alerts_df['time'] = pd.to_datetime(alerts_df['time'], errors='coerce')
        # 开始时间筛选
        if start_time:
            start_dt = pd.to_datetime(start_time, errors='coerce')
            if start_dt:
                alerts_df = alerts_df[alerts_df['time'] >= start_dt]
        # 结束时间筛选
        if end_time:
            end_dt = pd.to_datetime(end_time)
            if end_dt:
                alerts_df = alerts_df[alerts_df['time'] <= end_dt]
        # 转回字符串用于页面展示
        alerts_df['time'] = alerts_df['time'].dt.strftime('%Y-%m-%d %H:%M:%S')

    # 处理状态筛选
    if handle_status != "all":
        alerts_df = alerts_df[alerts_df['handle_status'] == handle_status]
    # 报警级别筛选
    if level != "all":
        alerts_df = alerts_df[alerts_df['level'] == level]

    return alerts_df

def build_stats_and_table(alerts_df):
    """组装统计卡片 + 报警表格，增加字段兜底与异常捕获"""
    required_cols = ['id', 'time', 'tool_id', 'machine', 'alert_type', 'level', 'description', 'handle_status']
    # 缺失字段填充空值，防止表格渲染报错
    for col in required_cols:
        if col not in alerts_df.columns:
            alerts_df[col] = ""

    try:
        if alerts_df.empty:
            stats = dbc.Row([
                dbc.Col(dbc.Card(dbc.CardBody([html.H4(0), html.P("危险报警")]), className="text-center"), width=3),
                dbc.Col(dbc.Card(dbc.CardBody([html.H4(0), html.P("未处理")]), className="text-center"), width=3),
            ])
            table = dbc.Alert("暂无报警记录", color="info")
            return stats, table

        # 统计危险报警、未处理报警数量
        danger_count = len(alerts_df[alerts_df['level'] == 'danger'])
        unprocessed_count = len(alerts_df[alerts_df['handle_status'] == 'unprocessed'])
        stats = dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([html.H4(danger_count, className="text-danger"), html.P("危险报警")]), className="text-center"), width=3),
            dbc.Col(dbc.Card(dbc.CardBody([html.H4(unprocessed_count), html.P("未处理")]), className="text-center"), width=3),
        ])

        # 前端展示：英文状态转回中文（筛选逻辑仍使用英文，与api_client保持一致）
        level_map = {'danger': '危险', 'warning': '预警', 'info': '提示'}
        status_map = {'unprocessed': '未处理', 'processing': '处理中', 'processed': '已处理'}
        alerts_df = alerts_df.copy()
        alerts_df['level_cn'] = alerts_df['level'].map(level_map)
        alerts_df['handle_status_cn'] = alerts_df['handle_status'].map(status_map)

        # 渲染数据表格
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
        error_msg = f"数据加载异常：{str(e)}"
        empty_stats = dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([html.H4(0), html.P("危险报警")]), className="text-center"), width=3),
            dbc.Col(dbc.Card(dbc.CardBody([html.H4(0), html.P("未处理")]), className="text-center"), width=3),
        ])
        error_table = dbc.Alert(error_msg, color="danger")
        return empty_stats, error_table

def create_alerts_page():
    """报警中心页面布局（补充url路由组件，修复初始化加载BUG）"""
    return html.Div([
        # 关键组件：路由监听，用于页面进入时自动加载数据
        dcc.Location(id="url", refresh=False),

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
    # 页面切换/进入时 自动加载数据
    @app.callback(
        [Output("alert-stats", "children"),
         Output("alert-table-container", "children")],
        [Input("url", "pathname")]
    )
    def initial_load(pathname):
        if pathname == "/alerts":
            df = fetch_alerts("all", "all", None, None)
            return build_stats_and_table(df)
        return no_update, no_update

    # 点击查询按钮 手动筛选数据
    @app.callback(
        [Output("alert-stats", "children", allow_duplicate=True),
         Output("alert-table-container", "children", allow_duplicate=True)],
        [Input("alert-query", "n_clicks")],
        [State("alert-handle-status", "value"),
         State("alert-level", "value"),
         State("alert-start-time", "value"),
         State("alert-end-time")],
        prevent_initial_call=True
    )
    def query_alerts(n_clicks, handle_status, level, start_time, end_time):
        df = fetch_alerts(handle_status, level, start_time, end_time)
        return build_stats_and_table(df)