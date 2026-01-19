from __future__ import annotations

from typing import Any, Dict

from orchestrator import run_pipeline
from config import DEFAULT_KEYWORD


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Serverless 触发入口。

    event: 平台传入的事件对象（包含 keyword、cron 信息等）
    context: 平台上下文
    """
    keyword = event.get("keyword") if isinstance(event, dict) else None
    keyword = keyword or DEFAULT_KEYWORD

    result = run_pipeline(keyword=keyword)
    return {
        "keyword": keyword,
        "status": "ok",
        "changes": len(result.get("changes", [])),
        "conflicts": len(result.get("conflicts", [])),
    }
