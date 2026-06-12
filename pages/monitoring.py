import dash
from dash import html, dcc, Input, Output, State, no_update, ctx
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import config
from api_client import get_tools, get_tool_detail, get_mock_data, get_tool_history
from utils.data_adapter import normalize_tool

def create_monitoring_page():
    return html.Div([
        dcc.Store(id="monitoring-selected-tool", data=None),
        dbc.Row([
            dbc.Col([
                html.H5("刀具列表", className="mb-3", style={"fontFamily": "Microsoft YaHei"}),
                html.Div(id="monitoring-tool-list", style={"maxHeight": "80vh", "overflowY": "auto"})
            ], width=2, style={"backgroundColor": "#111827", "borderRight": "1px solid #2a3a5c", "padding": "15px"}),
            dbc.Col([
                html.Div(id="monitoring-middle-content", children=[
                    html.Div("请从左侧选择刀具", className="text-center text-muted", style={"marginTop": "50px"})
                ])
            ], width=10, style={"padding": "20px", "background": "radial-gradient(circle at 20% 30%, #1a2332, #0c111c)"})
        ], className="g-0")
    ], style={"height": "100vh"})

def register_monitoring_callbacks(app):
    @app.callback(
        Output("monitoring-tool-list", "children"),
        Input("url", "pathname")
    )
    def load_tool_list(_):
        print("状态监测页面：加载刀具列表")
        tools_data = get_tools(page=1, page_size=200)
        tools = [normalize_tool(t) for t in tools_data] if tools_data else []
        if not tools and config.USE_MOCK:
            tools = get_mock_data()["tools"].to_dict("records")
        if not tools:
            print("状态监测页面：没有刀具数据")
            return dbc.Alert("没有刀具数据", color="warning")
        items = []
        for t in tools:
            tool_id = t.get("tool_id")
            if not tool_id:
                continue
            items.append(
                dbc.ListGroupItem(
                    f"{tool_id} ({t.get('type', '未知')})",
                    id={"type": "monitoring-tool-item", "index": tool_id},
                    action=True,
                    className="device-item",
                    style={"cursor": "pointer"}
                )
            )
        print(f"状态监测页面：加载了 {len(items)} 把刀具")
        return dbc.ListGroup(items, flush=True)

    @app.callback(
        Output("monitoring-middle-content", "children"),
        Input({"type": "monitoring-tool-item", "index": dash.ALL}, "n_clicks"),
        prevent_initial_call=True
    )
    def show_tool_detail(clicks):
        print("状态监测页面：点击事件触发")
        if not ctx.triggered:
            return html.Div("请从左侧选择刀具", className="text-center text-muted", style={"marginTop": "50px"})
        triggered = ctx.triggered[0]
        triggered_id = triggered.get("prop_id", "").split(".")[0]
        import json
        try:
            id_dict = json.loads(triggered_id)
            tool_id = id_dict.get("index")
        except:
            tool_id = getattr(ctx.triggered_id, "index", None)
        if not tool_id:
            return dbc.Alert("无法识别刀具ID", color="danger")
        print(f"状态监测页面：选中刀具 {tool_id}")

        try:
            # 获取详情（含 rul 和 hi）
            if config.USE_MOCK:
                data = get_mock_data()
                tools_df = data["tools"]
                tool_row = tools_df[tools_df["tool_id"] == tool_id]
                if tool_row.empty:
                    return dbc.Alert(f"未找到刀具 {tool_id}", color="warning")
                tool = tool_row.iloc[0].to_dict()
                health_score = tool.get("health_score", 0)
                rul_min = tool.get("rul", 0)
            else:
                tool = get_tool_detail(tool_id)
                if not tool:
                    return dbc.Alert(f"未获取到刀具 {tool_id} 详情", color="warning")
                health_score = tool.get("health_score", 0)
                rul_min = tool.get("rul", 0)

            # 获取历史曲线数据（使用新接口 start 参数）
            history = get_tool_history(tool_id, start="-30d")
            hi_vals = history.get("hi", [])
            x_vals = history.get("time", [])
            # 备选：若 history 无时间字段可用 health 字段，这里统一使用 hi

        except Exception as e:
            print(f"状态监测页面错误: {e}")
            return dbc.Alert(f"加载数据失败: {str(e)}", color="danger")

        # 绘制曲线
        fig = go.Figure()
        if hi_vals and len(hi_vals) > 0:
            if not x_vals or len(x_vals) != len(hi_vals):
                # 时间字段缺失则用序号
                x_vals = list(range(len(hi_vals)))
            fig.add_trace(go.Scatter(
                x=x_vals, y=hi_vals, mode='lines+markers',
                line=dict(color='#0dcaf0', width=2),
                marker=dict(size=3),
                name='HI (健康指标)'
            ))
            fig.update_layout(
                title=f"{tool_id} 健康指标退化曲线",
                xaxis_title="时间" if any(isinstance(x, str) for x in x_vals) else "样本序号",
                yaxis_title="HI 值",
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
        else:
            fig.update_layout(
                title="历史数据接口已实现，但暂无数据",
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            # 无数据时给出提示
            no_data_msg = html.Div([
                html.P("当前没有历史数据，可能的原因：", className="text-warning"),
                html.Ul([
                    html.Li("数据组尚未写入历史记录"),
                    html.Li("时间范围 start=-30d 内无数据，请调整参数"),
                    html.Li("检查后端日志确认 /api/tools/{id}/history 是否正常")
                ])
            ], className="mt-3")

        return html.Div([
            dbc.Card([
                dbc.CardBody([
                    html.H4(f"刀具 {tool_id}", className="text-info"),
                    html.P("状态监测与剩余寿命预测", className="text-muted")
                ])
            ], className="mb-3 glass-card"),
            dcc.Graph(figure=fig, style={"height": "350px"}),
            # 无数据时的额外提示
            (no_data_msg if (not hi_vals or len(hi_vals)==0) else None),
            dbc.Row([
                dbc.Col(dbc.Card([
                    dbc.CardBody([
                        html.H5("当前健康度", className="card-title text-muted"),
                        html.H2(f"{health_score} 分", className="text-success fw-bold"),
                        html.Small("归一化健康值 (0-100)")
                    ])
                ], className="glass-card text-center"), width=6),
                dbc.Col(dbc.Card([
                    dbc.CardBody([
                        html.H5("预测剩余寿命", className="card-title text-muted"),
                        html.H2(f"{rul_min} 分钟", className="text-info fw-bold"),
                        html.Small("单位: 分钟")
                    ])
                ], className="glass-card text-center"), width=6)
            ], className="mt-3")
        ])