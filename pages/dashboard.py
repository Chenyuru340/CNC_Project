# pages/dashboard.py
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
from components import cards, charts
from api_client import get_tools, get_aggregates, get_alerts, get_mock_data
import pandas as pd
from utils.data_adapter import normalize_tool
import config
from pages.alerts import get_filtered_alerts

COMMON_FONT = "Microsoft YaHei"

def create_dashboard():
    return html.Div([
        html.H2("刀具健康总览", className="mb-4", style={"fontFamily": COMMON_FONT}),
        dbc.Spinner(html.Div(id="dashboard-content"))
    ])

def register_dashboard_callbacks(app):
    @app.callback(
        Output("dashboard-content", "children"),
        Input("url", "pathname")
    )
    def load_dashboard(_):
        try:
            aggregates = get_aggregates()
            tools = get_tools(page=1, page_size=200)
            tools = [normalize_tool(t) for t in tools] if tools else []
            tools_df = pd.DataFrame(tools)
            if tools_df.empty and config.USE_MOCK:
                tools_df = get_mock_data()["tools"].copy()
            if tools_df.empty:
                return dbc.Alert("刀具数据为空", color="warning")
            # 统计卡片数据
            total = len(tools_df)
            healthy = len(tools_df[tools_df["status"] == "normal"])
            warning = len(tools_df[tools_df["status"] == "warning"])
            danger = len(tools_df[tools_df["status"] == "danger"])
            stats_row = dbc.Row([
                dbc.Col(cards.stat_card("在线刀具", total, "tools", "primary"), width=3),
                dbc.Col(cards.stat_card("健康刀具", healthy, "heartbeat", "success"), width=3),
                dbc.Col(cards.stat_card("预警刀具", warning, "exclamation-triangle", "warning"), width=3),
                dbc.Col(cards.stat_card("危险刀具", danger, "exclamation-circle", "danger"), width=3),
            ], className="mb-4")
            # 报警中心（前5条）
            filtered_alerts_df = get_filtered_alerts(limit=5)
            alerts = filtered_alerts_df.to_dict("records") if not filtered_alerts_df.empty else []
            LEVEL_TEXT_MAP = {"danger": "危险", "warning": "预警", "info": "提示"}
            alert_section = html.Div([
                html.H5("报警中心", className="mb-3", style={"fontFamily": COMMON_FONT}),
                dbc.Card([
                    dbc.CardBody([
                        dbc.ListGroup([
                            dbc.ListGroupItem([
                                html.Strong(f"刀具 {row.get('tool_id', '--')}", style={"fontFamily": COMMON_FONT}),
                                dbc.Badge(LEVEL_TEXT_MAP.get(row['level'], row['level']),
                                          color="danger" if row['level'] == 'danger' else ("warning" if row['level'] == 'warning' else "info"),
                                          className="ms-2"),
                                html.Div(row['description'], className="small text-muted")
                            ]) for row in alerts[:5]
                        ]) if alerts else dbc.Alert("暂无报警", color="info")
                    ])
                ])
            ])
            # 刀具状态分布图
            status_counts = tools_df["status"].value_counts().reset_index()
            status_counts.columns = ["status", "count"]
            status_cn = {"normal": "健康", "warning": "预警", "danger": "危险"}
            status_counts["status_cn"] = status_counts["status"].map(status_cn)
            pie_fig = charts.create_degradation_pie(tools_df)  # 复用原有函数
            status_chart = dbc.Col([
                dbc.Card([
                    dbc.CardHeader("刀具状态分布", style={"fontFamily": COMMON_FONT}),
                    dbc.CardBody(dcc.Graph(figure=pie_fig, config={"displayModeBar": False}))
                ])
            ], width=4)
            row_alert = dbc.Row([
                dbc.Col(alert_section, width=8),
                status_chart
            ], className="mb-4")
            # 精简刀具卡片
            tool_cards = [cards.tool_card_simple(row) for _, row in tools_df.iterrows()]
            tools_grid = dbc.Row([
                dbc.Col([
                    html.H5("刀具列表", style={"fontFamily": COMMON_FONT}),
                    dbc.Row(tool_cards, className="g-4")
                ])
            ])
            return html.Div([stats_row, row_alert, tools_grid])
        except Exception as e:
            import traceback
            traceback.print_exc()
            return dbc.Alert(f"数据加载失败: {str(e)}", color="danger")