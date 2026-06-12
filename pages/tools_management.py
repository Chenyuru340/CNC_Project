# pages/tools_management.py
import dash
from dash import html, dash_table, Input, Output, State, callback, no_update, dcc
import dash_bootstrap_components as dbc
from api_client import get_tools, delete_tool, add_tool, get_mock_data
import pandas as pd
import json
import config

def create_tools_page():
    return html.Div([
        html.H2("刀具管理", className="mb-4"),
        dbc.Card([
            dbc.CardHeader("刀具清单"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col(dbc.Input(id="tool-search", placeholder="刀具ID/机床/类型", type="text"), width=4),
                    dbc.Col(dbc.Button("查询", id="tool-search-btn", color="primary"), width=2),
                    dbc.Col(dbc.Button("刷新", id="tool-refresh-btn", color="secondary", outline=True), width=2),
                    dbc.Col(dbc.Button("➕ 新增刀具", id="open-add-modal", color="success", className="float-end"), width=3)
                ], className="mb-3"),
                dbc.Spinner(html.Div(id="tools-table-container")),
                dcc.Store(id="delete-tool-store", data=None),
                # 删除 delete-message 组件，避免自动显示删除提示
                # html.Div(id="delete-message", className="mt-2 text-success"),
                html.Div(id="add-message", className="mt-2 text-success")
            ])
        ]),
        # 新增刀具模态框（精简版）
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("新增刀具")),
            dbc.ModalBody([
                dbc.Form([
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("刀具ID *", html_for="new-tool-id"),
                            dbc.Input(id="new-tool-id", type="text", placeholder="例: T-021", required=True)
                        ], width=6),
                        dbc.Col([
                            dbc.Label("机床 *", html_for="new-machine"),
                            dbc.Input(id="new-machine", type="text", placeholder="例: 机床_1", required=True)
                        ], width=6)
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("刀具类型 *", html_for="new-type"),
                            dbc.Select(id="new-type", options=[
                                {"label": "铣刀", "value": "铣刀"},
                                {"label": "钻头", "value": "钻头"},
                                {"label": "车刀", "value": "车刀"},
                                {"label": "镗刀", "value": "镗刀"}
                            ], value="铣刀")
                        ], width=6),
                        dbc.Col([
                            dbc.Label("生产厂家", html_for="new-manufacturer"),
                            dbc.Input(id="new-manufacturer", type="text", placeholder="例: 山特维克")
                        ], width=6)
                    ], className="mb-3"),
                    html.Div(id="add-tool-feedback", className="text-danger mb-2")
                ])
            ]),
            dbc.ModalFooter([
                dbc.Button("取消", id="close-add-modal", className="ms-auto", outline=True),
                dbc.Button("确认添加", id="confirm-add-tool", color="success", className="ms-2")
            ])
        ], id="add-tool-modal", size="lg", is_open=False)
    ])

def register_tools_callbacks(app):
    # 加载刀具表格
    @app.callback(
        Output("tools-table-container", "children"),
        [Input("tool-search-btn", "n_clicks"),
         Input("tool-refresh-btn", "n_clicks"),
         Input("delete-tool-store", "data")],
        [State("tool-search", "value")]
    )
    def load_tools(search_clicks, refresh_clicks, delete_data, search_key):
        try:
            from utils.data_adapter import normalize_tool
            all_tools = get_tools(page=1, page_size=500)
            all_tools = [normalize_tool(t) for t in all_tools] if all_tools else []
            df = pd.DataFrame(all_tools)
            if df.empty and config.USE_MOCK:
                data = get_mock_data()
                df = data["tools"].copy()
            if df.empty:
                return dbc.Alert("未找到刀具", color="warning")
            # 状态中文映射
            status_cn = {'normal': '正常', 'warning': '预警', 'danger': '危险'}
            df['status_cn'] = df['status'].map(status_cn)
            df['rul'] = pd.to_numeric(df['rul'], errors='coerce').fillna(0)
            df['rul_display'] = df['rul'].apply(lambda x: f"{int(x // 60)}h{int(x % 60)}m" if x >= 60 else f"{int(x)}min")
            # 表格头
            table_header = [
                html.Thead(html.Tr([
                    html.Th("刀具ID"), html.Th("机床"), html.Th("类型"),
                    html.Th("振动"), html.Th("电流"), html.Th("磨损"),
                    html.Th("健康度"), html.Th("状态"), html.Th("剩余寿命"),
                    html.Th("操作")
                ]))
            ]
            table_rows = []
            for _, row in df.iterrows():
                health = float(row.get('health_score', 0) or 0)
                if health >= 80:
                    health_color = "green"
                elif health >= 60:
                    health_color = "orange"
                elif health >= 40:
                    health_color = "darkorange"
                else:
                    health_color = "red"
                tool_id = row.get('tool_id', 'unknown')
                table_rows.append(html.Tr([
                    html.Td(row.get('tool_id', '-')),
                    html.Td(row.get('machine', '-')),
                    html.Td(row.get('type', '-')),
                    html.Td(row.get('vibration', 0)),
                    html.Td(row.get('current', 0)),
                    html.Td(row.get('vb', 0)),
                    html.Td(html.Span(f"{health}分", style={"color": health_color, "fontWeight": "bold"})),
                    html.Td(row.get('status_cn', '-')),
                    html.Td(row.get('rul_display', '-')),
                    html.Td(dbc.Button("删除", id={"type": "delete-tool-btn", "index": tool_id},
                                       color="danger", size="sm", outline=True))
                ]))
            table_body = [html.Tbody(table_rows)]
            table = dbc.Table(table_header + table_body, bordered=True, hover=True, striped=True, size="sm", responsive=True)
            return html.Div(table)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return dbc.Alert(f"加载失败: {str(e)}", color="danger")

    # 删除刀具回调（不再输出 delete-message）
    @app.callback(
        Output("delete-tool-store", "data", allow_duplicate=True),
        Input({"type": "delete-tool-btn", "index": dash.ALL}, "n_clicks"),
        prevent_initial_call=True
    )
    def handle_delete(click_values):
        ctx = dash.callback_context
        if not ctx.triggered:
            return no_update
        trigger = ctx.triggered[0]
        if "delete-tool-btn" in trigger["prop_id"]:
            btn_id = json.loads(trigger["prop_id"].split(".")[0])
            tool_id = btn_id["index"]
            try:
                result = delete_tool(tool_id)
                # 只更新 store，触发表格刷新，不再显示任何消息
                return {"deleted": tool_id}
            except Exception as e:
                return {"deleted": tool_id}
        return no_update

    # 打开/关闭模态框
    @app.callback(
        Output("add-tool-modal", "is_open"),
        Input("open-add-modal", "n_clicks"),
        Input("close-add-modal", "n_clicks"),
        Input("confirm-add-tool", "n_clicks"),
        State("add-tool-modal", "is_open"),
        prevent_initial_call=True
    )
    def toggle_modal(open_clicks, close_clicks, confirm_clicks, is_open):
        ctx = dash.callback_context
        if not ctx.triggered:
            return False
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if button_id == "open-add-modal":
            return True
        elif button_id in ["close-add-modal", "confirm-add-tool"]:
            return False
        return is_open

    # 确认添加刀具（精简版）
    @app.callback(
        [Output("add-tool-feedback", "children"),
         Output("add-message", "children"),
         Output("new-tool-id", "value"),
         Output("new-machine", "value"),
         Output("new-type", "value"),
         Output("new-manufacturer", "value")],
        Input("confirm-add-tool", "n_clicks"),
        [State("new-tool-id", "value"),
         State("new-machine", "value"),
         State("new-type", "value"),
         State("new-manufacturer", "value")],
        prevent_initial_call=True
    )
    def add_new_tool(n_clicks, tool_id, machine, tool_type, manufacturer):
        if not n_clicks:
            return no_update, no_update, no_update, no_update, no_update, no_update
        if not tool_id or not machine:
            return "刀具ID和机床为必填项", "", no_update, no_update, no_update, no_update
        # 构建刀具数据（其他字段使用默认值，后端会重新计算）
        new_tool = {
            "tool_id": tool_id,
            "machine": machine,
            "type": tool_type,
            "manufacturer": manufacturer or "",
            "vibration": 0.0,
            "current": 0.0,
            "vb": 0.0,
            "health_score": 100.0,
            "status": "normal",
            "current_usage": 50.0,
            "rul": 2000
        }
        try:
            add_tool(new_tool)
            return ("", f"刀具 {tool_id} 添加成功", "", "", "铣刀", "")
        except Exception as e:
            return f"添加失败: {str(e)}", "", no_update, no_update, no_update, no_update
