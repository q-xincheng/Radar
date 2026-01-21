from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

from orchestrator import run_pipeline
from config import DEFAULT_KEYWORD
from logging_setup import setup_logging
from alerting import notify_failure

# Configure logging
logger = logging.getLogger(__name__)


def handler(event: Any, context: Any) -> Dict[str, Any]:
    """阿里云 FC 的入口函数（兼容定时触发器 payload）。

    event 可能是 bytes / str（来自触发器 payload），也可能已是 dict。
    keyword 获取优先级：event.keyword > env.DEFAULT_KEYWORD > config.DEFAULT_KEYWORD
    """
    # 设置统一日志配置
    setup_logging(context)
    
    # Get default keyword when event has no keyword
    # Priority: env.DEFAULT_KEYWORD > config.DEFAULT_KEYWORD
    default_keyword = os.getenv("DEFAULT_KEYWORD", DEFAULT_KEYWORD)
    keyword = default_keyword

    try:
        # Parse event to extract keyword
        if isinstance(event, (bytes, bytearray)):
            evt = json.loads(event.decode("utf-8") or "{}")
        elif isinstance(event, str):
            evt = json.loads(event or "{}")
        elif isinstance(event, dict):
            evt = event
        else:
            evt = {}
        keyword = evt.get("keyword", default_keyword)
    except Exception as e:
        logger.warning(f"Failed to parse event, using default keyword: {e}")
        evt = {}
        keyword = default_keyword

    try:
        # 调用已有编排逻辑
        result = run_pipeline(keyword=keyword)

        # 正确读取 orchestrator 返回的字段
        raw_changes_count = result.get("raw_changes_count", 0)
        decisions = result.get("decisions", [])
        conflicts_count = len(decisions)
        run_id = result.get("run_id", "")
        global_summary = result.get("global_summary", "")

        return {
            "status": "success",
            "keyword": keyword,
            "run_id": run_id,
            "raw_changes_count": raw_changes_count,
            "conflicts_count": conflicts_count,
            "global_summary": global_summary,
        }
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}", exc_info=True)
        
        # 构造告警上下文
        from alerting import _sanitize_dict
        alert_context = {
            "keyword": keyword,
            "error": str(e),
            "error_type": type(e).__name__,
        }
        
        # 尝试获取 run_id（如果在异常前已生成）
        try:
            from models import now_ts
            alert_context["run_id"] = now_ts()
        except Exception:
            pass
        
        # 添加脱敏后的 event 信息
        if evt:
            alert_context["event"] = _sanitize_dict(evt if isinstance(evt, dict) else {})
        
        # 发送告警通知
        notify_failure(alert_context)
        
        return {
            "status": "error",
            "keyword": keyword,
            "error": str(e),
        }
