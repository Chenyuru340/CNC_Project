# pages/dashboard.py
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
from components import cards, charts
from api_client import get_tools, get_mock_data
import pandas as pd
from utils.data_adapter import normalize_tool
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
            # 1. 获取刀具列表（后端已实现 GET /api/tools）
            tools = get_tools(page=1, page_size=200)
            tools = [normalize_tool(t) for t in tools] if tools else []
            tools_df = pd.DataFrame(tools)

            # 如果真实数据为空且开启了 Mock，则回退到 Mock 数据（保持演示能力）
            if tools_df.empty and config.USE_MOCK:
                mock_data = get_mock_data()
                tools_df = mock_data["tools"].copy()

            if tools_df.empty:
                return dbc.Alert("刀具数据为空", color="warning")

            # 2. 统计卡片数据（直接从刀具列表计算，无需 /tools/aggregates）
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

            # 3. 报警中心（后端无报警接口，显示“暂无报警”，样式与原卡片一致）
            alert_section = html.Div([
                html.H5("报警中心", className="mb-3", style={"fontFamily": COMMON_FONT}),
                dbc.Card([
                    dbc.CardBody([
                        dbc.Alert("暂无报警", color="info")
                    ])
                ])
            ])

            # 4. 刀具状态分布图（完全保留原有逻辑）
            pie_fig = charts.create_degradation_pie(tools_df)  # 该函数接受 tools_df 并返回饼图
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

            # 5. 刀具卡片列表（使用原项目中的 tool_card_simple，若不存在则回退到 tool_card）
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