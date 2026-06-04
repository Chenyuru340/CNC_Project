# pages/phm_agent.py
import dash
from dash import html, dcc, Input, Output, State, no_update, ctx
import dash_bootstrap_components as dbc
import base64
import pandas as pd
import io
import config
from api_client import post_agent, search_docs

def parse_file(contents, filename):
    if not contents:
        return None
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        if filename.lower().endswith(".csv"):
            return pd.read_csv(io.StringIO(decoded.decode("utf-8")))
        else:
            return decoded.decode("utf-8", errors="ignore")
    except:
        return None

def create_phm_agent_page():
    return html.Div([
        dcc.Store(id="phm-chat-history", data=[]),
        dcc.Store(id="phm-upload-data", data=None),
        html.Div([
            html.H2("PHM智能体（AI Agent）", style={"fontFamily": "Microsoft YaHei", "color": "#4dd0e1"}),
            html.P("支持信息查询 / 知识库查询 / 数据分析", style={"color": "#94a3b8"})
        ], style={"padding": "20px 20px 0 20px"}),
        html.Div(id="phm-chat-messages", style={
            "height": "calc(100vh - 200px)",
            "overflowY": "auto",
            "padding": "15px",
            "backgroundColor": "#0f172a",
            "margin": "0 20px",
            "borderRadius": "10px",
            "border": "1px solid #2a4a6a"
        }),
        html.Div([
            dcc.Upload(
                id="phm-upload-file",
                children=html.Div(["📁 拖拽或点击上传 CSV/TXT"], style={"padding": "10px"}),
                style={
                    "border": "1px dashed #2a4a6a",
                    "borderRadius": "5px",
                    "backgroundColor": "#0f1a24",
                    "textAlign": "center",
                    "cursor": "pointer",
                    "marginBottom": "10px",
                    "color": "#b0c7e0"
                }
            ),
            html.Div(id="phm-upload-status", className="small text-info mb-2"),
            dbc.InputGroup([
                dbc.Input(id="phm-user-input", placeholder="输入问题...", className="bg-dark text-light"),
                dbc.Button("发送", id="phm-send-btn", color="primary")
            ])
        ], style={"padding": "15px 20px 20px 20px", "borderTop": "1px solid #2a4a6a"})
    ], style={"height": "100vh", "backgroundColor": "#0a0f1a", "display": "flex", "flexDirection": "column"})

def register_phm_agent_callbacks(app):
    @app.callback(
        Output("phm-chat-messages", "children"),
        Output("phm-user-input", "value"),
        Output("phm-chat-history", "data"),
        Input("phm-send-btn", "n_clicks"),
        Input("phm-user-input", "n_submit"),
        State("phm-user-input", "value"),
        State("phm-chat-history", "data"),
        State("phm-upload-data", "data"),
        prevent_initial_call=True
    )
    def chat(click, submit, question, history, upload_data):
        if not question or not question.strip():
            return no_update, no_update, no_update
        history = history or []
        # 知识库检索
        context = ""
        try:
            docs = search_docs(question)
            if docs:
                context = "\n".join([d.get("content", "")[:500] for d in docs])
        except:
            pass
        # 构建增强问题
        enhanced_q = f"知识库内容：{context}\n用户问题：{question}"
        if upload_data:
            enhanced_q += f"\n上传文件数据摘要：{upload_data.get('data', '')[:1000]}"
        try:
            answer, figure = post_agent("global", enhanced_q, None)
        except Exception as e:
            answer = f"调用失败：{str(e)}"
            figure = None
        history.append({"user": question, "agent": answer, "figure": figure})
        # 渲染
        msgs = []
        for item in history:
            msgs.append(dbc.Alert(f"你：{item['user']}", color="secondary"))
            msgs.append(dbc.Alert(f"智能体：{item['agent']}", color="info"))
            if item.get("figure"):
                msgs.append(dcc.Graph(figure=item["figure"]))
        return msgs, "", history

    @app.callback(
        Output("phm-upload-status", "children"),
        Output("phm-upload-data", "data"),
        Input("phm-upload-file", "contents"),
        State("phm-upload-file", "filename"),
        prevent_initial_call=True
    )
    def upload_file(contents, filename):
        if not contents:
            return no_update, no_update
        data = parse_file(contents, filename)
        if isinstance(data, pd.DataFrame):
            summary = f"已上传CSV，共{len(data)}行，列：{', '.join(data.columns)}"
            return summary, {"filename": filename, "data": data.to_string(max_rows=10)}
        else:
            return f"已上传文本文件：{filename}", {"filename": filename, "data": str(data)[:2000]}