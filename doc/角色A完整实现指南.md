# 行研雷达 - 角色A（架构）完整实现指南

## 📋 实现概述

本文档说明"角色A（架构）"任务的完整实现，包括所有功能、配置、部署和使用方法。

## ✅ 已实现功能清单

### 1. 阿里云函数计算 FC 定时触发入口

#### 实现位置
- **文件**: `codes/trigger_layer.py`
- **函数**: `handler(event, context)`
- **配置**: `s.yaml`

#### 功能特性
- ✅ 标准 FC handler 接口：`handler(event, context)`
- ✅ 支持定时触发器 payload 解析（JSON/bytes/str）
- ✅ 生成唯一 run_id（UUID）
- ✅ 记录时间戳（ISO 8601 格式）
- ✅ 完整的异常捕获和错误报告
- ✅ 结构化日志输出（INFO/ERROR 级别）
- ✅ 本地调用入口：`local_invoke(keyword)`
- ✅ 独立测试脚本：`local_runner.py`

#### 定时触发配置
```yaml
# s.yaml
cronExpression: '0 0 0 * * *'  # 每24小时（每天凌晨0点）
payload: '{"keyword": "半导体"}'
```

### 2. 存储层历史镜像与最新索引

#### 实现位置
- **文件**: `codes/storage_layer.py`
- **类**: `StorageClient`

#### 核心功能

##### A. History/current_report.json（历史快照）
```python
# 保存当前报告
storage.save_current_report(keyword="半导体", items=news_items)

# 加载当前报告（用于增量对比）
old_snapshot = storage.load_current_report()
```

**特性**:
- ✅ 保存为 `data/History/current_report.json`
- ✅ 保存前自动归档旧版本到 `data/History/report_<timestamp>.json`
- ✅ 只有全流程成功才更新此文件
- ✅ 失败时保留旧数据

##### B. Latest_fetch.json（最新抓取）
```python
# 保存最新抓取数据
storage.save_latest_fetch(keyword="半导体", items=news_items)

# 加载最新抓取数据
latest = storage.load_latest_fetch()
```

**特性**:
- ✅ 保存为 `data/Latest_fetch.json`
- ✅ 每次采集立即更新
- ✅ 用于增量对比的"新数据"输入

##### C. 增量对比的两个输入
```python
# 在 orchestrator.py 中
old_snapshot = storage.load_current_report()      # 旧结论
latest_fetch = storage.load_latest_fetch()        # 新资讯
changes = incremental_compare(old_snapshot, latest_fetch)
```

### 3. 配置管理（环境变量）

#### 实现位置
- **文件**: `codes/config.py`, `.env.example`

#### 环境变量列表

##### 必需变量
```bash
SILICONFLOW_API_KEY=your_api_key_here  # LLM API 密钥（必填）
```

##### 可选变量
```bash
# 应用配置
DEFAULT_KEYWORD=半导体    # 默认关键词
DATA_DIR=data            # 数据目录

# OSS 配置（云存储）
OSS_ACCESS_KEY_ID=your_access_key_id
OSS_ACCESS_KEY_SECRET=your_access_key_secret
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_BUCKET_NAME=your_bucket_name
OSS_PREFIX=radar/
```

#### 配置方式

**方式1：.env 文件（本地开发）**
```bash
cp .env.example .env
# 编辑 .env 文件
```

**方式2：环境变量（Shell）**
```bash
export SILICONFLOW_API_KEY=your_key
```

**方式3：s.yaml（阿里云FC）**
```yaml
environmentVariables:
  SILICONFLOW_API_KEY: ${env(SILICONFLOW_API_KEY)}
```

### 4. 冲突仲裁优先级逻辑

#### 实现位置
- **文件**: `codes/conflict_resolution.py`, `codes/models.py`
- **函数**: `resolve_conflicts(changes)`

#### 权重体系（硬编码）
```python
# models.py
SOURCE_WEIGHTS = {
    SourceType.OFFICIAL: 1.0,    # 官方公告
    SourceType.MEDIA: 0.7,       # 权威媒体
    SourceType.RUMOR: 0.3,       # 市场传闻
}
```

#### 仲裁规则
1. **分组**: 按指标字段（field）分组所有变化项
2. **排序**: 按来源权重降序排列
3. **选择**: 权重最高的作为"最终结论"
4. **标记**: 其他低权重来源标记为"待核实"（`pending_sources`）

#### 输出格式
```python
ConflictDecision(
    field="产能利用率",              # 指标名称
    final_value="92%",              # 最终值
    chosen_source=SourceType.OFFICIAL,  # 采用来源（权重最高）
    pending_sources=[SourceType.MEDIA, SourceType.RUMOR],  # 待核实来源
    reason="官方公告确认产能利用率达到92%"  # AI 生成的洞察
)
```

### 5. 可靠性保障

#### A. 失败保护机制

**实现位置**: `codes/orchestrator.py`

```python
try:
    # 1. 采集最新资讯
    new_items = scraper.fetch(keyword=keyword)
    if not new_items:
        return {"status": "warning", "message": "No new items fetched"}
    
    # 2. 保存最新抓取
    storage.save_latest_fetch(keyword=keyword, items=new_items)
    
    # 3-6. 处理流程...
    
    # 7. 只有成功才更新 current_report
    storage.save_current_report(keyword=keyword, items=new_items)
    
    return {"status": "success", ...}
    
except Exception as e:
    logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
    # 失败时不覆盖任何旧数据
    return {"status": "error", "error": str(e)}
```

#### B. 结构化日志

**日志级别**: INFO, WARNING, ERROR

**日志格式**:
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

**示例输出**:
```
2026-01-20 14:00:00 - trigger_layer - INFO - Handler started - run_id: xxx
2026-01-20 14:00:01 - orchestrator - INFO - Starting data collection
2026-01-20 14:00:02 - orchestrator - ERROR - Pipeline failed: xxx
```

#### C. 返回结果包含排障信息

**成功返回**:
```json
{
  "run_id": "uuid-string",
  "timestamp": "2026-01-20T14:00:00",
  "status": "success",
  "keyword": "半导体",
  "summary": {...}
}
```

**失败返回**:
```json
{
  "run_id": "uuid-string",
  "timestamp": "2026-01-20T14:00:00",
  "status": "error",
  "error": "详细错误信息",
  "keyword": "半导体",
  "message": "Pipeline failed, old data preserved"
}
```

### 6. 文档

#### 已更新/创建的文档
- ✅ **README.md**: 完整使用指南
  - 快速开始
  - 本地运行（3种方式）
  - 阿里云FC部署
  - 数据流说明
  - 冲突仲裁逻辑
  - 环境变量配置
  - 故障排查

- ✅ **.env.example**: 环境变量模板
- ✅ **validate_architecture.py**: 架构验证脚本
- ✅ **本文档**: 完整实现指南

## 🚀 部署和使用

### 本地运行（无需API Key的验证）
```bash
# 验证架构和存储层
python validate_architecture.py
```

### 本地运行（完整流程，需要API Key）
```bash
# 方式1：使用运行脚本
export SILICONFLOW_API_KEY=your_key
python local_runner.py 半导体

# 方式2：使用 .env 文件
cp .env.example .env
# 编辑 .env，填入 API Key
python local_runner.py
```

### 阿里云 FC 部署
```bash
# 1. 安装 Serverless Devs
npm install -g @serverless-devs/s

# 2. 配置阿里云凭据
s config add

# 3. 设置环境变量
export SILICONFLOW_API_KEY=your_key

# 4. 部署
s deploy

# 5. 测试
s invoke -e '{"keyword": "半导体"}'

# 6. 查看日志
s logs -t
```

## 📊 数据流验证

### 运行验证脚本后的目录结构
```
data/
├── History/
│   ├── current_report.json       # 当前报告（旧快照）
│   └── report_20260120_*.json    # 历史归档
└── Latest_fetch.json             # 最新抓取
```

### 验证结果示例
```
✅ 存储层验证通过:
  - History/current_report.json 创建成功
  - Latest_fetch.json 创建成功

✅ 冲突仲裁验证通过:
  - 权重配置: Official(1.0) > Media(0.7) > Rumor(0.3)
  - 选择最高权重来源作为最终结论
  - 低权重来源标记为待核实

✅ 数据流验证通过:
  采集 → 保存最新 → 读取历史 → 对比 → 仲裁 → 保存当前
```

## 🔍 验收标准确认

| 验收点 | 状态 | 说明 |
|--------|------|------|
| 定时触发入口清晰 | ✅ | trigger_layer.py handler + s.yaml (24h cron) |
| History/current_report.json | ✅ | 存储层正确生成和读取 |
| Latest_fetch.json | ✅ | 存储层正确生成和读取 |
| 冲突仲裁权重逻辑 | ✅ | 1.0 > 0.7 > 0.3，输出最终结论与待核实项 |
| 本地可运行 | ✅ | local_runner.py + validate_architecture.py |
| 失败保护 | ✅ | 采集失败时不覆盖旧数据 |
| 结构化日志 | ✅ | INFO/ERROR 级别，带时间戳 |
| 返回排障信息 | ✅ | run_id, timestamp, status, error |
| 环境变量配置 | ✅ | .env.example + config.py |
| 文档完整 | ✅ | README.md + 部署指南 + 验证脚本 |

## 📝 关键代码示例

### 定时触发入口
```python
# codes/trigger_layer.py
def handler(event, context):
    run_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    
    try:
        result = run_pipeline(keyword=keyword)
        return {
            "run_id": run_id,
            "timestamp": timestamp,
            "status": "success",
            ...
        }
    except Exception as e:
        return {
            "run_id": run_id,
            "timestamp": timestamp,
            "status": "error",
            "error": str(e)
        }
```

### 存储层双输入
```python
# codes/storage_layer.py
class StorageClient:
    def save_latest_fetch(self, keyword, items):
        # 保存到 Latest_fetch.json
        
    def load_current_report(self):
        # 从 History/current_report.json 读取
```

### 冲突仲裁
```python
# codes/conflict_resolution.py
def resolve_conflicts(changes):
    for field, items in grouped.items():
        items_sorted = sorted(items, key=lambda x: SOURCE_WEIGHTS[x.source], reverse=True)
        chosen = items_sorted[0]  # 权重最高
        pending = [i.source for i in items_sorted[1:]]  # 待核实
        return ConflictDecision(chosen_source=chosen.source, pending_sources=pending)
```

## 🎯 后续扩展建议

1. **OSS 集成**: 将 StorageClient 扩展为支持阿里云 OSS
2. **数据库持久化**: 参考 doc/进度/0_成员B已完成的工作.md 中的表结构建议
3. **监控告警**: 接入钉钉/邮件告警
4. **重试机制**: 增加指数退避重试逻辑
5. **性能优化**: 批量处理、并发采集

## 📞 联系与支持

- 技术问题：查看 README.md 故障排查部分
- 部署问题：查看 doc/阿里云 FC 部署操作指南.md
- 架构验证：运行 `python validate_architecture.py`

---

**文档版本**: 1.0  
**最后更新**: 2026-01-20  
**负责人**: 成员 A（架构）
