# 行研雷达（Industry-Radar）

一个用于"增量追踪与更新"的行业研究动态监控智能体，包含定时巡检、增量对比和冲突仲裁的最小可行框架。

## 目标与功能
- **定时巡检**：按 Cron 触发全网资讯采集
- **增量对比**：识别"新发现"与"旧结论"的数值变化
- **冲突仲裁**：按来源权重自动选择可信结论
- **历史归档**：保存历史快照，支持趋势分析

## 代码框架（目录结构）
```
触发层入口：  trigger_layer.py       (阿里云 FC 入口 + 本地调试)
采集层：      scraper_layer.py       (抓取资讯)
存储层：      storage_layer.py       (历史快照 + 最新索引)
增量对比：    incremental_analysis.py (识别变化 + AI 洞察)
冲突仲裁：    conflict_resolution.py  (按权重选择结论)
流程编排：    orchestrator.py        (主流程 + 异常处理)
数据模型：    models.py              (数据结构 + 权重定义)
配置项：      config.py              (环境变量配置)
文档：        doc/本地运行指南.md     (详细运行说明)
```

## 关键特性

### 1. 存储层架构（三级存储）
- **history/** - 历史快照归档（按时间戳）
  - `report_YYYYMMDD_HHMMSS.json` - 所有历史采集记录
- **latest_fetch.json** - 最新采集的原始数据（增量对比的 new_items）
- **latest_report.json** - 最新分析报告（增量对比的 old_snapshot）

### 2. 冲突仲裁权重体系
```python
SOURCE_WEIGHTS = {
    SourceType.OFFICIAL: 1.0,   # 官方公告 - 最高权重
    SourceType.MEDIA: 0.7,      # 权威媒体
    SourceType.RUMOR: 0.3,      # 市场传闻
}
```
- 自动选择最高权重来源作为最终结论
- 低权重来源标记为"待核实"（pending_sources）

### 3. 可靠性保障
- ✅ 采集失败不覆盖旧数据
- ✅ 全流程异常捕获和日志
- ✅ 自动重试机制（最多 2 次）
- ✅ 详细的执行日志

### 4. 环境变量配置
所有敏感信息通过环境变量配置，无硬编码：
```bash
SILICONFLOW_API_KEY    # LLM API 密钥（必填）
DEFAULT_KEYWORD        # 默认关键词
DATA_DIR              # 数据存储目录
# 更多配置见 .env.example
```

## 快速开始

### 本地运行
```bash
# 1. 设置环境变量
export SILICONFLOW_API_KEY="your-api-key-here"

# 2. 运行一次 pipeline
python3 codes/trigger_layer.py

# 3. 查看输出
cat data/latest_report.json | python3 -m json.tool
```

详细说明请参考：[doc/本地运行指南.md](doc/本地运行指南.md)

### 阿里云 FC 部署
```bash
# 1. 安装 Serverless Devs CLI
npm install -g @serverless-devs/s

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入真实值

# 3. 部署
s deploy

# 4. 本地测试（模拟 FC）
s local invoke -e '{"keyword": "半导体"}'
```

### 定时触发配置
在 `s.yaml` 中配置 Cron 表达式：
```yaml
triggers:
  - name: timer-trigger
    type: timer
    config:
      cronExpression: '0 0 */6 * * *'  # 每6小时执行一次
      payload: '{"keyword": "半导体"}'
      enable: true
```

## 数据流说明

```
┌─────────────┐
│  Scraper    │  采集最新资讯 (new_items)
└──────┬──────┘
       │
       ├─────────────────────────────────────┐
       │                                     │
       ▼                                     ▼
┌─────────────────┐                  ┌──────────────┐
│ latest_fetch.json│ ◄────保存────── │  增量对比    │
└─────────────────┘                  └──────┬───────┘
                                            │
                                    读取 old_snapshot
                                            │
                                            ▼
                                     ┌──────────────┐
                                     │ 冲突仲裁      │
                                     └──────┬───────┘
                                            │
                        ┌───────────────────┴──────────────┐
                        ▼                                  ▼
                ┌─────────────────┐              ┌──────────────────┐
                │ history/         │              │ latest_report.json│
                │ report_*.json    │              └──────────────────┘
                └─────────────────┘
                  (历史归档)                       (下次对比的 old_snapshot)
```

## 开发指南

### 模块说明
- `trigger_layer.py`：Serverless 触发入口（Cron 触发器调用）
- `scraper_layer.py`：采集层（抓取资讯）
- `storage_layer.py`：存储层（快照写入/读取）
- `incremental_analysis.py`：增量对比（识别变化字段）
- `conflict_resolution.py`：冲突仲裁（按权重选择结论）
- `orchestrator.py`：流程编排（采集→对比→仲裁→存储）

### 本地调试
```python
# 方式 1: 直接运行 pipeline
from codes.orchestrator import run_pipeline
result = run_pipeline(keyword="半导体")
print(result)

# 方式 2: 模拟 FC Handler
from codes.trigger_layer import handler
result = handler({"keyword": "新能源"}, None)
print(result)

# 方式 3: 使用命令行
python3 codes/trigger_layer.py 新能源
```

## 逐步完善清单
详见 [doc/总待完善清单.md](doc/总待完善清单.md)

## 备注
- 当前存储层使用本地文件模拟对象存储，后续可替换为 OSS/S3 SDK。
- 增量对比与冲突仲裁为框架占位实现，待接入 LLM 与真实数据源。
- 完整的本地运行说明请参考 [doc/本地运行指南.md](doc/本地运行指南.md)。

## 贡献指南
详细的开发流程和注意事项请参考 [doc/预分工.md](doc/预分工.md)。
