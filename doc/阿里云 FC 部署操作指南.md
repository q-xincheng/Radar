# 🚀 阿里云 FC 部署操作指南
---

## ✅ 准备工作（成员 A）
1.  **安装 Serverless Devs CLI**
    参考官方文档：https://www.serverless-devs.com
2.  **云服务开通与权限配置**
    在阿里云控制台开通 **Function Compute** 与 **OSS**，并创建 `AccessKey/Role` 或使用 RAM 角色。
3.  **配置文件检查**
    在 `!s.yaml` 中确认 `region`、`cronExpression`、`handler` 路径是否正确。

---

## 🛠️ 部署命令（在项目根目录，PowerShell）
```powershell
# 登录 Serverless Devs（按照指引配置阿里云凭据）
s config add

# 部署函数（会上传代码并创建触发器）
s deploy
```

---

## 🧪 测试触发（部署后）
### 方式 1：本地/远程调用
```powershell
# 使用 s invoke 本地/远程调用（如果已安装并支持）
s invoke -e '{}'   # 或根据 s 文档调用远程函数
```
### 方式 2：阿里云控制台触发
在阿里云控制台里触发一次定时器的执行，查看日志。

---

## ⚙️ 必要的环境变量（成员 A 在控制台或 `!s.yaml` 中设置）

### 基础配置（必需）
- `SILICONFLOW_API_KEY`（LLM API Key）

### 存储配置（推荐使用 OSS）
推荐在生产环境使用 OSS 作为存储后端：
- `STORAGE_BACKEND=oss`
- `OSS_ENDPOINT`（如 `oss-cn-hangzhou.aliyuncs.com`）
- `OSS_BUCKET`（OSS Bucket 名称）
- `OSS_PREFIX`（可选，对象存储路径前缀，默认 `radar/`）

**认证方式：**
- **优先使用 RAM 角色**（推荐）：函数计算会自动提供临时凭证，无需配置 AK/SK
- **兜底使用 AK/SK**：如果 RAM 角色不可用，需配置：
  - `ALIBABA_CLOUD_ACCESS_KEY_ID`
  - `ALIBABA_CLOUD_ACCESS_KEY_SECRET`

### 数据库配置（可选）
- `DB_PATH`（SQLite 数据库路径，建议使用 `/tmp/radar.db`）

### 其他可选配置
- `DATA_DIR`（数据目录，默认 `data`，FC 环境建议使用 `/tmp`）
- `LLM_MODEL`、`LLM_BASE_URL`、`LLM_MAX_RETRIES`

---

## 📦 存储层注意事项（成员 A）
- **本地模式（local）**：使用本地文件系统，适用于本地开发和测试
- **OSS 模式（oss）**：使用阿里云 OSS 对象存储，适用于生产环境
  - 支持 RAM 角色认证（FC 环境推荐）
  - 支持 AK/SK 认证（本地调试兜底）
  - 需要确保函数有访问 OSS 的权限
- 本地临时目录（如 `/tmp`）不可作为持久化存储。

---

## 💾 数据库说明
系统使用 SQLite 持久化指标状态和决策历史：
- **indicator_states**：保存每个关键词+指标的最新状态
- **conflict_decisions**：保存每次运行的完整决策记录

**FC 环境注意事项：**
- 建议使用 `/tmp` 目录（如 `DB_PATH=/tmp/radar.db`）
- `/tmp` 目录会在函数实例回收时清空，如需长期保存请考虑使用 RDS 或 OSS

---

## ⏰ 定时触发器配置（Cron）

**重要说明：** Cron 触发器是云资源配置，需要在阿里云控制台手动创建，而非 Python 代码实现。

### 创建定时触发器（每 6 小时一次）

1. **登录阿里云函数计算控制台**
   - 访问：https://fc.console.aliyun.com/

2. **进入函数详情页**
   - 选择服务 → 选择函数 → 进入函数详情

3. **创建触发器**
   - 点击"触发器"标签 → "创建触发器"
   - **触发器类型**：选择"定时触发器"
   - **触发器名称**：自定义（如 `timer-6h`）
   - **Cron 表达式**：`0 0 */6 * * *`（每 6 小时触发一次）
     - 格式：`秒 分 时 日 月 星期`
     - 示例：
       - `0 0 */6 * * *`：每 6 小时（0:00, 6:00, 12:00, 18:00）
       - `0 0 0 * * *`：每天 0 点
       - `0 0 */4 * * *`：每 4 小时
   - **触发消息（Payload）**：输入 JSON 格式的 keyword
     ```json
     {"keyword": "半导体"}
     ```
   - 点击"确定"

4. **验证触发器**
   - 在触发器列表中查看创建的触发器
   - 可以手动触发一次测试功能是否正常

### Cron 表达式示例

```
# 格式：秒 分 时 日 月 星期
0 0 */6 * * *   # 每 6 小时
0 30 8 * * *    # 每天 8:30
0 0 9 * * 1     # 每周一 9:00
0 0 0 1 * *     # 每月 1 号 0:00
```

---

## 🔍 成员 B（你）需要确认
- `incremental_analysis.py`、`conflict_resolution.py` 不使用本地硬编码路径（现在已改为接受传入数据）。
- `trigger_layer.py` 已按 FC 要求返回可被监控系统捕获的 JSON（已更新）。
- `storage_layer.py` 已支持 OSS 和 local 两种后端。
- `database_layer.py` 已实现 SQLite 数据持久化。

---

## 🎯 可继续推进的任务
如果你愿意，我可以继续：
1.  把 `storage_layer.py` 改为 OSS 示例实现（需要 OSS 凭据与占位配置）。
2.  生成一个更完整的 `!s.yaml`（包含环境变量、Layer 配置与 OSS 权限示例）。
3.  写一份给成员 A 的逐步部署说明文档（含最小权限策略示例）。

---

要不要我帮你生成**带详细注释的 OSS 版 storage_layer.py 代码**？这样你就能直接替换当前的本地文件版本。