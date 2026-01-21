# 行研雷达（Industry-Radar）

一个用于“增量追踪与更新”的行业研究动态监控智能体，包含定时巡检、增量对比和冲突仲裁的最小可行框架。

## 目标与功能
- 定时巡检：按 Cron 触发全网资讯采集
- 增量对比：识别“新发现”与“旧结论”的数值变化
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
- `storage_layer.py`：存储层（快照写入/读取）
- `incremental_analysis.py`：增量对比（识别变化字段）
- `conflict_resolution.py`：冲突仲裁（按权重选择结论）
- `orchestrator.py`：流程编排（采集→对比→仲裁→存储）

## 本地运行（角色 A 完成后）
1. 预设环境变量（避免硬编码敏感信息）
```bash
export SILICONFLOW_API_KEY="your_api_key"
export DATA_DIR="data"                    # 可选，自定义存储根目录
export LLM_MODEL="deepseek-ai/DeepSeek-V3" # 可选
export LLM_BASE_URL="https://api.siliconflow.cn/v1" # 可选
export LLM_MAX_RETRIES=3                  # 可选
```
2. 运行示例管线
```python
from orchestrator import run_pipeline

result = run_pipeline(keyword="半导体")
print(result["global_summary"])
print(result["decisions"])
```
3. 存储层会在 `data/` 下保留最新快照，并在 `data/history/` 中保留历史镜像，供增量对比使用（History/current_report.json 与 Latest_fetch.json 可从这里取得）。 

## 逐步完善清单
详见 [逐步完善清单.md](0_逐步完善清单.md)

## 备注
- 当前存储层使用本地文件模拟对象存储，后续可替换为 OSS/S3 SDK。
- 增量对比与冲突仲裁为框架占位实现，待接入 LLM 与真实数据源。
