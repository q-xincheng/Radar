from __future__ import annotations

import json
import logging
from typing import Any, Dict

from orchestrator import run_pipeline
from config import DEFAULT_KEYWORD

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def handler(event: Any, context: Any) -> Dict[str, Any]:
    """阿里云 FC 的入口函数（兼容定时触发器 payload）。
    
    可靠性保证：
    1. 异常捕获与日志记录
    2. 失败时返回详细错误信息
    3. 支持多种输入格式（bytes/str/dict）
    
    event 可能是 bytes / str（来自触发器 payload），也可能已是 dict。
    """
    keyword = DEFAULT_KEYWORD
    
    try:
        # 解析 event
        if isinstance(event, (bytes, bytearray)):
            evt = json.loads(event.decode("utf-8") or "{}")
        elif isinstance(event, str):
            evt = json.loads(event or "{}")
        elif isinstance(event, dict):
            evt = event
        else:
            evt = {}
        keyword = evt.get("keyword", DEFAULT_KEYWORD)
        
        logger.info(f"Handler invoked with keyword: {keyword}")
        
    except Exception as e:
        logger.warning(f"Failed to parse event, using default keyword: {e}")
        evt = {}
        keyword = DEFAULT_KEYWORD
    
    try:
        # 调用已有编排逻辑
        result = run_pipeline(keyword=keyword)
        
        # 提取结果
        status = result.get("status", "success")
        changes = result.get("changes", [])
        conflicts = result.get("decisions", [])
        
        summary = {
            "keyword": keyword,
            "status": status,
            "raw_changes_count": len(changes),
            "conflicts_count": len(conflicts),
        }
        
        # 如果流程失败，记录错误信息
        if status == "error":
            error_msg = result.get("message", "Unknown error")
            logger.error(f"Pipeline failed: {error_msg}")
            summary["error"] = error_msg
        elif status == "no_data":
            logger.warning("No data fetched")
            summary["message"] = result.get("message", "No data")
        else:
            logger.info(f"Pipeline completed successfully: {summary}")
        
        return {
            "statusCode": 200,
            "status": status,
            "global_summary": summary,
            "raw_changes_count": summary["raw_changes_count"],
            "conflicts_count": summary["conflicts_count"],
        }
        
    except Exception as e:
        logger.error(f"Unhandled exception in handler: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "status": "error",
            "global_summary": {
                "keyword": keyword,
                "status": "error",
                "error": str(e),
                "raw_changes_count": 0,
                "conflicts_count": 0,
            },
        }


if __name__ == "__main__":
    """本地测试入口"""
    import sys
    
    # 从命令行参数获取关键词，或使用默认值
    keyword = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_KEYWORD
    
    logger.info(f"Running locally with keyword: {keyword}")
    result = handler({"keyword": keyword}, None)
    
    print("\n" + "="*60)
    print("执行结果:")
    print("="*60)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("="*60)
