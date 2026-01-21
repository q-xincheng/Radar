# 本地运行指南 (Local Run Guide)

本文档说明如何在本地环境运行"行研雷达"智能体。

## 1. 环境准备

### 1.1 安装依赖

```bash
pip install -r requirements.txt
```

如果没有 `requirements.txt`，请安装以下依赖：

```bash
pip install langchain-openai
```

### 1.2 配置环境变量

在运行之前，需要配置以下环境变量。您可以选择以下任一方式：

#### 方式 1: 使用 `.env` 文件（推荐）

在项目根目录创建 `.env` 文件：

```bash
# .env 文件示例

# LLM API 配置（必需）
SILICONFLOW_API_KEY=your_api_key_here

# 数据存储配置（可选，有默认值）
DATA_DIR=data
HISTORY_DIR=data/History
DEFAULT_KEYWORD=半导体

# LLM 高级配置（可选）
LLM_MODEL=deepseek-ai/DeepSeek-V3
LLM_BASE_URL=https://api.siliconflow.cn/v1
LLM_TEMPERATURE=0.1
LLM_MAX_RETRIES=3

# OSS/S3 配置（可选，用于云端存储）
OSS_ACCESS_KEY=your_oss_access_key
OSS_ACCESS_SECRET=your_oss_access_secret
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_BUCKET=your_bucket_name
OSS_PREFIX=radar/
```

然后使用以下命令加载环境变量：

```bash
export $(cat .env | xargs)
```

#### 方式 2: 直接导出环境变量

```bash
# 必需配置
export SILICONFLOW_API_KEY="your_api_key_here"

# 可选配置（使用默认值）
export DEFAULT_KEYWORD="半导体"
export DATA_DIR="data"
export HISTORY_DIR="data/History"
```

### 1.3 重要提示

⚠️ **安全警告**：
- **切勿将包含敏感信息的 `.env` 文件提交到 Git 仓库**
- 请确保 `.env` 已添加到 `.gitignore` 文件中
- API 密钥、OSS 凭证等敏感信息仅通过环境变量传递

## 2. 运行方式

### 2.1 方式一：直接运行触发层脚本（推荐）

使用默认关键词运行：

```bash
cd /path/to/Radar
python codes/trigger_layer.py
```

使用自定义关键词运行：

```bash
python codes/trigger_layer.py "新能源汽车"
```

### 2.2 方式二：通过 Python 模块运行

```bash
cd /path/to/Radar
python -m codes.trigger_layer
```

### 2.3 方式三：在 Python 代码中调用

```python
from codes.orchestrator import run_pipeline

# 运行流程
result = run_pipeline(keyword="半导体")

# 查看结果
print("状态:", result["status"])
print("变化数量:", result["raw_changes_count"])
print("全局总结:", result["global_summary"])
print("冲突决策:", result["decisions"])
```

## 3. 输出文件说明

运行成功后，会在以下位置生成文件：

### 3.1 数据目录结构

```
data/
├── History/                        # 历史快照目录
│   ├── current_report.json        # 当前报告（作为下次对比的"旧结论"）
│   ├── report_20260121_123456.json # 历史快照 1（带时间戳）
│   └── report_20260121_234567.json # 历史快照 2（带时间戳）
└── Latest_fetch.json              # 最新一次抓取结果
```

### 3.2 文件说明

| 文件路径 | 用途 | 更新时机 |
|---------|------|---------|
| `data/History/current_report.json` | 保存上次成功的报告，作为增量对比的"旧结论"输入 | 仅在流程成功完成时更新 |
| `data/Latest_fetch.json` | 保存最新一次抓取的原始数据 | 每次采集后立即保存 |
| `data/History/report_*.json` | 带时间戳的历史快照，用于审计和回溯 | 每次成功完成后保存 |

### 3.3 可靠性保证

- ✅ **失败保护**：如果采集或分析失败，`current_report.json` 不会被覆盖
- ✅ **历史追溯**：所有成功的快照都会保留在 `History/` 目录中
- ✅ **最新数据**：`Latest_fetch.json` 始终包含最新一次抓取结果

## 4. 日志查看

运行时会输出详细的日志信息，包括：

- ✅ 流程开始/结束
- ✅ 采集到的条目数量
- ✅ 识别的变化数量
- ✅ 冲突仲裁结果
- ⚠️ 警告信息（如未采集到数据）
- ❌ 错误信息（如 API 调用失败）

示例日志输出：

```
2026-01-21 12:34:56 - orchestrator - INFO - Starting pipeline for keyword: 半导体
2026-01-21 12:34:57 - storage_layer - INFO - Latest fetch saved to data/Latest_fetch.json
2026-01-21 12:34:57 - orchestrator - INFO - Fetched 1 items
2026-01-21 12:35:00 - orchestrator - INFO - Identified 1 changes
2026-01-21 12:35:00 - conflict_resolution - INFO - Field '行业增速预测': Chose media (weight=0.7)
2026-01-21 12:35:00 - orchestrator - INFO - Resolved 1 conflicts
2026-01-21 12:35:01 - storage_layer - INFO - Current report saved to data/History/current_report.json
2026-01-21 12:35:01 - orchestrator - INFO - Pipeline completed successfully
```

## 5. 常见问题

### 5.1 环境变量未设置

**错误信息**：
```
ValueError: SILICONFLOW_API_KEY environment variable is not set
```

**解决方案**：
请确保已正确设置 `SILICONFLOW_API_KEY` 环境变量。

### 5.2 数据目录权限问题

**错误信息**：
```
PermissionError: [Errno 13] Permission denied: 'data/History'
```

**解决方案**：
```bash
mkdir -p data/History
chmod 755 data
chmod 755 data/History
```

### 5.3 首次运行无历史数据

这是正常现象。首次运行时：
- 不存在 `current_report.json`
- 系统会将所有采集内容视为"新发现"
- 后续运行将基于 `current_report.json` 进行增量对比

## 6. 阿里云 FC 部署

如需部署到阿里云函数计算（FC），请参考：

1. **环境变量配置**：在 FC 控制台的函数配置页面设置环境变量
2. **入口函数**：`codes/trigger_layer.handler`
3. **定时触发器**：在 FC 控制台配置 Cron 表达式，例如 `0 0 */6 * * *`（每 6 小时触发一次）
4. **详细部署指南**：参考 `doc/阿里云 FC 部署操作指南.md`

## 7. 数据流程说明

```
┌─────────────────┐
│  触发层         │  trigger_layer.py (handler)
│  (FC/本地)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  流程编排       │  orchestrator.py
│  (run_pipeline) │
└────────┬────────┘
         │
         ├──► 1. 采集最新资讯 (scraper_layer.py)
         │        │
         │        ▼ 保存到 Latest_fetch.json
         │
         ├──► 2. 加载旧快照 (storage_layer.py)
         │        │ 读取 History/current_report.json
         │
         ├──► 3. 增量对比 (incremental_analysis.py)
         │        │ 调用 LLM 识别变化
         │
         ├──► 4. 冲突仲裁 (conflict_resolution.py)
         │        │ 按权重选择最终结论
         │        │ 官方1.0 > 媒体0.7 > 传闻0.3
         │
         ├──► 5. 生成全局总结 (incremental_analysis.py)
         │
         └──► 6. 保存结果 (storage_layer.py)
                  ├─► History/current_report.json (覆盖)
                  └─► History/report_TIMESTAMP.json (新建)
```

## 8. 冲突仲裁权重说明

系统内置的来源权重（在 `models.py` 中硬编码）：

| 来源类型 | 权重 | 说明 |
|---------|------|------|
| `official` | 1.0 | 官方公告，权威性最高 |
| `media` | 0.7 | 权威媒体，可信度较高 |
| `rumor` | 0.3 | 市场传闻，需要核实 |

**仲裁规则**：
- 当同一指标出现多个来源的不同值时，系统自动选择权重最高的来源作为最终结论
- 其他低权重来源会被标记为"待核实"（`pending_sources`）
- 最终决策包含选中来源、待核实来源列表和 AI 生成的分析建议

---

如有其他问题，请查看项目文档或提交 Issue。
