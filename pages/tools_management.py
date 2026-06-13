# pages/tools_management.py
import dash
from dash import html, Input, Output, State, callback, no_update, dcc, ctx
import dash_bootstrap_components as dbc
import pandas as pd
import json
import config
from api_client import get_tools, delete_tool, add_tool, get_mock_data

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
                html.Div(id="tools-feedback", className="mt-2")  # 统一反馈区
            ])
        ]),
        # 新增刀具模态框
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
        Output("tools-feedback", "children", allow_duplicate=True),
        Input("tool-search-btn", "n_clicks"),
        Input("tool-refresh-btn", "n_clicks"),
        Input("delete-tool-store", "data"),
        State("tool-search", "value"),
        prevent_initial_call=False
    )
    def load_tools(search_clicks, refresh_clicks, delete_data, search_key):
        try:
            # 直接使用 get_tools 返回的数据，无需二次 normalize
            all_tools = get_tools(page=1, page_size=500)
            if not all_tools and config.USE_MOCK:
                mock_data = get_mock_data()
                all_tools = mock_data["tools"].to_dict("records")
            if not all_tools:
                return dbc.Alert("未找到刀具", color="warning"), ""

            df = pd.DataFrame(all_tools)

            # 确保必要列存在（后端可能缺失，用"-"填充）
            for col in ["tool_id", "machine", "type", "manufacturer"]:
                if col not in df.columns:
                    df[col] = "-"
            df["tool_id"] = df["tool_id"].fillna("-")
            df["machine"] = df["machine"].fillna("-")
            df["type"] = df["type"].fillna("铣刀")
            df["manufacturer"] = df["manufacturer"].fillna("-")

            # 搜索过滤
            if search_key and search_key.strip():
                keyword = search_key.strip().lower()
                mask = df["tool_id"].str.lower().str.contains(keyword) | \
                       df["machine"].str.lower().str.contains(keyword) | \
                       df["type"].str.lower().str.contains(keyword)
                df = df[mask]

            if df.empty:
                return dbc.Alert("未找到匹配的刀具", color="info"), ""

            # 构建表格
            table_header = [
                html.Thead(html.Tr([
                    html.Th("刀具ID"), html.Th("机床"), html.Th("类型"),
                    html.Th("生产厂家"), html.Th("操作")
                ]))
            ]
            table_rows = []
            for _, row in df.iterrows():
                tool_id = row["tool_id"]
                table_rows.append(html.Tr([
                    html.Td(tool_id),
                    html.Td(row["machine"]),
                    html.Td(row["type"]),
                    html.Td(row["manufacturer"]),
                    html.Td(dbc.Button("删除", id={"type": "delete-tool-btn", "index": tool_id},
                                       color="danger", size="sm", outline=True))
                ]))
            table_body = [html.Tbody(table_rows)]
            table = dbc.Table(table_header + table_body, bordered=True, hover=True, striped=True, size="sm", responsive=True)
            return html.Div(table), ""
        except Exception as e:
            import traceback
            traceback.print_exc()
            return dbc.Alert(f"加载失败: {str(e)}", color="danger"), ""

    # 删除刀具（降级提示）
    @app.callback(
        Output("delete-tool-store", "data"),
        Output("tools-feedback", "children", allow_duplicate=True),
        Input({"type": "delete-tool-btn", "index": dash.ALL}, "n_clicks"),
        prevent_initial_call=True
    )
    def handle_delete(click_values):
        if not ctx.triggered:
            return no_update, no_update
        trigger = ctx.triggered[0]
        if "delete-tool-btn" not in trigger["prop_id"]:
            return no_update, no_update
        btn_id = json.loads(trigger["prop_id"].split(".")[0])
        tool_id = btn_id["index"]
        try:
            result = delete_tool(tool_id)
            if result and isinstance(result, dict):
                # 成功删除（或Mock成功）
                return {"deleted": tool_id}, f"刀具 {tool_id} 删除成功"
            else:
                # 接口返回None或空，说明未实现
                return no_update, dbc.Alert("删除功能暂未开放，请联系管理员", color="warning")
        except Exception as e:
            return no_update, dbc.Alert(f"删除异常: {str(e)}", color="danger")

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
        trigger = ctx.triggered[0] if ctx.triggered else None
        if not trigger:
            return is_open
        button_id = trigger["prop_id"].split(".")[0]
        if button_id == "open-add-modal":
            return True
        elif button_id in ["close-add-modal", "confirm-add-tool"]:
            return False
        return is_open

    # 确认添加刀具（提交正确字段 + 降级提示）
    @app.callback(
        Output("add-tool-feedback", "children"),
        Output("tools-feedback", "children", allow_duplicate=True),
        Output("new-tool-id", "value"),
        Output("new-machine", "value"),
        Output("new-type", "value"),
        Output("new-manufacturer", "value"),
        Output("add-tool-modal", "is_open", allow_duplicate=True),
        Input("confirm-add-tool", "n_clicks"),
        State("new-tool-id", "value"),
        State("new-machine", "value"),
        State("new-type", "value"),
        State("new-manufacturer", "value"),
        prevent_initial_call=True
    )
    def add_new_tool(n_clicks, tool_id, machine, tool_type, manufacturer):
        if not n_clicks:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update
        if not tool_id or not machine:
            return "刀具ID和机床为必填项", no_update, no_update, no_update, no_update, no_update, no_update

        new_tool = {
            "tool_id": tool_id,
            "machine": machine,
            "type": tool_type or "铣刀",
            "manufacturer": manufacturer or ""
        }
        try:
            result = add_tool(new_tool)
            if result and isinstance(result, dict) and result.get("tool_id"):
                # 成功（Mock或真实接口返回正常）
                return "", f"刀具 {tool_id} 添加成功", "", "", "铣刀", "", False
            else:
                # 接口未实现或返回异常
                return "新增失败：后端接口暂未开放", no_update, no_update, no_update, no_update, no_update, no_update
        except Exception as e:
            return f"添加异常: {str(e)}", no_update, no_update, no_update, no_update, no_update, no_update