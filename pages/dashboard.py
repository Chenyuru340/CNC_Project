from dash import html, dcc, callback, Input, Output, State, no_update
import dash_bootstrap_components as dbc
from components import cards, charts
from api_client import get_tools, get_tool_detail, get_mock_data, get_aggregates, get_alerts, get_tool_predict, \
    get_tool_history
import pandas as pd
import config

COMMON_FONT = "Microsoft YaHei"

def create_dashboard():
    return html.Div([
        html.H2("刀具健康总览", className="mb-4", style={"fontFamily": COMMON_FONT}),
        dcc.Interval(id="dashboard-interval", interval=30000, n_intervals=0),
        dbc.Spinner(html.Div(id="dashboard-content"))
    ])

def register_dashboard_callbacks(app):
    @app.callback(
        Output("dashboard-content", "children"),
        Input("url", "pathname"),               # 页面切换时立刻触发
        Input("dashboard-interval", "n_intervals"),  # 定时刷新
        Input("global-settings-store", "data"),      # 设置变更时刷新
    )
    def load_dashboard(pathname, n_intervals, settings):
        if pathname != "/":
            return no_update                      # 非仪表盘页面不请求数据

        alert_threshold = settings.get("alert_threshold", 40) if settings else 40
        try:
            tools = get_tools(page=1, page_size=200)
            tools_df = pd.DataFrame(tools)
            if tools_df.empty and config.USE_MOCK:
                mock_data = get_mock_data()
                tools_df = mock_data["tools"].copy()

            if not tools_df.empty:
                for i, row in tools_df.iterrows():
                    tid = row.get("tool_id")
                    if tid:
                        # 只取最近1小时的历史数据，避免超时
                        hist = get_tool_history(tid, start="-1h")
                        if hist and hist.get("health") and hist.get("rul"):
                            # 取最后一条记录的值作为当前值
                            last_health = hist["health"][-1]
                            last_rul = hist["rul"][-1]
                            tools_df.at[i, "health_score"] = last_health
                            tools_df.at[i, "rul"] = last_rul

            if not tools_df.empty and "health_score" in tools_df.columns:
                def compute_status(health):
                    h = float(health) if health else 0
                    if h >= 80:
                        return "normal"
                    elif h >= alert_threshold + 10:
                        return "warning"
                    elif h >= alert_threshold:
                        return "danger"
                    else:
                        return "danger"
                tools_df["status"] = tools_df["health_score"].apply(compute_status)

            warning_count = len(tools_df[tools_df["status"] == "warning"]) if not tools_df.empty else 0
            danger_count = len(tools_df[tools_df["status"] == "danger"]) if not tools_df.empty else 0
            total_tools = len(tools_df)
            healthy_tools = total_tools - warning_count - danger_count

            stats_row = dbc.Row([
                dbc.Col(cards.stat_card("在线刀具", total_tools, "tools", "primary"), width=3),
                dbc.Col(cards.stat_card("健康刀具", healthy_tools, "heartbeat", "success"), width=3),
                dbc.Col(cards.stat_card("预警刀具", warning_count, "exclamation-triangle", "warning"), width=3),
                dbc.Col(cards.stat_card("危险刀具", danger_count, "exclamation-circle", "danger"), width=3),
            ], className="mb-4")

            alerts = get_alerts(page=1, page_size=100)
            total_alerts = len(alerts)
            unprocessed_count = len([a for a in alerts if a.get("handle_status") == "unprocessed"])
            processing_count = len([a for a in alerts if a.get("handle_status") == "processing"])
            processed_count = len([a for a in alerts if a.get("handle_status") == "processed"])
            latest_alerts = alerts[:5]

            alert_stats = dbc.Row([
                dbc.Col(dbc.Card(
                    dbc.CardBody([
                        html.H6("未处理", className="text-muted mb-1", style={"fontFamily": COMMON_FONT}),
                        html.H3(unprocessed_count, className="text-danger fw-bold mb-0")
                    ]),
                    className="shadow-sm border-danger"
                ), width=3),
                dbc.Col(dbc.Card(
                    dbc.CardBody([
                        html.H6("处理中", className="text-muted mb-1", style={"fontFamily": COMMON_FONT}),
                        html.H3(processing_count, className="text-warning fw-bold mb-0")
                    ]),
                    className="shadow-sm border-warning"
                ), width=3),
                dbc.Col(dbc.Card(
                    dbc.CardBody([
                        html.H6("已处理", className="text-muted mb-1", style={"fontFamily": COMMON_FONT}),
                        html.H3(processed_count, className="text-success fw-bold mb-0")
                    ]),
                    className="shadow-sm border-success"
                ), width=3),
                dbc.Col(dbc.Card(
                    dbc.CardBody([
                        html.H6("总计", className="text-muted mb-1", style={"fontFamily": COMMON_FONT}),
                        html.H3(total_alerts, className="fw-bold mb-0")
                    ]),
                    className="shadow-sm"
                ), width=3),
            ], className="mb-3")

            alert_cards = []
            for alert in latest_alerts:
                level = alert.get("level", "info")
                if level == "danger":
                    border_color = "#dc3545"
                    level_badge = dbc.Badge("危险", color="danger")
                elif level == "warning":
                    border_color = "#ffc107"
                    level_badge = dbc.Badge("警告", color="warning")
                else:
                    border_color = "#0dcaf0"
                    level_badge = dbc.Badge("信息", color="info")

                status = alert.get("handle_status", "unprocessed")
                if status == "unprocessed":
                    status_badge = dbc.Badge("未处理", color="danger", className="ms-2")
                elif status == "processing":
                    status_badge = dbc.Badge("处理中", color="warning", className="ms-2")
                else:
                    status_badge = dbc.Badge("已处理", color="success", className="ms-2")

                alert_cards.append(
                    dbc.Card(
                        dbc.CardBody([
                            html.Div([
                                html.Div([
                                    html.Div(style={
                                        "width": "4px",
                                        "height": "100%",
                                        "backgroundColor": border_color,
                                        "position": "absolute",
                                        "left": 0,
                                        "top": 0,
                                        "borderRadius": "4px 0 0 4px"
                                    }),
                                    html.Div([
                                        html.Div([
                                            html.Small(alert.get("time", ""), className="text-muted me-2"),
                                            html.Strong(alert.get("tool_id", ""), className="me-2"),
                                            level_badge,
                                            status_badge
                                        ], className="mb-1"),
                                        html.Div([
                                            html.Span(alert.get("alert_type", ""), className="me-2 fw-bold"),
                                            html.Small(alert.get("description", ""), className="text-muted")
                                        ])
                                    ], style={"paddingLeft": "16px"})
                                ], className="d-flex", style={"position": "relative"})
                            ])
                        ]),
                        className="mb-2 shadow-sm"
                    )
                )

            if not alert_cards:
                alert_cards = [dbc.Alert("暂无报警记录", color="info")]

            alert_section = html.Div([
                html.H5("报警中心", className="mb-3", style={"fontFamily": COMMON_FONT}),
                alert_stats,
                html.Div(alert_cards),
                dbc.NavLink("查看全部 →", href="/alerts", className="mt-2 d-block text-end")
            ])

            if not tools_df.empty:
                pie_fig = charts.create_degradation_pie(tools_df)
                status_chart = dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("刀具状态分布", style={"fontFamily": COMMON_FONT}),
                        dbc.CardBody(dcc.Graph(figure=pie_fig, config={"displayModeBar": False}))
                    ])
                ], width=4)
            else:
                status_chart = dbc.Col(dbc.Alert("无状态数据", color="warning"), width=4)

            row_alert = dbc.Row([
                dbc.Col(alert_section, width=8),
                status_chart
            ], className="mb-4")

            if tools_df.empty:
                tools_grid = dbc.Alert("刀具数据为空，请检查后端接口或数据源", color="warning")
            else:
                tool_cards = [cards.tool_card_simple(row, alert_threshold) for _, row in tools_df.iterrows()]
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

    @app.callback(
        Output("dashboard-interval", "interval"),
        Input("global-settings-store", "data")
    )
    def update_interval(settings):
        if settings:
            return settings.get("refresh_interval", 30) * 1000
        return 30000