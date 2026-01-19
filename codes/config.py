from __future__ import annotations

DATA_DIR = "data"
DEFAULT_KEYWORD = "半导体"

# 触发配置（用于 Serverless 平台的 cron 触发器）
CRON_EXAMPLE = "0 */6 * * *"  # 每 6 小时

# LLM 提示词模板（占位）
LLM_COMPARE_PROMPT = (
    "请对比以下两段信息，识别数值或结论变化，"
    "输出 JSON 数组，字段包含 field/old/new/status/source。\n"
    "旧结论: {old}\n新资讯: {new}"
)
