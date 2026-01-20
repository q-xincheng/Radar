# 行研雷达 - 快速参考指南

## 🚀 快速命令

### 本地验证（无需API Key）
```bash
python validate_architecture.py
```

### 本地运行（需要API Key）
```bash
# 设置环境变量
export SILICONFLOW_API_KEY=your_key_here

# 运行
python local_runner.py 半导体
```

### 阿里云部署
```bash
# 一次性部署
s deploy

# 查看日志
s logs -t

# 手动触发
s invoke -e '{"keyword": "半导体"}'
```

## 📂 关键文件说明

| 文件 | 说明 |
|------|------|
| `codes/trigger_layer.py` | FC入口 + 本地调用 |
| `codes/orchestrator.py` | 主流程编排 |
| `codes/storage_layer.py` | 存储层（双输入） |
| `codes/conflict_resolution.py` | 冲突仲裁（权重逻辑） |
| `s.yaml` | FC配置（24h cron） |
| `.env.example` | 环境变量模板 |
| `local_runner.py` | 本地运行脚本 |
| `validate_architecture.py` | 验证脚本 |

## 📊 数据文件

| 文件 | 用途 |
|------|------|
| `data/Latest_fetch.json` | 最新抓取数据 |
| `data/History/current_report.json` | 当前报告（旧快照） |
| `data/History/report_*.json` | 历史归档 |

## ⚙️ 环境变量

### 必需
```bash
SILICONFLOW_API_KEY=your_api_key_here
```

### 可选
```bash
DEFAULT_KEYWORD=半导体
DATA_DIR=data
OSS_ACCESS_KEY_ID=...
OSS_ACCESS_KEY_SECRET=...
```

## 🔍 验收点

- ✅ 定时触发：`trigger_layer.handler` + `s.yaml` (24h)
- ✅ 存储层：`History/current_report.json` + `Latest_fetch.json`
- ✅ 冲突仲裁：权重 1.0 > 0.7 > 0.3
- ✅ 失败保护：采集失败不覆盖旧数据
- ✅ 日志：结构化输出
- ✅ 返回：run_id, timestamp, status, error

## 🛠️ 故障排查

### 问题1：ModuleNotFoundError
```bash
pip install -r requirements.txt
```

### 问题2：API Key错误
```bash
export SILICONFLOW_API_KEY=your_key
# 或编辑 .env 文件
```

### 问题3：数据目录不存在
```bash
mkdir -p data/History
```

## 📚 详细文档

- 完整指南：`doc/角色A完整实现指南.md`
- 使用手册：`README.md`
- 部署指南：`doc/阿里云 FC 部署操作指南.md`
