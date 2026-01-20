# 行研雷达（Industry-Radar）

一个用于"增量追踪与更新"的行业研究动态监控智能体，包含定时巡检、增量对比和冲突仲裁的最小可行框架。

## 目标与功能
- 定时巡检：按 Cron 触发全网资讯采集
- 增量对比：识别"新发现"与"旧结论"的数值变化
- 冲突仲裁：按来源权重自动选择可信结论
- 历史存档：保存所有历史快照和分析报告

## 代码框架（目录结构）
```
codes/
├── trigger_layer.py       # 触发层入口（阿里云 FC handler）
├── scraper_layer.py       # 采集层（抓取资讯）
├── storage_layer.py       # 存储层（快照写入/读取、历史归档）
├── incremental_analysis.py # 增量对比（识别变化字段）
├── conflict_resolution.py  # 冲突仲裁（按权重选择结论）
├── orchestrator.py        # 流程编排（采集→对比→仲裁→存储）
├── models.py              # 数据模型与权重定义
└── config.py              # 配置项（通过环境变量）

data/                      # 数据文件夹
├── latest_fetch.json      # 最新抓取的原始数据
├── latest_report.json     # 最新分析报告（用于下一轮增量对比）
└── report_*.json          # 历史快照文件

history/                   # 历史归档文件夹
├── current_report.json    # 当前报告
└── current_report_*.json  # 历史归档的报告
```

## 环境变量配置

在运行前，请设置以下环境变量（**严禁硬编码密钥**）：

### 必需配置

```bash
# LLM API 配置（用于增量分析和全局总结）
export SILICONFLOW_API_KEY="your-api-key-here"

# 可选：自定义 LLM 配置
export LLM_MODEL="deepseek-ai/DeepSeek-V3"
export LLM_BASE_URL="https://api.siliconflow.cn/v1"
export LLM_TEMPERATURE="0.1"
export LLM_MAX_RETRIES="3"

# 可选：自定义数据目录和关键词
export DATA_DIR="data"
export HISTORY_DIR="history"
export DEFAULT_KEYWORD="半导体"
```

### 可选配置（用于阿里云 OSS 集成）

```bash
# 阿里云 OSS 配置（当前版本使用本地文件，未来可集成 OSS）
export OSS_ACCESS_KEY_ID="your-access-key-id"
export OSS_ACCESS_KEY_SECRET="your-access-key-secret"
export OSS_ENDPOINT="oss-cn-hangzhou.aliyuncs.com"
export OSS_BUCKET_NAME="your-bucket-name"
export OSS_PREFIX="radar/"
```

## 快速开始

### 1. 本地运行示例

```python
# 方式一：直接调用主流程
from codes.orchestrator import run_pipeline

result = run_pipeline(keyword="半导体")
print(result["global_summary"])
print(f"发现 {result['raw_changes_count']} 项变化")
print(f"生成 {len(result['decisions'])} 项决策")
```

```python
# 方式二：模拟 FC handler 调用
from codes.trigger_layer import simulate_cron_trigger

result = simulate_cron_trigger(keyword="人工智能")
print(result)
```

### 2. 命令行运行

```bash
# 进入代码目录
cd codes

# 确保环境变量已设置
export SILICONFLOW_API_KEY="your-api-key-here"

# 运行 FC handler 测试
python trigger_layer.py

# 或直接运行 orchestrator
python -c "from orchestrator import run_pipeline; print(run_pipeline('半导体'))"
```

### 3. 查看生成的文件

```bash
# 查看最新抓取的原始数据
cat data/latest_fetch.json

# 查看最新分析报告
cat data/latest_report.json

# 查看当前报告
cat history/current_report.json

# 列出所有历史归档
ls -lh history/current_report_*.json

# 列出所有历史快照
ls -lh data/report_*.json
```

## 核心功能详解

### 1. 阿里云 FC 入口 (trigger_layer.py)

- **handler(event, context)**: FC 入口函数
  - 支持定时触发器（Cron）
  - 支持手动触发（可通过 event 传递参数）
  - 自动解析不同格式的 event（bytes/str/dict）
  - 完整的异常处理和日志记录
  
- **simulate_cron_trigger(keyword)**: 本地模拟触发
  - 用于本地测试和调试
  - 无需部署到云端即可测试完整流程

### 2. 存储层 (storage_layer.py)

支持多层次的数据存储：

- **latest_fetch.json**: 保存最新抓取的原始数据（NewsItem 列表）
- **latest_report.json**: 保存最新的分析报告（ConflictDecision 列表）
- **history/current_report.json**: 当前报告副本
- **history/current_report_YYYYMMDD_HHMMSS.json**: 历史归档

关键方法：
- `save_snapshot()`: 保存采集快照到 data/ 和 latest_fetch.json
- `save_report()`: 保存分析报告到 latest_report.json 和 history/
- `load_latest_snapshot()`: 加载最新快照用于增量对比

### 3. 冲突仲裁 (conflict_resolution.py)

**硬编码的来源权重**：
- 官方公告 (official): **1.0**
- 权威媒体 (media): **0.7**
- 市场传闻 (rumor): **0.3**

**仲裁规则**：
1. 按权重降序排序所有冲突来源
2. 选择权重最高的作为最终结论
3. 如果存在相同权重的来源 → 标记为 **"待核实"** (to_be_verified)
4. 否则标记为 **"已确认"** (confirmed)

输出示例：
```json
{
  "field": "产能利用率",
  "final_value": "92%",
  "chosen_source": "official",
  "pending_sources": ["media", "rumor"],
  "reason": "行业景气度爆发，头部厂家产线已接近满负荷运转。",
  "status": "confirmed"
}
```

### 4. 可靠性保障

- **采集失败不覆盖旧数据**: 采集失败时抛出异常，中止流程
- **全流程异常捕获**: orchestrator.py 中所有步骤都有 try-catch
- **详细日志记录**: 使用 Python logging 模块记录所有关键步骤
- **存储失败处理**: 存储失败不影响返回结果，用户仍可查看分析

## 部署到阿里云 FC

### 使用 Serverless Devs 部署

1. 安装 Serverless Devs 工具：
```bash
npm install -g @serverless-devs/s
```

2. 配置阿里云密钥：
```bash
s config add
```

3. 部署函数：
```bash
s deploy
```

4. 设置环境变量（在阿里云控制台）：
   - 进入函数计算控制台
   - 选择您的函数
   - 配置 → 环境变量
   - 添加 `SILICONFLOW_API_KEY` 等必需变量

5. 配置定时触发器（Cron）：
   - 触发器管理 → 创建触发器
   - 触发器类型：定时触发器
   - Cron 表达式：例如 `0 0 9 * * *`（每天上午9点）
   - 触发消息：`{"keyword": "半导体"}`

## 本地开发指南

### 安装依赖

```bash
pip install langchain-openai
```

### 运行测试

```bash
# 设置环境变量
export SILICONFLOW_API_KEY="your-key"

# 进入代码目录
cd codes

# 测试完整流程
python trigger_layer.py

# 测试单独模块
python -c "from scraper_layer import ScraperAgent; print(ScraperAgent().fetch('AI'))"
```

### 调试技巧

1. **查看日志**: 所有模块都使用 logging，调整日志级别：
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

2. **检查生成的文件**: 每次运行后检查 data/ 和 history/ 文件夹

3. **模拟不同场景**:
```python
# 模拟首次运行（无历史数据）
import shutil
shutil.rmtree("data", ignore_errors=True)
shutil.rmtree("history", ignore_errors=True)

# 模拟采集失败
# 在 scraper_layer.py 的 fetch() 方法中抛出异常
```

## 输出结构示例

### FC Handler 返回结构

```json
{
  "statusCode": 200,
  "body": {
    "status": "success",
    "keyword": "半导体",
    "summary": {
      "total_changes": 3,
      "total_decisions": 3,
      "to_be_verified": 1,
      "confirmed": 2
    },
    "global_summary": "半导体行业整体处于复苏阶段...",
    "message": "成功分析 半导体 行业动态，发现 3 项变化"
  }
}
```

### latest_report.json 结构

```json
{
  "keyword": "半导体",
  "generated_at": "20260120_150530",
  "global_summary": "半导体行业整体处于复苏阶段...",
  "decisions": [
    {
      "field": "产能利用率",
      "final_value": "92%",
      "chosen_source": "official",
      "pending_sources": ["media"],
      "reason": "行业景气度爆发",
      "status": "confirmed"
    }
  ],
  "changes_count": 3
}
```

## 常见问题

### Q1: 如何切换不同的行业关键词？

```python
# 方法一：环境变量
export DEFAULT_KEYWORD="新能源汽车"

# 方法二：手动触发时传参
from codes.trigger_layer import handler
result = handler({"keyword": "人工智能"}, None)
```

### Q2: 历史文件会无限增长吗？

当前版本会保留所有历史文件。建议：
- 定期清理旧文件（例如保留最近30天）
- 或者实现 S3/OSS 生命周期策略

### Q3: 如何添加新的数据源权重？

修改 `codes/models.py`：
```python
SOURCE_WEIGHTS = {
    SourceType.OFFICIAL: 1.0,
    SourceType.MEDIA: 0.7,
    SourceType.RUMOR: 0.3,
    SourceType.ANALYST: 0.8,  # 新增分析师报告
}
```

### Q4: LLM 调用失败怎么办？

系统会自动降级：
- 增量对比失败 → 返回空列表，不影响存储
- 全局总结失败 → 使用默认模板
- 完整日志记录在控制台

## 逐步完善清单

详见 [doc/逐步完善清单.md](doc/逐步完善清单.md)

## 备注

- 当前存储层使用本地文件模拟对象存储，后续可替换为 OSS/S3 SDK。
- 增量对比与冲突仲裁依赖 LLM，需确保 API key 有效。
- 所有敏感配置必须通过环境变量提供，严禁硬编码。

## License

MIT
