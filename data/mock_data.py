
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def generate_mock_data():
    print("🔥 MOCK DATA 被调用")
    """生成更贴合PHM2010真实数据的虚拟数据集"""
    np.random.seed(42)  # 保证可重复性
    random.seed(42)

    # ========== 1. 定义刀具基础属性和传感器参数 ==========
    num_tools = 20
    tool_ids = [f"T-{i:03d}" for i in range(1, num_tools+1)]
    machines = [f"机床_{i}" for i in range(1, 6)]
    tool_types = ["铣刀", "钻头", "车刀", "镗刀"]

    # 为每把刀具随机分配基础属性
    base_machines = [random.choice(machines) for _ in range(num_tools)]
    base_types = [random.choice(tool_types) for _ in range(num_tools)]

    # 定义不同刀具类型的磨损速率差异 (模拟不同加工工况)
    wear_rate_map = {"铣刀": 1.0, "钻头": 1.2, "车刀": 0.9, "镗刀": 1.1}
    base_wear_rates = [wear_rate_map[t] for t in base_types]

    # ========== 2. 定义物理量转换与范围 ==========
    # PHM2010原始数据单位: 力(N), 振动(g), 磨损量(10⁻³ mm)
    # 模拟数据统一转换为工程单位: 振动(mm/s), 磨损量(mm)
    G_TO_MM_S = 9.8  # 1g = 9.8 mm/s² (加速度)
    # 假设初始健康状态下，三向振动信号的RMS值在 0.1g ~ 0.5g 之间 (即约 1 ~ 5 mm/s)
    # 最终失效状态时，振动RMS可能达到 1g ~ 2g 以上 (即约 10 ~ 20 mm/s)

    # ========== 3. 生成刀具当前状态数据 ==========
    tools = []
    for i in range(num_tools):
        # 生成一个介于0到1之间的健康因子，代表寿命消耗比例 (0=全新, 1=完全失效)
        # 使用Beta分布模拟不同刀具的寿命分布，部分早期失效，部分寿命较长
        health_factor = np.random.beta(a=2.0, b=5.0)  # 多数集中在0.2-0.6之间
        rul_minutes = int(2000 * (1 - health_factor)) + 10  # RUL (分钟) 10~2000
        rul_minutes = max(10, min(2000, rul_minutes))

        # 基于健康因子计算各项退化指标 (遵循磨损加剧则信号增强的物理规律)
        # 使用指数模型模拟非线性退化: signal = base + (max_signal - base) * (health_factor ^ p)
        p = 1.5  # 幂指数 >1 模拟后期加速退化

        # 振动 (mm/s) - 磨损后振动加剧
        vib_base = np.random.uniform(1.0, 3.0)  # 健康状态振动
        vib_max = np.random.uniform(12.0, 18.0) # 严重磨损状态振动
        vibration = vib_base + (vib_max - vib_base) * (health_factor ** p)
        vibration = round(vibration, 2)

        # 电流 (A) - 磨损后负载增加
        cur_base = np.random.uniform(25.0, 35.0)
        cur_max = np.random.uniform(60.0, 75.0)
        current = cur_base + (cur_max - cur_base) * (health_factor ** p)
        current = round(current, 1)

        # 磨损量 (mm) - 物理磨损量，失效阈值通常为0.3~0.5mm
        vb_max = np.random.uniform(0.35, 0.55)
        vb = vb_max * (health_factor ** p)
        vb = round(vb, 3)

        # 电流使用率 (%) - 模拟电机负载率，随磨损上升
        usage_base = np.random.uniform(30.0, 50.0)
        usage_max = np.random.uniform(85.0, 98.0)
        current_usage = usage_base + (usage_max - usage_base) * (health_factor ** p)
        current_usage = round(current_usage, 1)

        # 健康分 (0-100) - 健康分随健康因子线性下降
        health_score = max(0, min(100, 100 * (1 - health_factor)))
        health_score = round(health_score, 1)

        # 状态映射
        if health_score >= 80:
            status = "normal"
        elif health_score >= 60:
            status = "warning"
        else:
            status = "danger"

        tools.append({
            "tool_id": tool_ids[i],
            "machine": base_machines[i],
            "type": base_types[i],
            "vibration": vibration,
            "current": current,
            "vb": vb,
            "health_score": health_score,
            "status": status,
            "current_usage": current_usage,
            "rul": rul_minutes,
            "wear_rate": base_wear_rates[i]  # 隐含属性，不用于前端展示
        })

    tools_df = pd.DataFrame(tools)

    # ========== 4. 生成历史特征曲线数据 (模拟过去30天的退化趋势) ==========
    # 为每把刀具生成30天的历史数据，从较健康状态退化到当前状态
    dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
    features_history = []

    for _, tool in tools_df.iterrows():
        tool_id = tool["tool_id"]
        # 获取刀具当前退化状态 (作为退化终点)
        final_health_factor = 1 - (tool["health_score"] / 100.0)

        # 对于历史数据，假设30天前的健康因子为当前值的 10%~30%
        start_health_factor = max(0.01, final_health_factor * np.random.uniform(0.1, 0.3))

        for j, date in enumerate(dates):
            # 计算退化进度 t (0 = 历史起始, 1 = 当前)
            t = j / (len(dates) - 1)
            # 非线性退化模拟，当前退化速度为线性，早期更慢
            current_health_factor = start_health_factor + (final_health_factor - start_health_factor) * (t ** 1.2)

            # 计算各项特征值
            vib_base = tool["vibration"] * (1 - final_health_factor) ** 0.5  # 反推健康状态基准
            vib_max = tool["vibration"]
            vib = vib_base + (vib_max - vib_base) * (current_health_factor / final_health_factor)
            vib = round(vib + np.random.normal(0, 0.1), 2)  # 添加传感器噪声

            cur_base = tool["current"] * (1 - final_health_factor) ** 0.5
            cur_max = tool["current"]
            cur = cur_base + (cur_max - cur_base) * (current_health_factor / final_health_factor)
            cur = round(cur + np.random.normal(0, 0.5), 1)

            vb_max = tool["vb"]
            vb = vb_max * (current_health_factor / final_health_factor)
            vb = round(vb + np.random.normal(0, 0.005), 3)
            vb = max(0, vb)  # 磨损量非负

            # 历史健康分
            health_score = max(0, min(100, 100 * (1 - current_health_factor)))
            health_score = round(health_score + np.random.normal(0, 1.0), 1)

            # 历史使用率
            usage_base = tool["current_usage"] * (1 - final_health_factor) ** 0.5
            usage_max = tool["current_usage"]
            usage = usage_base + (usage_max - usage_base) * (current_health_factor / final_health_factor)
            usage = round(usage + np.random.normal(0, 1.0), 1)

            features_history.append({
                "tool_id": tool_id,
                "timestamp": date.strftime("%Y-%m-%d"),
                "vibration": max(0.1, vib),
                "current": max(10.0, cur),
                "vb": max(0.001, vb),
                "health_score": health_score,
                "current_usage": max(0, min(100, usage))
            })

    features_df = pd.DataFrame(features_history)

    # ========== 5. 生成报警数据 ==========
    alerts = []
    alert_levels = ["danger", "warning", "info"]
    alert_types = ["磨损超标", "剩余寿命不足", "健康度过低", "振动异常", "电流异常"]
    for i in range(15):
        alert_time = datetime.now() - timedelta(hours=random.randint(0, 72))
        level = random.choice(alert_levels)
        handle_status = random.choice(["unprocessed", "processing", "processed"])
        tool_id = random.choice(tool_ids)
        # 获取该刀具的机器
        machine = tools_df.loc[tools_df["tool_id"] == tool_id, "machine"].values[0]
        alerts.append({
            "id": i + 1,
            "time": alert_time.strftime("%Y-%m-%d %H:%M:%S"),
            "tool_id": tool_id,
            "machine": machine,
            "alert_type": random.choice(alert_types),
            "level": level,
            "description": f"刀具{tool_id}出现{random.choice(['异常振动', '温度过高', '磨损严重'])}",
            "handle_status": handle_status
        })
    alerts_df = pd.DataFrame(alerts)

    # ========== 6. 生成剩余寿命预测数据 ==========
    future_dates = pd.date_range(start=datetime.now(), periods=15, freq="D")
    rul_predictions = []
    for _, tool in tools_df.iterrows():
        tool_id = tool["tool_id"]
        health_factor = 1 - tool["health_score"] / 100.0
        for i, date in enumerate(future_dates):
            # 预测未来健康度将加速下降
            future_health_factor = health_factor * (1 + (i / 15) ** 1.5)
            pred_health = max(0, 100 * (1 - future_health_factor))
            pred_health = round(pred_health + np.random.normal(0, 2.0), 1)
            rul_predictions.append({
                "tool_id": tool_id,
                "date": date.strftime("%m-%d"),
                "predicted_health": max(0, min(100, pred_health)),
                "lower_bound": max(0, round(pred_health - 5, 1)),
                "upper_bound": min(100, round(pred_health + 5, 1))
            })
    rul_df = pd.DataFrame(rul_predictions)

    return {
        "tools": tools_df,
        "features": features_df,
        "alerts": alerts_df,
        "rul_predictions": rul_df
    }