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

## 本地运行

### 0. 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt
```

### 1. 环境配置

**重要：** 所有敏感凭据必须通过环境变量配置，禁止硬编码到代码中。

#### 方式 A：使用 .env 文件（推荐用于本地开发）

1. 复制环境变量模板文件：
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，填入真实凭据：
```bash
# 必需项
SILICONFLOW_API_KEY="your_actual_api_key_here"

# 如果使用阿里云服务，需要配置（推荐使用 RAM 子账号）：
ALIBABA_CLOUD_ACCESS_KEY_ID="your_access_key_id"
ALIBABA_CLOUD_ACCESS_KEY_SECRET="your_access_key_secret"

# 可选配置项（已有默认值）
# LLM_MODEL="deepseek-ai/DeepSeek-V3"
# LLM_BASE_URL="https://api.siliconflow.cn/v1"
# LLM_MAX_RETRIES=3
# DATA_DIR="data"
```

3. 安装 python-dotenv（如需自动加载 .env 文件）：
```bash
pip install python-dotenv
```

#### 方式 B：手动设置环境变量

**Windows PowerShell：**
```powershell
$env:SILICONFLOW_API_KEY="your_api_key_here"
$env:ALIBABA_CLOUD_ACCESS_KEY_ID="your_access_key_id"
$env:ALIBABA_CLOUD_ACCESS_KEY_SECRET="your_access_key_secret"
```

**Linux/macOS：**
```bash
export SILICONFLOW_API_KEY="your_api_key_here"
export ALIBABA_CLOUD_ACCESS_KEY_ID="your_access_key_id"
export ALIBABA_CLOUD_ACCESS_KEY_SECRET="your_access_key_secret"
```

**可选配置项：**
```bash
export DATA_DIR="data"                    # 自定义存储根目录
export LLM_MODEL="deepseek-ai/DeepSeek-V3" # LLM 模型
export LLM_BASE_URL="https://api.siliconflow.cn/v1" # LLM API 地址
export LLM_MAX_RETRIES=3                  # LLM API 重试次数
```

### 2. 运行示例管线
```python
from orchestrator import run_pipeline

result = run_pipeline(keyword="半导体")
print(result["global_summary"])
print(result["decisions"])
```
3. 存储层会在 `data/` 下保留最新快照，并在 `data/history/` 中保留历史镜像，供增量对比使用（History/current_report.json 与 Latest_fetch.json 可从这里取得）。 

## 云端部署（阿里云函数计算 FC）

本项目已配置 Serverless Devs 支持，可快速部署到阿里云函数计算。

### 1. 安装 Serverless Devs CLI

**方式 A：npm 安装（推荐）**
```bash
npm install -g @serverless-devs/s
```

**方式 B：通过脚本安装**
```bash
curl -o- -L http://cli.so/install.sh | bash
```

安装完成后，验证安装：
```bash
s --version
```

### 2. 配置阿里云访问凭据

**重要：** 推荐使用 RAM 子账号，而非主账号 AccessKey。RAM 子账号创建方法详见 [doc/阿里云AccessKey.md](doc/阿里云AccessKey.md)。

配置凭据（选择以下任一方式）：

**方式 A：交互式配置（推荐）**
```bash
s config add
```
按提示输入：
- Alias（别名）：`aliyun-fc`
- AccessKeyID：你的 RAM 子账号 AK ID
- AccessKeySecret：你的 RAM 子账号 AK Secret
- 选择默认区域：`cn-hangzhou`

**方式 B：通过环境变量配置**
```bash
# Windows PowerShell
$env:ALIBABA_CLOUD_ACCESS_KEY_ID="your_access_key_id"
$env:ALIBABA_CLOUD_ACCESS_KEY_SECRET="your_access_key_secret"

# Linux/macOS
export ALIBABA_CLOUD_ACCESS_KEY_ID="your_access_key_id"
export ALIBABA_CLOUD_ACCESS_KEY_SECRET="your_access_key_secret"
```

### 3. 配置函数环境变量

有两种方式配置云函数所需的环境变量：

**方式 A：在 s.yaml 中配置（推荐用于非敏感配置）**

编辑 `s.yaml`，在 `function` 部分添加 `environmentVariables`：

```yaml
function:
  name: industry-radar-func
  description: 行研雷达函数
  runtime: python3.9
  handler: codes/trigger_layer.handler
  memorySize: 128
  timeout: 30
  environmentVariables:
    LLM_MODEL: deepseek-ai/DeepSeek-V3
    LLM_BASE_URL: https://api.siliconflow.cn/v1
    LLM_MAX_RETRIES: "3"
    DATA_DIR: /tmp/data
```

**方式 B：通过控制台配置（推荐用于敏感凭据）**

1. 先执行 `s deploy` 部署函数
2. 登录[阿里云函数计算控制台](https://fc.console.aliyun.com/)
3. 进入函数详情页 → "配置" → "环境变量"
4. 添加以下环境变量：
   - `SILICONFLOW_API_KEY`：你的 SiliconFlow API Key（**必需**）
   - `ALIBABA_CLOUD_ACCESS_KEY_ID`：如需访问 OSS（可选）
   - `ALIBABA_CLOUD_ACCESS_KEY_SECRET`：如需访问 OSS（可选）
5. 点击"保存"

**方式 C：使用 s.yaml + .env 结合（适合团队协作）**

在 `s.yaml` 同目录创建 `.env` 文件（已被 .gitignore 忽略）：
```bash
SILICONFLOW_API_KEY=your_actual_api_key
```

然后在 `s.yaml` 中通过 `${env(VARIABLE_NAME)}` 引用：
```yaml
function:
  environmentVariables:
    SILICONFLOW_API_KEY: ${env(SILICONFLOW_API_KEY)}
    LLM_MODEL: deepseek-ai/DeepSeek-V3
```

### 4. 部署到阿里云

在项目根目录执行：

```bash
# 部署函数和触发器
s deploy

# 仅部署函数（不含触发器）
s deploy function

# 查看部署信息
s info
```

部署成功后，会看到类似输出：
```
✔ Deploy function [industry-radar-func] successfully
  ServiceName: industry-radar-service
  FunctionName: industry-radar-func
  Handler: codes/trigger_layer.handler
  Runtime: python3.9
  Trigger: timer-trigger (cron: 0 0 */6 * * *)
```

### 5. 测试和监控

**本地调用测试：**
```bash
s invoke -e '{"keyword": "半导体"}'
```

**查看日志：**
```bash
# 实时日志
s logs -t

# 查看最近 10 分钟日志
s logs --start-time "10m ago"
```

**在控制台查看：**
1. 访问[函数计算控制台](https://fc.console.aliyun.com/)
2. 进入函数详情页
3. 查看"执行记录"和"日志查询"

### 6. 更新和维护

**更新代码：**
```bash
# 修改代码后重新部署
s deploy

# 仅更新函数代码（快速部署）
s deploy function
```

**更新环境变量：**
- 修改 s.yaml 中的 `environmentVariables` 后执行 `s deploy`
- 或在控制台直接修改（立即生效）

**删除部署：**
```bash
# 删除整个服务（包含函数和触发器）
s remove
```

### 故障排查

如果部署失败，检查：
1. ✅ Serverless Devs CLI 已正确安装（`s --version`）
2. ✅ 阿里云凭据已配置（`s config get`）
3. ✅ RAM 账号有 FC、OSS 相关权限
4. ✅ 环境变量 `SILICONFLOW_API_KEY` 已设置
5. ✅ Python 依赖已在 `codes/` 目录下（或通过层部署）

常见错误：
- `InvalidAccessKeyId.NotFound`：检查 AccessKey 是否正确
- `NoPermission`：RAM 账号缺少权限，需在 RAM 控制台授予 AliyunFCFullAccess
- `ServiceNotFound`：首次部署，s.yaml 配置的服务不存在（正常，会自动创建）

## 逐步完善清单
详见 [逐步完善清单.md](0_逐步完善清单.md)

## 备注
- 当前存储层使用本地文件模拟对象存储，后续可替换为 OSS/S3 SDK。
- 增量对比与冲突仲裁为框架占位实现，待接入 LLM 与真实数据源。
