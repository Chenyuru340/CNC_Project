import re
import plotly.graph_objs as go
import pandas as pd
import io
import base64
from data.mock_data import generate_mock_data

def agent_response(question, file_info=None):
    """
    模拟智能体回答，支持文件上传和多模态返回。
    file_info 格式: {"filename": str, "content": bytes, "content_type": str}
    返回值: (answer_text, figure_or_image)
        figure_or_image 可以是 Plotly 图对象，或包含 "image_base64" 键的字典
    """
    data = generate_mock_data()
    tools_df = data['tools']
    features_df = data['features']

    question_lower = question.lower()
    answer = ""
    figure = None

    # 状态中文映射
    status_cn = {'normal': '正常', 'warning': '预警', 'danger': '危险'}

    # 处理文件内容（如果有）
    file_content = None
    if file_info:
        filename = file_info["filename"]
        content = file_info["content"]
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            answer = f"已收到图片文件 {filename}，正在分析刀具磨损状态...\n（此处为模拟分析结果：刀具表面无明显裂纹，但存在轻微磨损。）"
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=[1,2,3], y=[10,20,30], mode='lines', name='磨损趋势'))
            fig.update_layout(title="刀具磨损趋势模拟图")
            figure = fig
            return answer, figure
        elif filename.lower().endswith('.txt'):
            text = content.decode('utf-8', errors='ignore')
            file_content = text
            answer = f"已读取文件 {filename}，内容摘要：{text[:200]}..."
        elif filename.lower().endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
            answer = f"已读取CSV文件 {filename}，共 {len(df)} 行数据。"
            if 'vibration' in df.columns and 'time' in df.columns:
                fig = go.Figure(data=go.Scatter(x=df['time'], y=df['vibration'], mode='lines'))
                fig.update_layout(title="振动数据趋势")
                figure = fig
        else:
            answer = f"已收到文件 {filename}，暂不支持此类型分析。"

    # 如果没有文件，或文件处理后仍需回答问题，进行关键词匹配
    if not figure and not answer:
        if "剩余寿命" in question_lower or "rul" in question_lower:
            tool_match = re.search(r'T-\d{3}', question)
            if tool_match:
                tool_id = tool_match.group()
                tool = tools_df[tools_df['tool_id'] == tool_id]
                if not tool.empty:
                    rul = tool['rul'].values[0]
                    # 分钟转小时+分钟
                    if rul >= 60:
                        rul_display = f"{rul//60}小时{rul%60}分"
                    else:
                        rul_display = f"{rul}分钟"
                    answer = f"刀具 {tool_id} 的预测剩余寿命为 {rul_display}。"
                else:
                    answer = f"未找到刀具 {tool_id}。"
            else:
                avg_rul = tools_df['rul'].mean()
                answer = f"所有刀具的平均剩余寿命为 {avg_rul/60:.1f} 小时。"
                top5 = tools_df.nsmallest(5, 'rul')[['tool_id', 'rul']]
                fig = go.Figure(data=[go.Bar(x=top5['tool_id'], y=top5['rul']/60)])
                fig.update_layout(title="剩余寿命最短的5把刀具", xaxis_title="刀具ID", yaxis_title="剩余寿命（小时）")
                figure = fig

        elif "趋势" in question_lower or "曲线" in question_lower:
            tool_match = re.search(r'T-\d{3}', question)
            if tool_match:
                tool_id = tool_match.group()
                df = features_df[features_df['tool_id'] == tool_id]
                if not df.empty:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['vibration'], mode='lines', name='振动 (mm/s)'))
                    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['current'], mode='lines', name='电流 (A)', yaxis='y2'))
                    fig.update_layout(title=f"{tool_id} 振动与电流趋势", xaxis_title="日期",
                                      yaxis=dict(title="振动 (mm/s)"), yaxis2=dict(title="电流 (A)", overlaying='y', side='right'))
                    figure = fig
                    answer = f"这是 {tool_id} 最近30天的振动与电流趋势。"
                else:
                    answer = f"未找到刀具 {tool_id} 的数据。"
            else:
                avg_vib = features_df.groupby('timestamp')['vibration'].mean().reset_index()
                avg_cur = features_df.groupby('timestamp')['current'].mean().reset_index()
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=avg_vib['timestamp'], y=avg_vib['vibration'], mode='lines', name='平均振动 (mm/s)'))
                fig.add_trace(go.Scatter(x=avg_cur['timestamp'], y=avg_cur['current'], mode='lines', name='平均电流 (A)', yaxis='y2'))
                fig.update_layout(title="所有刀具平均振动与电流趋势", xaxis_title="日期")
                figure = fig
                answer = "这是所有刀具的平均振动与电流趋势。"

        elif "健康度" in question_lower or "状态" in question_lower:
            tool_match = re.search(r'T-\d{3}', question)
            if tool_match:
                tool_id = tool_match.group()
                tool = tools_df[tools_df['tool_id'] == tool_id]
                if not tool.empty:
                    health = tool['health_score'].values[0]
                    status = status_cn.get(tool['status'].values[0], tool['status'].values[0])
                    answer = f"刀具 {tool_id} 当前健康度为 {health} 分，状态为 {status}。"
                else:
                    answer = f"未找到刀具 {tool_id}。"
            else:
                avg_health = tools_df['health_score'].mean()
                answer = f"所有刀具平均健康度为 {avg_health:.1f} 分。"

        else:
            answer = "抱歉，我暂时无法回答这个问题。您可以询问刀具的剩余寿命、健康度或趋势曲线，或者上传图片/CSV文件进行分析。"

    return answer, figure