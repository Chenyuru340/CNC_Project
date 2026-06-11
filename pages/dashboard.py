from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
from components import cards, charts
# 导入合法接口（均为文档定义接口，无非法接口）
from api_client import get_tools, get_mock_data, get_aggregates, get_alerts
from utils.data_adapter import normalize_tool
import pandas

pd
import config

# 全局字体统一定义
COMMON_FONT = "Microsoft YaHei"


def create_dashboard():
    return html.Div([
        # 关键组件：路由监听（原代码缺失，导致页面无法自动加载数据）
        dcc.Location(id="url", refresh=False),

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
            # 1. 获取聚合统计数据（接口：/api/tools/aggregates）
            agg_data = get_aggregates() or {}
            total_tools = agg_data.get("total_tools", 0)
            warning_tools = agg_data.get("warning_tools", 0)
            danger_tools = agg_data.get("danger_tools", 0)
            # 数值格式化，匹配接口示例（保留1位小数）
            avg_health = round(agg_data.get("avg_health", 0.0), 1)
            avg_rul = round(agg_data.get("avg_rul", 0.0), 1)
            healthy_tools = total_tools - warning_tools - danger_tools

            # 组装统计卡片行
            stats_row = dbc.Row([
                dbc.Col(cards.stat_card("在线刀具", total_tools, "tools", "primary"), width=2),
                dbc.Col(cards.stat_card("健康刀具", healthy_tools, "heartbeat", "success"), width=2),
                dbc.Col(cards.stat_card("预警刀具", warning_tools, "exclamation-triangle", "warning"), width=2),
                dbc.Col(cards.stat_card("危险刀具", danger_tools, "exclamation-circle", "danger"), width=2),
                dbc.Col(cards.stat_card("平均健康度", avg_health, "activity", "info"), width=2),
                dbc.Col(cards.stat_card("平均剩余寿命", avg_rul, "clock", "secondary"), width=2),
            ], className="mb-4")

            # 2. 获取刀具列表数据（接口：/api/tools）
            tools = get_tools(page=1, page_size=200)
            tools = [normalize_tool(t) for t in tools] if tools else []
            tools_df = pd.DataFrame(tools)

            # Mock模式兜底数据
            if tools_df.empty and config.USE_MOCK:
                mock_data = get_mock_data()
                tools_df = mock_data["tools"].copy()

            # 字段兜底，避免图表渲染报错
            for col in ["status", "health_score", "rul"]:
                if col not in tools_df.columns:
                    tools_df[col] = ""

            # 刀具数据完全为空时直接返回
            if tools_df.empty:
                return html.Div([
                    stats_row,
                    dbc.Alert("刀具数据为空", color="warning")
                ])

            # 3. 获取报警数据（接口：/api/alerts）
            alerts = get_alerts(page=1, page_size=10)
            unprocessed_alert_count = len([a for a in alerts if a.get("handle_status") == "unprocessed"])

            # 组装报警模块
            if alerts:
                alert_list_items = []
                for idx, alert in enumerate(alerts[:5]):
                    alert_text = f"[{alert.get('time', '')}] {alert.get('tool_id', '')} - {alert.get('alert_type', '')}"
                    alert_list_items.append(html.Li(alert_text))
                alert_content = html.Div([
                    html.P(f"未处理报警：{unprocessed_alert_count} 条", className="fw-bold"),
                    html.Ul(alert_list_items)
                ])
            else:
                alert_content = dbc.Alert("暂无报警记录", color="info")

            alert_section = html.Div([
                html.H5("报警中心", className="mb-3", style={"fontFamily": COMMON_FONT}),
                dbc.Card([
                    dbc.CardBody([alert_content])
                ])
            ])

            # 4. 刀具状态饼图
            pie_fig = charts.create_degradation_pie(tools_df)
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

            # 5. 刀具卡片列表（兼容两种卡片函数）
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

            # 页面整体组装
            return html.Div([stats_row, row_alert, tools_grid])

        except Exception as e:
            import traceback
            traceback.print_exc()
            return dbc.Alert(f"数据加载失败: {str(e)}", color="danger")