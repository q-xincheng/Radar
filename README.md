# 行研雷达（Industry-Radar）

一个用于"增量追踪与更新"的行业研究动态监控智能体，包含定时巡检、增量对比和冲突仲裁的完整架构。

## 📋 目录
- [核心功能](#核心功能)
- [架构设计](#架构设计)
- [快速开始](#快速开始)
- [本地运行](#本地运行)
- [阿里云FC部署](#阿里云fc部署)
- [数据流说明](#数据流说明)
- [冲突仲裁逻辑](#冲突仲裁逻辑)
- [环境变量配置](#环境变量配置)

## 🎯 核心功能

### 1. 定时巡检
- 支持阿里云 FC 定时触发（24小时周期）
- 自动抓取全网行业资讯
- 生成唯一运行ID和时间戳

### 2. 增量对比
- 识别"新发现"与"旧结论"的数值变化
- 基于 LLM 的语义化指标提取
- 支持跨行业动态指标识别

### 3. 冲突仲裁
- **官方公告 (Weight=1.0)** > 权威媒体 (Weight=0.7) > 市场传闻 (Weight=0.3)
- 自动选择权重最高来源作为"最终结论"
- 低权重来源标记为"待核实"

### 4. 可靠性保障
- 采集失败时不覆盖旧数据
- 全流程异常捕获与结构化日志
- 返回结果包含 run_id、timestamp、status、error

## 🏗️ 架构设计

### 目录结构
```
Radar/
├── codes/
│   ├── trigger_layer.py        # 触发层：FC入口 + 本地调用
│   ├── orchestrator.py         # 流程编排：主控逻辑
│   ├── scraper_layer.py        # 采集层：资讯抓取
│   ├── storage_layer.py        # 存储层：快照管理
│   ├── incremental_analysis.py # 增量对比：LLM分析
│   ├── conflict_resolution.py  # 冲突仲裁：权重决策
│   ├── models.py              # 数据模型与权重定义
│   └── config.py              # 配置管理
├── data/                      # 数据目录
│   ├── History/              # 历史快照
│   │   ├── current_report.json   # 当前报告（旧快照）
│   │   └── report_*.json         # 历史归档
│   └── Latest_fetch.json     # 最新抓取数据
├── local_runner.py           # 本地运行脚本
├── s.yaml                   # 阿里云FC配置
├── requirements.txt         # Python依赖
└── .env.example            # 环境变量模板
```

### 关键模块说明
- `trigger_layer.py`：Serverless 触发入口 + 本地调用接口
- `storage_layer.py`：支持 History/current_report.json 与 Latest_fetch.json
- `orchestrator.py`：采集→对比→仲裁→存储，带失败保护
- `conflict_resolution.py`：硬编码权重体系，输出最终结论 + 待核实项

## 🚀 快速开始

### 前置要求
- Python 3.9+
- LLM API Key（如 SiliconFlow）

### 安装依赖
```bash
pip install -r requirements.txt
```

### 配置环境变量
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入你的 API Key
# SILICONFLOW_API_KEY=your_api_key_here
```

## 💻 本地运行

### 方式1：使用运行脚本（推荐）
```bash
# 使用默认关键词
python local_runner.py

# 指定关键词
python local_runner.py 半导体
python local_runner.py 新能源
```

### 方式2：直接调用Python模块
```python
import sys
sys.path.insert(0, 'codes')
from trigger_layer import local_invoke

# 运行巡检
result = local_invoke(keyword="半导体")
print(result["global_summary"])
print(result["status"])
```

### 方式3：使用 orchestrator
```python
import sys
sys.path.insert(0, 'codes')
from orchestrator import run_pipeline

# 运行完整流程
result = run_pipeline(keyword="半导体")
print(result["changes"])
print(result["conflicts"])
```

## ☁️ 阿里云FC部署

### 1. 准备工作
```bash
# 安装 Serverless Devs CLI
npm install -g @serverless-devs/s

# 配置阿里云凭据
s config add
```

### 2. 设置环境变量
```bash
# 方式1：导出到当前shell（临时）
export SILICONFLOW_API_KEY=your_key_here

# 方式2：写入 .env 文件（推荐）
echo "SILICONFLOW_API_KEY=your_key_here" > .env
```

### 3. 部署函数
```bash
# 部署到阿里云
s deploy

# 查看部署信息
s info

# 查看日志
s logs -t
```

### 4. 测试触发
```bash
# 手动触发一次
s invoke -e '{"keyword": "半导体"}'
```

### 5. 定时触发配置
当前配置：每24小时触发一次（每天凌晨0点）
```yaml
cronExpression: '0 0 0 * * *'  # 秒 分 时 日 月 周
```

修改触发频率：
- 每6小时：`'0 0 */6 * * *'`
- 每12小时：`'0 0 */12 * * *'`
- 每周一上午9点：`'0 0 9 * * 1'`

## 📊 数据流说明

### 增量对比的两个输入
1. **History/current_report.json**：上一次巡检的报告快照（旧结论）
2. **Latest_fetch.json**：本次抓取的最新资讯（新发现）

### 数据流转过程
```
1. [采集] 抓取最新资讯 → Latest_fetch.json
2. [读取] 加载 History/current_report.json（旧快照）
3. [对比] LLM 增量分析：旧 vs 新
4. [仲裁] 按权重解决冲突
5. [存储] 成功后更新 History/current_report.json
6. [归档] 旧的 current_report 移到 History/report_<timestamp>.json
```

### 失败保护机制
- 采集失败 → 保留旧数据，返回错误状态
- 对比失败 → 保留旧数据，返回错误状态
- 只有全流程成功才更新 History/current_report.json

## ⚖️ 冲突仲裁逻辑

### 权重体系（硬编码）
```python
SOURCE_WEIGHTS = {
    SourceType.OFFICIAL: 1.0,    # 官方公告
    SourceType.MEDIA: 0.7,       # 权威媒体
    SourceType.RUMOR: 0.3,       # 市场传闻
}
```

### 仲裁规则
1. 当同一指标出现多个来源的不同值时
2. 按权重降序排列所有来源
3. 选择权重最高的作为**最终结论**
4. 其他低权重来源标记为**待核实**

### 输出格式
```python
ConflictDecision(
    field="产能利用率",
    final_value="92%",
    chosen_source=SourceType.OFFICIAL,  # 采用官方数据
    pending_sources=[SourceType.MEDIA, SourceType.RUMOR],  # 待核实
    reason="行业景气度爆发，头部厂家产线已接近满负荷运转。"
)
```

## 🔧 环境变量配置

### 必需变量
```bash
# LLM API 密钥（必填）
SILICONFLOW_API_KEY=your_api_key_here
```

### 可选变量
```bash
# 应用配置
DEFAULT_KEYWORD=半导体    # 默认监控关键词
DATA_DIR=data            # 数据存储目录

# OSS 配置（如需使用云存储）
OSS_ACCESS_KEY_ID=your_access_key_id
OSS_ACCESS_KEY_SECRET=your_access_key_secret
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_BUCKET_NAME=your_bucket_name
OSS_PREFIX=radar/
```

### 在阿里云FC设置环境变量
1. 方式1：在 `s.yaml` 中配置
```yaml
environmentVariables:
  SILICONFLOW_API_KEY: ${env(SILICONFLOW_API_KEY)}
```

2. 方式2：在阿里云控制台设置
   - 函数计算 → 函数详情 → 配置 → 环境变量

## 🔍 返回结果格式

### 成功返回
```json
{
  "run_id": "uuid-string",
  "timestamp": "2026-01-20T14:00:00",
  "status": "success",
  "keyword": "半导体",
  "summary": {
    "raw_changes_count": 3,
    "conflicts_count": 2,
    "global_summary": "半导体行业整体向好..."
  },
  "global_summary": "半导体行业整体向好...",
  "raw_changes_count": 3,
  "conflicts_count": 2
}
```

### 失败返回
```json
{
  "run_id": "uuid-string",
  "timestamp": "2026-01-20T14:00:00",
  "status": "error",
  "error": "Pipeline execution failed: ...",
  "keyword": "半导体",
  "message": "Pipeline failed, old data preserved"
}
```

## 📝 日志格式

结构化日志输出：
```
2026-01-20 14:00:00 - trigger_layer - INFO - Handler started - run_id: xxx
2026-01-20 14:00:01 - orchestrator - INFO - Starting data collection
2026-01-20 14:00:02 - orchestrator - INFO - Saving latest fetch data
2026-01-20 14:00:03 - orchestrator - INFO - Loading previous snapshot
2026-01-20 14:00:04 - orchestrator - INFO - Performing incremental analysis
2026-01-20 14:00:10 - orchestrator - INFO - Resolving conflicts
2026-01-20 14:00:11 - orchestrator - INFO - Generating global summary
2026-01-20 14:00:13 - orchestrator - INFO - Saving current report to history
2026-01-20 14:00:14 - orchestrator - INFO - Pipeline completed successfully
```

## 🛠️ 故障排查

### 常见问题

1. **ImportError: No module named 'xxx'**
   ```bash
   pip install -r requirements.txt
   ```

2. **ValueError: SILICONFLOW_API_KEY environment variable is required**
   ```bash
   # 检查环境变量是否设置
   echo $SILICONFLOW_API_KEY
   
   # 设置环境变量
   export SILICONFLOW_API_KEY=your_key_here
   ```

3. **本地运行没有输出**
   - 检查 API Key 是否有效
   - 查看日志输出的错误信息
   - 确认网络连接正常

4. **FC部署失败**
   - 检查 s.yaml 配置是否正确
   - 确认阿里云凭据已配置：`s config get`
   - 查看详细错误：`s deploy --debug`

## 📚 扩展阅读

- [逐步完善清单](doc/进度/0_逐步完善清单.md)
- [阿里云 FC 部署操作指南](doc/阿里云%20FC%20部署操作指南.md)
- [数据契约协商](doc/数据契约协商.md)

## 🤝 团队分工

- **成员 A（架构）**：定时触发、存储层、可靠性、部署 ✅
- **成员 B（AI引擎）**：增量对比、冲突仲裁、LLM接入 ✅
- **成员 C（数据前端）**：采集层、报告展示

## 📄 许可证

本项目采用 MIT 许可证。
