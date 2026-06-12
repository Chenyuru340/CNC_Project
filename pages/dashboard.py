from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
from components import cards, charts
from api_client import get_tools, get_mock_data, get_aggregates, get_alerts
import pandas as pd
import config

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
            # 1. 聚合指标
            agg_data = get_aggregates() or {}
            total_tools = agg_data.get("total_tools", 0)
            warning_tools = agg_data.get("warning_tools", 0)
            danger_tools = agg_data.get("danger_tools", 0)
            # 以下两个变量已不再使用，但保留计算，以便未来恢复
            # avg_health = round(agg_data.get("avg_health", 0.0), 1)
            # avg_rul = round(agg_data.get("avg_rul", 0.0), 1)
            healthy_tools = total_tools - warning_tools - danger_tools

            # 统计卡片（仅保留4个）
            stats_row = dbc.Row([
                dbc.Col(cards.stat_card("在线刀具", total_tools, "tools", "primary"), width=3),
                dbc.Col(cards.stat_card("健康刀具", healthy_tools, "heartbeat", "success"), width=3),
                dbc.Col(cards.stat_card("预警刀具", warning_tools, "exclamation-triangle", "warning"), width=3),
                dbc.Col(cards.stat_card("危险刀具", danger_tools, "exclamation-circle", "danger"), width=3),
            ], className="mb-4")

            # 2. 刀具列表
            tools = get_tools(page=1, page_size=200)
            tools_df = pd.DataFrame(tools)

            if tools_df.empty and config.USE_MOCK:
                mock_data = get_mock_data()
                tools_df = mock_data["tools"].copy()

            for col in ["status", "health_score", "rul"]:
                if col not in tools_df.columns:
                    tools_df[col] = ""

            # 3. 报警数据
            alerts = get_alerts(page=1, page_size=100)
            total_alerts = len(alerts)
            unprocessed_count = len([a for a in alerts if a.get("handle_status") == "unprocessed"])
            processing_count = len([a for a in alerts if a.get("handle_status") == "processing"])
            processed_count = len([a for a in alerts if a.get("handle_status") == "processed"])
            latest_alerts = alerts[:5]

            # 报警统计横条
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

            # 报警卡片列表
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

            # 4. 刀具状态饼图
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

            # 5. 刀具卡片列表
            if tools_df.empty:
                tools_grid = dbc.Alert("刀具数据为空，请检查后端接口或数据源", color="warning")
            else:
                try:
                    tool_card_func = cards.tool_card_simple
                except AttributeError:
                    tool_card_func = cards.tool_card
                tool_cards = [tool_card_func(row) for _, row in tools_df.iterrows()]
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