# CNC Tool Condition Monitoring - Frontend

## 部署步骤

### 1. 安装 Python 3.9+

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 确认后端地址

已在 `api_client.py` 中配置为：
```python
BASE_URL = "http://192.168.130.191:8000/api"
```
如果后端 IP 变了，修改这一行即可。

### 4. 启动

Windows: 双击 `run.bat`

或命令行:
```bash
python app.py
```

### 5. 打开浏览器

http://localhost:8050

## 离线演示模式

如果后端不可用，编辑 `config.py`：
```python
USE_MOCK = True
```