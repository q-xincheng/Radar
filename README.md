# 行研雷达（Industry-Radar）

一个用于"增量追踪与更新"的行业研究动态监控智能体，包含定时巡检、增量对比和冲突仲裁的最小可行框架。

## 目标与功能
- 定时巡检：按 Cron 触发全网资讯采集
- 增量对比：识别"新发现"与"旧结论"的数值变化
- 冲突仲裁：按来源权重自动选择可信结论

## 代码框架（目录结构）
```
触发层入口： trigger_layer.py
采集层： scraper_layer.py
存储层： storage_layer.py
增量对比： incremental_analysis.py
冲突仲裁： conflict_resolution.py
流程编排： orchestrator.py
数据模型与权重： models.py
配置项： config.py
逐步完善清单： 逐步完善清单.md
```

## 关键模块说明
- `trigger_layer.py`：Serverless 触发入口（Cron 触发器调用）
- `scraper_layer.py`：采集层（抓取资讯）
- `storage_layer.py`：存储层（快照写入/读取，支持 History/current_report.json 模式）
- `incremental_analysis.py`：增量对比（识别变化字段）
- `conflict_resolution.py`：冲突仲裁（按权重选择结论：官方1.0 > 媒体0.7 > 传闻0.3）
- `orchestrator.py`：流程编排（采集→对比→仲裁→存储，带失败保护）

## 快速开始

### 本地运行
详细的本地运行指南请参考：**[LOCAL_RUN.md](LOCAL_RUN.md)**

快速示例：
```bash
# 1. 配置环境变量
export SILICONFLOW_API_KEY="your_api_key_here"

# 2. 运行触发层
python codes/trigger_layer.py

# 3. 查看输出
# - data/History/current_report.json (当前报告)
# - data/Latest_fetch.json (最新抓取)
```

### Python 代码调用
```python
from orchestrator import run_pipeline

result = run_pipeline(keyword="半导体")
print(result["status"])           # 运行状态
print(result["global_summary"])   # 全局总结
print(result["decisions"])        # 冲突决策
```

## 冲突仲裁权重说明

系统内置来源权重（硬编码于 `models.py`）：
- 官方公告 (`official`): **1.0** - 最高权威
- 权威媒体 (`media`): **0.7** - 较高可信度
- 市场传闻 (`rumor`): **0.3** - 待核实

当同一指标出现多个来源的冲突数据时，系统自动选择权重最高的来源作为最终结论，其他来源标记为"待核实"。

## 环境变量配置

必需配置：
- `SILICONFLOW_API_KEY`: LLM API 密钥

可选配置（有默认值）：
- `DATA_DIR`: 数据目录（默认：data）
- `HISTORY_DIR`: 历史快照目录（默认：data/History）
- `DEFAULT_KEYWORD`: 默认关键词（默认：半导体）

详见 [.env.example](.env.example)

## 数据目录结构

```
data/
├── History/                        # 历史快照目录
│   ├── current_report.json        # 当前报告（作为下次对比的"旧结论"）
│   └── report_TIMESTAMP.json      # 历史快照（带时间戳）
└── Latest_fetch.json              # 最新抓取结果
```

## 阿里云 FC 部署

详细部署指南请参考：`doc/阿里云 FC 部署操作指南.md`

## 逐步完善清单
详见 [逐步完善清单.md](0_逐步完善清单.md)

## 示例脚本

- `examples/conflict_resolution_demo.py`: 冲突仲裁权重系统演示

## 备注
- ✅ 存储层支持 History/ 目录和 current_report.json 模式
- ✅ 失败时不覆盖 current_report，确保数据可靠性
- ✅ 全流程异常捕获与日志记录
- ✅ 环境变量配置，无硬编码敏感信息
- ✅ 冲突仲裁自动选择高权重来源，低权重标记为"待核实"
