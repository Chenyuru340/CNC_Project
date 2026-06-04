# pages/monitoring.py
import dash
from dash import html, dcc, Input, Output, State, no_update, ctx
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import numpy as np
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
    # 加载刀具列表
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

    # 点击刀具更新中间内容
    @app.callback(
        Output("monitoring-middle-content", "children"),
        Input({"type": "monitoring-tool-item", "index": dash.ALL}, "n_clicks"),
        prevent_initial_call=True
    )
    def show_tool_detail(clicks):
        print("状态监测页面：点击事件触发")
        if not ctx.triggered:
            return html.Div("请从左侧选择刀具", className="text-center text-muted", style={"marginTop": "50px"})
        # 获取点击的刀具ID
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

        # 获取刀具详情和HI曲线数据
        try:
            if config.USE_MOCK:
                data = get_mock_data()
                tools_df = data["tools"]
                tool_row = tools_df[tools_df["tool_id"] == tool_id]
                if tool_row.empty:
                    return dbc.Alert(f"未找到刀具 {tool_id}", color="warning")
                tool = tool_row.iloc[0].to_dict()
                health_score = tool.get("health_score", 0)
                rul_min = tool.get("rul", 0)
                # 使用新接口获取历史数据
                history = get_tool_history(tool_id, days=30)
                hi_vals = history.get("hi", [])
                x_vals = history.get("time", [])
                # 如果新接口没有数据，尝试从旧 features 获取（向后兼容）
                if not hi_vals:
                    features = data["features"]
                    tool_features = features[features["tool_id"] == tool_id].sort_values("timestamp")
                    if not tool_features.empty and "health_score" in tool_features.columns:
                        hi_vals = tool_features["health_score"].values / 100.0
                        x_vals = tool_features["timestamp"].values
            else:
                # 真实模式：优先使用新接口
                tool = get_tool_detail(tool_id)
                if not tool:
                    return dbc.Alert(f"未获取到刀具 {tool_id} 详情", color="warning")
                health_score = tool.get("health_score", 0)
                rul_min = tool.get("rul", 0)
                # 调用新接口 /api/tools/{tool_id}/history
                history = get_tool_history(tool_id, days=30)
                hi_vals = history.get("hi", [])
                x_vals = history.get("time", [])
                # 如果新接口无数据，可以回退到 get_features（可选）
                if not hi_vals:
                    # 回退方案（兼容旧接口）
                    from api_client import get_features
                    features = get_features(tool_id=tool_id, days=30)
                    if features:
                        hi_vals = [1 - f.get("health_score", 0)/100 for f in features]
                        x_vals = [f.get("date") or f.get("timestamp") for f in features]
        except Exception as e:
            print(f"状态监测页面错误: {e}")
            return dbc.Alert(f"加载数据失败: {str(e)}", color="danger")

        # 绘制HI曲线
        fig = go.Figure()
        if len(hi_vals) > 0:
            # 横坐标：如果有时间字符串，使用时间；否则使用序号
            if x_vals and all(isinstance(x, str) for x in x_vals):
                x_axis_title = "时间"
            else:
                x_vals = list(range(len(hi_vals)))
                x_axis_title = "样本序号"
            fig.add_trace(go.Scatter(x=x_vals, y=hi_vals, mode='lines+markers',
                                     line=dict(color='#0dcaf0', width=2),
                                     marker=dict(size=3), name='HI (健康指标)'))
            fig.update_layout(title=f"{tool_id} 健康指标退化曲线",
                              xaxis_title=x_axis_title, yaxis_title="HI 值",
                              template="plotly_dark",
                              paper_bgcolor='rgba(0,0,0,0)',
                              plot_bgcolor='rgba(0,0,0,0)')
        else:
            fig.update_layout(title="暂无历史数据", template="plotly_dark",
                              paper_bgcolor='rgba(0,0,0,0)',
                              plot_bgcolor='rgba(0,0,0,0)')

        return html.Div([
            dbc.Card([
                dbc.CardBody([
                    html.H4(f"刀具 {tool_id}", className="text-info"),
                    html.P("状态监测与剩余寿命预测", className="text-muted")
                ])
            ], className="mb-3 glass-card"),
            dcc.Graph(figure=fig, style={"height": "350px"}),
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