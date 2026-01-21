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
存储门面： storage_lib.py          （稳定 API 接口）
增量对比： incremental_analysis.py
冲突仲裁： conflict_resolution.py
流程编排： orchestrator.py
数据模型与权重： models.py
配置项： config.py
日志配置： logging_setup.py         （统一日志配置）
告警模块： alerting.py             （钉钉 + 邮件告警）
逐步完善清单： 逐步完善清单.md
```

## 关键模块说明
- `trigger_layer.py`：Serverless 触发入口（Cron 触发器调用）
- `scraper_layer.py`：采集层（抓取资讯）
- `storage_layer.py`：存储层（快照写入/读取）
- `storage_lib.py`：存储门面（稳定 API 接口，供团队调用）
- `incremental_analysis.py`：增量对比（识别变化字段）
- `conflict_resolution.py`：冲突仲裁（按权重选择结论）
- `orchestrator.py`：流程编排（采集→对比→仲裁→存储，含数据保护）
- `logging_setup.py`：统一日志配置（支持从环境变量读取日志级别）
- `alerting.py`：告警模块（钉钉机器人 + QQ 邮箱通知）

## 本地运行

### 0. 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt
```

### 快速本地运行步骤（逐步）
按下面的顺序即可在本地完整跑通任务：

1. **准备环境变量**  
   - 复制模板：`cp .env.example .env`（如无模板，可直接创建 `.env`）。  
   - 填入至少一项：`SILICONFLOW_API_KEY=your_actual_api_key_here`。  
   - 如需阿里云能力，追加：`ALIBABA_CLOUD_ACCESS_KEY_ID`、`ALIBABA_CLOUD_ACCESS_KEY_SECRET`。  
   - 可选：`DATA_DIR` 自定义数据目录。

2. **加载环境变量**（二选一）  
   - 推荐：在终端导出：`export SILICONFLOW_API_KEY=...`（最简单、无需额外依赖）；  
   - 如需 `.env` 自动加载，可手动安装 `python -m pip install python-dotenv`，然后在自定义脚本开头加入 `from dotenv import load_dotenv; load_dotenv()`（仓库默认未内置）。

3. **运行调试链路（纯本地模拟，不依赖外部 API）**  
   - `python codes/mock_test_b.py`  
   该脚本会：模拟旧快照 -> 生成新资讯 -> 增量对比 -> 冲突仲裁 -> 生成总决策，并在控制台打印结果。

4. **运行真实管线（需要有效 API Key，确保已加载环境变量且 Key 可用，否则会抛出缺少 API Key 的错误）**  
   ```python
   from codes.orchestrator import run_pipeline
   result = run_pipeline(keyword="半导体")
   print(result["global_summary"])
   print(result["decisions"])
   ```
   首次运行会在 `data/` 下生成当前快照，并在后续运行时进行增量对比。

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
# LOG_LEVEL="INFO"  # 日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL

# 存储后端配置（可选）
# STORAGE_BACKEND="local"  # 或 "oss" 使用阿里云 OSS

# OSS 配置（当 STORAGE_BACKEND=oss 时需要）
# OSS_ENDPOINT="oss-cn-hangzhou.aliyuncs.com"
# OSS_BUCKET="your-bucket-name"
# OSS_PREFIX="radar/"

# 告警配置（可选，用于采集失败通知）
# 钉钉机器人告警
# DINGTALK_WEBHOOK_URL="https://oapi.dingtalk.com/robot/send?access_token=your_token"
# DINGTALK_SECRET=""  # 可选，当前版本不使用加签

# 邮件告警（QQ 邮箱）
# SMTP_HOST="smtp.qq.com"
# SMTP_PORT="465"  # 465 for SSL (推荐), 587 for STARTTLS
# SMTP_USERNAME="your_email@qq.com"
# SMTP_PASSWORD="your_qq_mail_authorization_code"  # QQ 邮箱授权码
# SMTP_TO="recipient1@example.com,recipient2@example.com"  # 多个收件人用逗号分隔
# SMTP_FROM="your_email@qq.com"  # 可选，默认使用 SMTP_USERNAME

# SQLite 数据库路径（可选）
# DB_PATH="data/radar.db"
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

# 存储后端配置
export STORAGE_BACKEND="local"            # 或 "oss" 使用阿里云 OSS

# OSS 配置（当 STORAGE_BACKEND=oss 时需要）
export OSS_ENDPOINT="oss-cn-hangzhou.aliyuncs.com"
export OSS_BUCKET="your-bucket-name"
export OSS_PREFIX="radar/"

# SQLite 数据库路径
export DB_PATH="data/radar.db"            # 本地持久化路径

# 日志配置
export LOG_LEVEL="INFO"                   # 日志级别

# 告警配置（可选）
export DINGTALK_WEBHOOK_URL="https://oapi.dingtalk.com/robot/send?access_token=your_token"
export SMTP_HOST="smtp.qq.com"
export SMTP_PORT="465"
export SMTP_USERNAME="your_email@qq.com"
export SMTP_PASSWORD="your_authorization_code"
export SMTP_TO="recipient@example.com"
```

### 告警配置

系统支持采集失败时的实时告警通知，帮助及时发现和处理问题。

#### 支持的告警渠道

1. **钉钉机器人告警**
   - 适用场景：团队协作、即时通知
   - 配置方法：
     ```bash
     export DINGTALK_WEBHOOK_URL="https://oapi.dingtalk.com/robot/send?access_token=your_token"
     ```
   - 获取 webhook：在钉钉群中添加自定义机器人，复制 webhook URL
   - 注意：当前版本不使用加签功能（`DINGTALK_SECRET` 参数保留但不使用）

2. **QQ 邮箱告警**
   - 适用场景：正式通知、记录存档
   - 支持端口：
     - **465（SSL）**：推荐使用，安全性更高
     - **587（STARTTLS）**：备选方案
   - 配置方法：
     ```bash
     export SMTP_HOST="smtp.qq.com"
     export SMTP_PORT="465"                    # 或 587
     export SMTP_USERNAME="your_email@qq.com"
     export SMTP_PASSWORD="your_authorization_code"  # 使用授权码，非密码
     export SMTP_TO="recipient1@example.com,recipient2@example.com"  # 多个收件人用逗号分隔
     # export SMTP_FROM="your_email@qq.com"   # 可选，默认使用 SMTP_USERNAME
     ```

#### QQ 邮箱授权码获取步骤

QQ 邮箱使用授权码代替密码进行第三方登录，获取步骤：

1. 登录 [QQ 邮箱网页版](https://mail.qq.com/)
2. 点击顶部 **设置** → **账户**
3. 找到 **POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务** 部分
4. 开启 **POP3/SMTP服务** 或 **IMAP/SMTP服务**
5. 按提示发送短信验证后，系统会显示 **授权码**
6. 复制授权码并配置到 `SMTP_PASSWORD` 环境变量中

注意事项：
- 授权码是一串16位字符（如 `abcdefghijklmnop`），不是 QQ 密码
- 授权码要妥善保管，不要泄露给他人
- 如果忘记授权码，可以重新生成（旧授权码会失效）

#### 告警触发条件

系统会在以下情况自动发送告警：

1. **采集失败**：`scraper.fetch()` 抛出异常
2. **采集返回空数据**：为防止误覆盖旧快照，空数据视为失败
3. **流程执行异常**：其他导致任务失败的异常情况

告警消息会自动脱敏，不会泄露敏感信息（如 API Key、密码等）。

#### 可靠性保护机制

- **不覆盖旧数据**：采集失败或返回空数据时，不会保存新快照，避免误伤历史数据
- **异常隔离**：告警模块异常不会影响主流程，确保系统稳定性
- **自动重试**：LLM API 调用支持自动重试（通过 `LLM_MAX_RETRIES` 配置）

### 存储和数据库配置

#### 存储后端

系统支持两种存储后端（通过 `STORAGE_BACKEND` 环境变量切换）：

1. **local（默认）**：本地文件存储
   - 适用场景：本地开发和测试
   - 数据保存在 `${DATA_DIR}` 目录下
   - 无需额外配置

2. **oss**：阿里云 OSS 对象存储
   - 适用场景：生产环境、云函数部署
   - **认证方式**：
     - 优先使用 RAM 角色（适用于函数计算环境，无需配置 AK/SK）
     - 兜底使用 AK/SK（本地调试时需配置 `ALIBABA_CLOUD_ACCESS_KEY_ID` 和 `ALIBABA_CLOUD_ACCESS_KEY_SECRET`）
   - **必需环境变量**：
     - `OSS_ENDPOINT`：OSS 访问域名（如 `oss-cn-hangzhou.aliyuncs.com`）
     - `OSS_BUCKET`：OSS Bucket 名称
   - **可选配置**：
     - `OSS_PREFIX`：对象存储路径前缀（默认 `radar/`）

#### SQLite 数据库

系统使用 SQLite 持久化指标状态和决策历史：

- **指标状态表（indicator_states）**：保存每个关键词+指标的最新状态
- **决策历史表（conflict_decisions）**：保存每次运行的完整决策记录
- **数据库路径**：通过 `DB_PATH` 环境变量配置（默认 `${DATA_DIR}/radar.db`）
  - 本地开发：使用 `data/radar.db`
  - 函数计算环境：建议使用 `/tmp/radar.db`（注意 `/tmp` 目录会在函数实例回收时清空）


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
