# pages/knowledge_base.py
import base64
from dash import html, dcc, Input, Output, State, no_update, ALL, ctx
import dash_bootstrap_components as dbc
from api_client import get_docs_list, get_doc_detail, add_doc, delete_doc, search_docs, upload_doc
import config

# =========================================================
# 辅助函数：获取文件列表并渲染
# =========================================================
def get_file_list():
    try:
        docs = get_docs_list()
        if not docs:
            return []
        files = []
        for d in docs:
            filename = d.get("filename", "")
            size_kb = round(d.get("size", 0) / 1024, 2) if d.get("size") else "?"
            files.append({
                "name": filename,
                "size": f"{size_kb} KB" if isinstance(size_kb, (int, float)) else size_kb
            })
        files.sort(key=lambda x: x["name"].lower())
        return files
    except Exception as e:
        print(f"get_file_list error: {e}")
        return []

def render_file_list(selected_filename=None):
    files = get_file_list()
    if not files:
        return dbc.Alert(
            "暂无知识文件，请上传或新建Markdown文档",
            color="secondary"
        )
    items = []
    for file in files:
        is_active = (selected_filename == file["name"])
        item = dbc.ListGroupItem(
            [
                html.Div([
                    html.Div(
                        file["name"],
                        style={
                            "fontWeight": "600",
                            "fontSize": "15px",
                            "marginBottom": "4px",
                            "fontFamily": "Microsoft YaHei"
                        }
                    ),
                    html.Small(
                        file["size"],
                        style={"color": "#94a3b8", "fontFamily": "Microsoft YaHei"}
                    )
                ])
            ],
            id={"type": "kb-file-item", "index": file["name"]},
            action=True,
            n_clicks=0,
            style={
                "backgroundColor": "#0f172a" if not is_active else "#1e3a5c",
                "border": "1px solid #2a4a6a",
                "color": "#f1f5f9",
                "borderRadius": "12px",
                "marginBottom": "10px",
                "cursor": "pointer",
                "transition": "all 0.2s ease"
            }
        )
        items.append(item)
    return dbc.ListGroup(items, flush=True)

# =========================================================
# 页面布局 (保持不变)
# =========================================================
def create_knowledge_base_page():
    return html.Div([
        dcc.Store(id="kb-selected-file", data=None),
        dcc.Interval(id="kb-auto-refresh", interval=10000, n_intervals=0),
        html.Div([
            html.H2("知识库管理", style={
                "color": "#4dd0e1", "fontWeight": "700", "marginBottom": "6px",
                "fontFamily": "Microsoft YaHei"
            }),
            html.P("支持上传PDF/DOC/DOCX/TXT/MD，编辑、删除文档，并搜索知识库内容",
                   style={"color": "#94a3b8", "fontFamily": "Microsoft YaHei"})
        ], className="mb-4"),
        html.Div([
            dbc.InputGroup([
                dbc.Input(
                    id="kb-search-input",
                    placeholder="输入关键词搜索知识库...",
                    style={"backgroundColor": "#0b1220", "color": "#e2e8f0",
                           "border": "1px solid #2a4a6a", "fontFamily": "Microsoft YaHei"}
                ),
                dbc.Button("搜索", id="kb-search-btn", color="primary", className="ms-2")
            ], className="mb-3"),
            html.Div(id="kb-search-results", className="mb-3")
        ]),
        html.Div([
            dcc.Upload(
                id="kb-upload",
                children=dbc.Button(
                    [html.I(className="fas fa-upload me-2"), "上传文件"],
                    color="primary", style={"marginRight": "10px", "borderRadius": "10px"}
                ),
                multiple=False
            ),
            dbc.Button(
                [html.I(className="fas fa-plus me-2"), "新建文件"],
                id="kb-new-btn", color="success",
                style={"marginRight": "10px", "borderRadius": "10px"}
            ),
            dbc.Button(
                [html.I(className="fas fa-save me-2"), "保存"],
                id="kb-save-btn", color="warning",
                style={"marginRight": "10px", "borderRadius": "10px"}
            ),
            dbc.Button(
                [html.I(className="fas fa-trash me-2"), "删除"],
                id="kb-delete-btn", color="danger",
                style={"borderRadius": "10px"}
            )
        ], className="d-flex flex-wrap mb-4", style={"gap": "10px"}),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(
                        html.H5("文档列表", style={"marginBottom": 0, "color": "#f1f5f9",
                                                  "fontFamily": "Microsoft YaHei"}),
                        style={"backgroundColor": "#1e293b", "borderBottom": "1px solid #2a4a6a"}
                    ),
                    dbc.CardBody(
                        html.Div(id="kb-file-list"),
                        style={"maxHeight": "720px", "overflowY": "auto"}
                    )
                ], style={
                    "backgroundColor": "#111827",
                    "border": "1px solid #2a4a6a",
                    "borderRadius": "20px",
                    "boxShadow": "0 10px 30px rgba(0,0,0,0.35)"
                })
            ], width=4),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(
                        html.H5("编辑器", style={"marginBottom": 0, "color": "#f1f5f9",
                                                "fontFamily": "Microsoft YaHei"}),
                        style={"backgroundColor": "#1e293b", "borderBottom": "1px solid #2a4a6a"}
                    ),
                    dbc.CardBody([
                        dbc.Input(
                            id="kb-filename",
                            type="text",
                            placeholder="文件名（如 manual.md）",
                            style={
                                "backgroundColor": "#0b1220",
                                "color": "#e2e8f0",
                                "border": "1px solid #2a4a6a",
                                "borderRadius": "8px",
                                "marginBottom": "12px",
                                "fontFamily": "Microsoft YaHei"
                            }
                        ),
                        dcc.Textarea(
                            id="kb-editor",
                            placeholder="在此编写Markdown内容...",
                            style={
                                "width": "100%",
                                "height": "680px",
                                "background": "#0b1220",
                                "color": "#e2e8f0",
                                "border": "1px solid #2a4a6a",
                                "outline": "none",
                                "resize": "none",
                                "padding": "16px",
                                "borderRadius": "12px",
                                "fontFamily": "Consolas, monospace",
                                "fontSize": "14px",
                                "lineHeight": "1.7",
                                "boxSizing": "border-box",
                                "overflowY": "auto"
                            }
                        )
                    ])
                ], style={
                    "backgroundColor": "#111827",
                    "border": "1px solid #2a4a6a",
                    "borderRadius": "20px",
                    "boxShadow": "0 10px 30px rgba(0,0,0,0.35)"
                })
            ], width=8)
        ]),
        html.Div(id="kb-msg", className="mt-3")
    ], style={"padding": "10px"})

# =========================================================
# 回调注册
# =========================================================
def register_knowledge_base_callbacks(app):
    @app.callback(
        Output("kb-file-list", "children"),
        Input("kb-auto-refresh", "n_intervals"),
        State("kb-selected-file", "data")
    )
    def refresh_file_list(n, selected):
        return render_file_list(selected)

    @app.callback(
        Output("kb-filename", "value"),
        Output("kb-editor", "value"),
        Output("kb-selected-file", "data"),
        Output("kb-file-list", "children", allow_duplicate=True),
        Input({"type": "kb-file-item", "index": ALL}, "n_clicks"),
        prevent_initial_call=True
    )
    def load_file(clicks):
        if not ctx.triggered_id:
            return no_update, no_update, no_update, no_update
        file_name = ctx.triggered_id["index"]
        try:
            doc = get_doc_detail(file_name)
            content = doc.get("content", "") if doc else ""
            new_list = render_file_list(file_name)
            return file_name, content, file_name, new_list
        except Exception as e:
            return file_name, f"读取失败：{str(e)}", file_name, render_file_list(file_name)

    @app.callback(
        Output("kb-filename", "value", allow_duplicate=True),
        Output("kb-editor", "value", allow_duplicate=True),
        Output("kb-selected-file", "data", allow_duplicate=True),
        Input("kb-new-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def new_markdown(_):
        return "new_doc.md", "", None

    # 保存文件（调用 upload_doc）
    @app.callback(
        Output("kb-msg", "children"),
        Output("kb-file-list", "children", allow_duplicate=True),
        Input("kb-save-btn", "n_clicks"),
        State("kb-filename", "value"),
        State("kb-editor", "value"),
        State("kb-selected-file", "data"),
        prevent_initial_call=True
    )
    def save_file(_, filename, content, selected):
        if not filename:
            return dbc.Alert("请输入文件名", color="danger"), no_update
        if not filename.endswith(".md"):
            return dbc.Alert("文件名必须以 .md 结尾（Markdown格式）", color="warning"), no_update
        try:
            result = add_doc(filename, content or "")
            if result:
                new_list = render_file_list(selected)
                return dbc.Alert(f"保存成功：{filename}", color="success"), new_list
            else:
                return dbc.Alert("保存失败，请检查后端连接", color="danger"), no_update
        except Exception as e:
            return dbc.Alert(str(e), color="danger"), no_update

    # 删除文件（后端未实现，提示）
    @app.callback(
        Output("kb-msg", "children", allow_duplicate=True),
        Output("kb-filename", "value", allow_duplicate=True),
        Output("kb-editor", "value", allow_duplicate=True),
        Output("kb-selected-file", "data", allow_duplicate=True),
        Output("kb-file-list", "children", allow_duplicate=True),
        Input("kb-delete-btn", "n_clicks"),
        State("kb-selected-file", "data"),
        prevent_initial_call=True
    )
    def delete_file(_, selected_filename):
        if not selected_filename:
            return dbc.Alert("未选择文件", color="warning"), no_update, no_update, no_update, no_update
        try:
            result = delete_doc(selected_filename)
            if result:
                new_list = render_file_list(None)
                return (dbc.Alert(f"删除成功：{selected_filename}", color="success"),
                        "", "", None, new_list)
            else:
                return (dbc.Alert("删除失败，请检查后端连接或文件是否存在", color="danger"),
                        no_update, no_update, no_update, no_update)
        except Exception as e:
            return (dbc.Alert(str(e), color="danger"),
                    no_update, no_update, no_update, no_update)

    # 上传文件（改为调用 upload_doc）
    @app.callback(
        Output("kb-msg", "children", allow_duplicate=True),
        Output("kb-file-list", "children", allow_duplicate=True),
        Input("kb-upload", "contents"),
        State("kb-upload", "filename"),
        prevent_initial_call=True
    )
    def upload_file(contents, filename):
        if contents is None:
            return no_update, no_update
        try:
            content_type, content_string = contents.split(",")
            decoded = base64.b64decode(content_string)
            result = upload_doc(filename, decoded)
            if result:
                new_list = render_file_list()
                return dbc.Alert(f"上传成功：{filename}", color="success"), new_list
            else:
                return dbc.Alert("上传失败，请检查后端连接", color="danger"), no_update
        except Exception as e:
            return dbc.Alert(str(e), color="danger"), no_update

    # 知识库检索
    @app.callback(
        Output("kb-search-results", "children"),
        Input("kb-search-btn", "n_clicks"),
        State("kb-search-input", "value"),
        prevent_initial_call=True
    )
    def search_kb(n_clicks, query):
        if not query:
            return html.Div()
        try:
            results = search_docs(query)
            if not results:
                return dbc.Alert("未找到相关文档", color="info")
            items = []
            for res in results[:10]:
                filename = res.get("filename", "未知")
                snippet = res.get("content", "")[:300]
                items.append(
                    dbc.ListGroupItem([
                        html.Strong(filename, style={"fontFamily": "Microsoft YaHei"}),
                        html.P(snippet, style={"color": "#b0c7e0", "fontSize": "0.9rem",
                                               "marginTop": "5px", "fontFamily": "Microsoft YaHei"})
                    ], style={"backgroundColor": "#1a2332", "borderColor": "#2a4a6a", "marginBottom": "5px"})
                )
            return html.Div([
                html.H6("检索结果", style={"color": "#4dd0e1", "marginBottom": "10px",
                                         "fontFamily": "Microsoft YaHei"}),
                dbc.ListGroup(items)
            ])
        except Exception as e:
            return dbc.Alert(f"检索失败：{str(e)}", color="danger")