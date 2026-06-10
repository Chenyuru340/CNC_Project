# CNC Tool Predictive Maintenance Frontend

## 项目简介

这是 CNC（数控机床）刀具预测性维护系统的前端部分，基于 **Dash + Plotly + Bootstrap** 开发。

### 主要功能

* 显示刀具健康度和状态
* 显示振动、电流、温度等实时数据
* 显示刀具预测分析图表
* 与后端 Agent 和数据服务交互，展示智能分析结果

---

## 技术栈

* Python 3.10+
* Dash
* dash-bootstrap-components
* Plotly
* Requests

---

## 项目结构

```text
frontend/
├── app.py                  # 前端主程序
├── pages/                  # 各个页面模块
│   ├── dashboard.py        # 仪表盘页面
│   ├── alerts.py           # 报警中心
│   ├── fault_diagnosis.py  # 故障诊断
│   └── ...
├── components/             # 可复用组件
│   ├── sidebar.py
│   ├── cards.py
│   └── charts.py
├── assets/                 # CSS、图片等静态资源
│   ├── style.css
│   └── ...
├── config.py               # 配置文件
└── requirements.txt        # Python依赖列表
```

---

## 安装依赖

在项目根目录下创建虚拟环境并安装依赖：

### Linux / Mac

```bash
python -m venv venv
source venv/bin/activate
```

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### 安装项目依赖

```bash
pip install -r requirements.txt
```

---

## 配置

在 `config.py` 中配置以下参数：

* 后端 API 地址
* Agent 服务地址
* 刷新间隔
* 其他系统配置参数

示例：

```python
BACKEND_URL = "http://127.0.0.1:8000"
AGENT_URL = "http://127.0.0.1:8002/agent"
REFRESH_INTERVAL = 5
```

---

## 启动前端

运行：

```bash
python app.py
```

默认访问地址：

```text
http://127.0.0.1:8050
```

---

## 页面功能

| 页面               | 功能说明                |
| ---------------- | ------------------- |
| Dashboard        | 刀具健康总览，关键指标展示       |
| Alerts           | 报警中心，展示异常信息         |
| Fault Diagnosis  | 故障诊断页面，支持输入问题获取智能分析 |
| Tools Management | 刀具管理界面              |
| Knowledge Base   | 知识库浏览和查询            |

---

## 使用说明

1. 确保后端服务已经部署并正常运行
2. 确保 Agent 服务已经部署并可访问
3. 确保数据库中已存在初始刀具数据
4. 启动前端服务
5. 打开浏览器访问：

```text
http://127.0.0.1:8050
```

6. 在 Dashboard 页面查看刀具状态和健康度
7. 在 Fault Diagnosis 页面输入问题获取智能分析结果

---

## 注意事项

* 前端仅负责界面展示与用户交互
* 所有智能分析逻辑由 Agent 服务提供
* CSS 文件支持自定义主题修改
* 部署到公网时建议使用 Nginx 反向代理
* 请确保前后端 API 已正确配置跨域访问策略

---

## 开发与贡献

### Fork 仓库

```bash
git clone <repository_url>
```

### 创建功能分支

```bash
git checkout -b feature/xxx
```

### 提交修改

```bash
git commit -m "Add feature xxx"
```

### 推送代码

```bash
git push origin feature/xxx
```

### 创建 Pull Request

在 GitHub 页面提交 Pull Request。

---

## 联系方式

如有问题请联系：

📧 Email：[1372808407@qq.com](mailto:1372808407@qq.com)

---

## License

This project is for academic research and learning purposes.
