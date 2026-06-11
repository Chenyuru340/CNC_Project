import dash
from dash import html, dcc, Input, Output, State, callback, no_update, ctx
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import base64
import pandas as pd
import io
import numpy as np
from scipy.signal import spectrogram, hilbert

import config
# 恢复导入后端诊断接口函数
from api_client import post_diagnosis_analysis

# ---------- 辅助函数 ----------
def parse_uploaded_file(contents, filename):
    if contents is None:
        return None
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        if filename.lower().endswith('.csv'):
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        elif filename.lower().endswith('.parquet'):
            df = pd.read_parquet(io.BytesIO(decoded))
        else:
            return None
        return df
    except Exception as e:
        print(f"文件解析失败: {e}")
        return None

def generate_mock_analysis(active_tab, signal, params):
    # 注意：这个函数仅在 USE_MOCK=True 时使用，真实模式下不会调用
    if active_tab == "time":
        features = params.get("features", ["均值", "均方根"])
        feat_vals = {}
        for feat in features:
            if feat == "均值":
                vals = [np.mean(signal)] * len(signal)
            elif feat == "方差":
                vals = [np.var(signal)] * len(signal)
            elif feat == "峰值":
                vals = [np.max(np.abs(signal))] * len(signal)
            elif feat == "峭度":
                kurt = np.mean((signal - np.mean(signal))**4) / (np.std(signal)**4 + 1e-8)
                vals = [kurt] * len(signal)
            elif feat == "均方根":
                vals = [np.sqrt(np.mean(signal**2))] * len(signal)
            else:
                continue
            feat_vals[feat] = vals
        fig = go.Figure()
        for feat, vals in feat_vals.items():
            fig.add_trace(go.Scatter(x=list(range(len(signal))), y=vals, mode='lines', name=feat))
        fig.update_layout(
            title="时域特征曲线", xaxis_title="样本序号", yaxis_title="特征值",
            template="plotly_dark", height=450,
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0)'
        )
        return fig
    elif active_tab == "freq":
        sr = params.get("sample_rate", 25600)
        freq_type = params.get("freq_type", "fft")
        if freq_type == "fft":
            freqs = np.fft.rfftfreq(len(signal), d=1/sr)
            amps = np.abs(np.fft.rfft(signal))
        else:
            analytic = hilbert(signal)
            envelope = np.abs(analytic)
            freqs = np.fft.rfftfreq(len(envelope), d=1/sr)
            amps = np.abs(np.fft.rfft(envelope))
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=freqs, y=amps, mode='lines', fill='tozeroy'))
        fig.update_layout(
            title=f"{'包络谱' if freq_type=='envelope' else '频谱'}分析",
            xaxis_title="频率 (Hz)", yaxis_title="幅值",
            template="plotly_dark", height=450,
            paper_bgcolor='rgba(0,0,0)', plot_bgcolor='rgba(0,0,0)'
        )
        return fig
    else:
        sr = params.get("sample_rate", 25600)
        nperseg = params.get("nperseg", 256)
        f, t, Sxx = spectrogram(signal, sr, nperseg=nperseg)
        fig = go.Figure(data=go.Heatmap(
            x=t, y=f, z=10*np.log10(Sxx + 1e-8),
            colorscale='Viridis', name='STFT'
        ))
        fig.update_layout(
            title="STFT 时频图谱", xaxis_title="时间 (s)", yaxis_title="频率 (Hz)",
            template="plotly_dark", height=450,
            paper_bgcolor='rgba(0,0,0)', plot_bgcolor='rgba(0,0,0)'
        )
        return fig

def create_fault_diagnosis_page():
    return html.Div([
        dcc.Store(id="diagnosis-data-store", data={}),
        html.Div([
            html.H2("故障诊断", className="text-neon mb-1"),
            html.P("导入数据文件，选择信号通道，进行时域/频域/时频域分析", className="text-muted")
        ], className="mb-4"),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("⚙️ 分析配置", className="text-neon mb-0")),
                    dbc.CardBody([
                        dcc.Upload(
                            id="diagnosis-upload",
                            children=html.Div([
                                html.I(className="fas fa-cloud-upload-alt fa-2x mb-2", style={"opacity": 0.7}),
                                html.H5("拖拽或点击上传文件", className="mb-1"),
                                html.Small("支持 CSV / Parquet 格式", className="text-muted"),
                                html.Div(id="diagnosis-upload-filename", className="mt-2 small text-info")
                            ], className="text-center"),
                            multiple=False,
                            style={
                                'width': '100%', 'padding': '30px 20px', 'borderWidth': '2px',
                                'borderStyle': 'dashed', 'borderRadius': '15px', 'borderColor': '#2a4a6a',
                                'backgroundColor': '#0f1a24', 'cursor': 'pointer', 'transition': 'all 0.3s ease'
                            }
                        ),
                        dbc.Button(
                            [html.I(className="fas fa-trash-alt me-2"), "清除文件"],
                            id="diagnosis-clear-btn",
                            color="secondary",
                            size="sm",
                            className="mt-2 w-100",
                            outline=True,
                            style={"borderRadius": "8px"}
                        ),
                        html.Hr(className="my-3"),
                        html.Label("📡 信号通道", className="fw-bold mb-1"),
                        dcc.Dropdown(
                            id="diagnosis-channel",
                            placeholder="请先上传文件",
                            className="mb-3 dash-dropdown",
                            clearable=False
                        ),
                        dbc.Tabs([
                            dbc.Tab(label="时域分析", tab_id="time", children=[
                                html.Label("统计特征 (多选)", className="mt-2 mb-1"),
                                dcc.Dropdown(
                                    id="time-features",
                                    options=[
                                        {"label": "均值", "value": "均值"},
                                        {"label": "方差", "value": "方差"},
                                        {"label": "峰值", "value": "峰值"},
                                        {"label": "峭度", "value": "峭度"},
                                        {"label": "均方根", "value": "均方根"}
                                    ],
                                    multi=True,
                                    value=["均值", "均方根"],
                                    className="mb-2 dash-dropdown"
                                )
                            ]),
                            dbc.Tab(label="频域分析", tab_id="freq", children=[
                                html.Label("频谱类型", className="mt-2 mb-1"),
                                dcc.RadioItems(
                                    id="freq-type",
                                    options=[
                                        {"label": "频谱 (FFT)", "value": "fft"},
                                        {"label": "包络谱", "value": "envelope"}
                                    ],
                                    value="fft",
                                    inline=True,
                                    className="mb-2"
                                ),
                                html.Label("采样率 (Hz)", className="mt-1 mb-1"),
                                dbc.Input(id="freq-sr", type="number", value=25600, step=1000, className="mb-2")
                            ]),
                            dbc.Tab(label="时频域分析", tab_id="stft", children=[
                                html.Label("采样率 (Hz)", className="mt-2 mb-1"),
                                dbc.Input(id="stft-sr", type="number", value=25600, step=1000, className="mb-2"),
                                html.Small("窗口长度: 256 (固定)", className="text-muted")
                            ])
                        ], id="analysis-tabs", active_tab="time"),
                        dbc.Button(
                            [html.I(className="fas fa-chart-line me-2"), "开始分析"],
                            id="diagnosis-analyze-btn",
                            color="primary",
                            className="mt-4 w-100",
                            disabled=True,
                            style={"borderRadius": "10px", "padding": "10px"}
                        ),
                        html.Div(id="analysis-status", className="mt-3 small text-center text-muted")
                    ])
                ], className="glass-card h-100")
            ], width=12, lg=3, className="mb-3 mb-lg-0"),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("📊 分析结果", className="text-neon mb-0")),
                    dbc.CardBody(
                        id="diagnosis-results",
                        children=[
                            dbc.Alert(
                                "请上传数据文件并选择分析类型",
                                color="info",
                                className="text-center",
                                style={"backgroundColor": "#0f1a24", "borderColor": "#2a4a6a"}
                            )
                        ],
                        style={"minHeight": "550px"}
                    )
                ], className="glass-card")
            ], width=12, lg=9)
        ])
    ], style={"padding": "20px"})

def register_fault_diagnosis_callbacks(app):
    @app.callback(
        [Output("diagnosis-data-store", "data"),
         Output("diagnosis-upload-filename", "children"),
         Output("diagnosis-channel", "options"),
         Output("diagnosis-channel", "value"),
         Output("diagnosis-analyze-btn", "disabled"),
         Output("diagnosis-results", "children", allow_duplicate=True),
         Output("analysis-status", "children")],
        Input("diagnosis-upload", "contents"),
        State("diagnosis-upload", "filename"),
        prevent_initial_call=True
    )
    def handle_upload(contents, filename):
        if contents is None:
            return {}, "未上传文件", [], None, True, no_update, ""
        df = parse_uploaded_file(contents, filename)
        if df is None:
            return {}, "不支持的文件类型", [], None, True, dbc.Alert("文件格式不支持，请上传 CSV 或 Parquet", color="danger"), ""
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if not numeric_cols:
            return {}, f"已上传: {filename} (无数值列)", [], None, True, dbc.Alert("文件中没有数值型信号通道", color="warning"), ""
        store_data = {"contents": contents, "filename": filename}
        options = [{"label": col, "value": col} for col in numeric_cols]
        return store_data, f"✅ {filename} ({len(df)} 行, {len(numeric_cols)} 通道)", options, numeric_cols[0], False, dbc.Alert("文件就绪，请开始分析", color="success"), ""

    @app.callback(
        [Output("diagnosis-data-store", "data", allow_duplicate=True),
         Output("diagnosis-upload-filename", "children", allow_duplicate=True),
         Output("diagnosis-channel", "options", allow_duplicate=True),
         Output("diagnosis-channel", "value", allow_duplicate=True),
         Output("diagnosis-analyze-btn", "disabled", allow_duplicate=True),
         Output("diagnosis-results", "children", allow_duplicate=True),
         Output("analysis-status", "children", allow_duplicate=True)],
        Input("diagnosis-clear-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def clear_file(n_clicks):
        if n_clicks:
            return {}, "未上传文件", [], None, True, dbc.Alert("已清除文件，请重新上传", color="info"), ""
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update

    @app.callback(
        Output("diagnosis-results", "children", allow_duplicate=True),
        Input("diagnosis-analyze-btn", "n_clicks"),
        [State("diagnosis-data-store", "data"),
         State("diagnosis-channel", "value"),
         State("analysis-tabs", "active_tab"),
         State("time-features", "value"),
         State("freq-type", "value"),
         State("freq-sr", "value"),
         State("stft-sr", "value")],
        prevent_initial_call=True
    )
    def run_analysis(n_clicks, store_data, channel, active_tab, time_features, freq_type, stft_sr):
        if not store_data or "contents" not in store_data:
            return dbc.Alert("请先上传文件", color="warning")
        if not channel:
            return dbc.Alert("请选择信号通道", color="warning")
        df = parse_uploaded_file(store_data["contents"], store_data["filename"])
        if df is None:
            return dbc.Alert("数据解析失败", color="danger")
        if channel not in df.columns:
            return dbc.Alert(f"通道 {channel} 不存在", color="danger")
        signal = df[channel].dropna().values
        if len(signal) < 10:
            return dbc.Alert("信号过短，无法分析", color="warning")

        # 真实模式：调用后端接口 /diagnosis/analyze
        if not config.USE_MOCK:
            result = post_diagnosis_analysis(
                file_base64=store_data["contents"].split(',')[1],
                filename=store_data["filename"],
                channel=channel,
                analysis_type=active_tab,
                params={
                    "features": time_features if active_tab == "time" else None,
                    "freq_type": freq_type if active_tab == "freq" else None,
                    "sample_rate": freq_sr if active_tab == "freq" else stft_sr if active_tab == "stft" else None
                }
            )
            if "error" in result:
                return dbc.Alert(f"分析失败: {result['error']}", color="danger")
            if "figure" in result:
                try:
                    fig_json = result["figure"]
                    # 如果后端返回的是字符串，尝试解析为 JSON
                    if isinstance(fig_json, str):
                        import json
                        fig_json = json.loads(fig_json)
                    # 直接传给 dcc.Graph 渲染
                    return dcc.Graph(figure=fig_json, style={"height": "500px", "width": "100%"})
                except Exception as e:
                    return dbc.Alert(f"图表数据解析错误: {str(e)}", color="danger")
            else:
                return dbc.Alert("后端未返回图表数据", color="danger")
        # 模拟模式：前端本地计算绘图（本地调试用）
        else:
            params = {}
            if active_tab == "time":
                params["features"] = time_features
            elif active_tab == "freq":
                params["sample_rate"] = freq_sr if freq_sr else 25600
                params["freq_type"] = freq_type
            else:
                params["sample_rate"] = stft_sr if stft_sr else 25600
                params["nperseg"] = 256
            fig = generate_mock_analysis(active_tab, signal, params)
            return dcc.Graph(figure=fig, style={"height": "500px", "width": "100%"})