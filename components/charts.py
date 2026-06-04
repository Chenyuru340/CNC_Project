import plotly.graph_objs as go
import plotly.express as px
import pandas as pd

STATUS_COLOR = {
    "normal": "#20c997",
    "warning": "#ffc107",
    "danger": "#dc3545",
    "info": "#0dcaf0"
}

CHART_HEIGHT = 300
COMMON_FONT = dict(
    family="Microsoft YaHei",
    color="#f0f0f0"
)


def create_gauge(value, title="平均健康度", threshold=70):
    """仪表盘图表"""
    try:
        value = float(value)
    except Exception:
        value = 0

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={'text': title, 'font': COMMON_FONT},
        number={'font': {'color': '#20c997'}},
        domain={'x': [0, 1], 'y': [0, 1]},
        gauge={
            'axis': {'range': [0, 100], 'tickfont': COMMON_FONT},
            'bar': {'color': "#20c997"},
            'steps': [
                {'range': [0, 60], 'color': "#dc3545"},
                {'range': [60, 80], 'color': "#ffc107"},
                {'range': [80, 100], 'color': "#20c997"}
            ],
            'threshold': {
                'line': {'color': "#ff6b6b", 'width': 4},
                'thickness': 0.75,
                'value': threshold
            }
        }
    ))

    fig.update_layout(
        height=CHART_HEIGHT,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=COMMON_FONT
    )

    return fig


def create_feature_trend(df, tool_id=None):
    """振动 / 电流趋势图"""
    if df is None or df.empty:
        fig = go.Figure()
        fig.add_annotation(text="暂无数据", x=0.5, y=0.5, showarrow=False, font=COMMON_FONT)
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=CHART_HEIGHT, font=COMMON_FONT)
        return fig

    time_col = next((col for col in ["timestamp", "time", "date", "created_at"] if col in df.columns), None)
    if time_col is None:
        fig = go.Figure()
        fig.add_annotation(text="缺少时间字段", x=0.5, y=0.5, showarrow=False, font=COMMON_FONT)
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=CHART_HEIGHT, font=COMMON_FONT)
        return fig

    if tool_id and 'tool_id' in df.columns:
        df = df[df['tool_id'] == tool_id]

    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="无该刀具的趋势数据", x=0.5, y=0.5, showarrow=False, font=COMMON_FONT)
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=CHART_HEIGHT, font=COMMON_FONT)
        return fig

    df = df.copy()
    df["vibration"] = df.get("vibration", 0)
    df["current"] = df.get("current", 0)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df[time_col],
        y=df['vibration'],
        mode='lines+markers',
        name='振动 (mm/s)',
        line=dict(color='#0dcaf0'),
        marker=dict(size=4)
    ))
    fig.add_trace(go.Scatter(
        x=df[time_col],
        y=df['current'],
        mode='lines+markers',
        name='电流 (A)',
        yaxis='y2',
        line=dict(color='#ff9f4a'),
        marker=dict(size=4)
    ))

    fig.update_layout(
        title="振动与电流趋势",
        xaxis_title="时间",
        yaxis=dict(title="振动 (mm/s)", color='#0dcaf0', gridcolor='#2a3a5c'),
        yaxis2=dict(title="电流 (A)", overlaying='y', side='right', color='#ff9f4a'),
        legend=dict(x=0.01, y=0.99, font=COMMON_FONT),
        height=CHART_HEIGHT,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=COMMON_FONT
    )

    return fig


def create_rul_bar(tools_df):
    """剩余寿命 TOP5"""
    if tools_df is None or tools_df.empty:
        fig = go.Figure()
        fig.add_annotation(text="无刀具数据", x=0.5, y=0.5, showarrow=False, font=COMMON_FONT)
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=CHART_HEIGHT, font=COMMON_FONT)
        return fig

    tools_df = tools_df.copy()
    tools_df['rul'] = tools_df.get('rul', 0)
    tools_df['health_score'] = tools_df.get('health_score', 0)

    top5 = tools_df.nsmallest(5, 'rul')[['tool_id', 'rul', 'health_score']]
    if top5.empty:
        fig = go.Figure()
        fig.add_annotation(text="无剩余寿命数据", x=0.5, y=0.5, showarrow=False, font=COMMON_FONT)
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=CHART_HEIGHT, font=COMMON_FONT)
        return fig

    top5['rul_hours'] = top5['rul'] / 60

    fig = px.bar(
        top5,
        x='tool_id',
        y='rul_hours',
        color='health_score',
        color_continuous_scale='RdYlGn_r',
        title="剩余寿命最短的5把刀具"
    )

    fig.update_layout(
        yaxis_title="剩余寿命 (小时)",
        height=CHART_HEIGHT,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=COMMON_FONT
    )

    return fig


def create_degradation_pie(tools_df):
    """刀具状态分布"""
    if tools_df is None or tools_df.empty or 'status' not in tools_df.columns:
        fig = go.Figure()
        fig.add_annotation(text="无状态数据", x=0.5, y=0.5, showarrow=False, font=COMMON_FONT)
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=COMMON_FONT)
        return fig

    counts = tools_df['status'].value_counts().reset_index()
    counts.columns = ['status', 'count']
    status_cn = {'normal': '正常', 'warning': '预警', 'danger': '危险'}
    counts['status_cn'] = counts['status'].map(status_cn).fillna(counts['status'])

    fig = px.pie(
        counts,
        values='count',
        names='status_cn',
        color='status',
        color_discrete_map=STATUS_COLOR,
        title="刀具状态分布"
    )

    fig.update_layout(
        height=CHART_HEIGHT,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=COMMON_FONT
    )

    fig.update_traces(
        textfont_color='#f0f0f0',
        marker=dict(line=dict(color='#0a0f1a', width=1))
    )

    return fig