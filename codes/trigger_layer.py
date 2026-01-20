from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict
from datetime import datetime

from orchestrator import run_pipeline
from config import DEFAULT_KEYWORD

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def handler(event: Any, context: Any) -> Dict[str, Any]:
    """阿里云 FC 的入口函数（兼容定时触发器 payload）。
    
    增强功能：
    - 生成唯一 run_id
    - 记录时间戳
    - 完整的异常捕获和错误报告
    - 结构化日志输出
    
    event 可能是 bytes / str（来自触发器 payload），也可能已是 dict。
    """
    run_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    keyword = DEFAULT_KEYWORD

    logger.info(f"Handler started - run_id: {run_id}, timestamp: {timestamp}")

    try:
        # 解析 event 参数
        if isinstance(event, (bytes, bytearray)):
            evt = json.loads(event.decode("utf-8") or "{}")
        elif isinstance(event, str):
            evt = json.loads(event or "{}")
        elif isinstance(event, dict):
            evt = event
        else:
            evt = {}
            
        keyword = evt.get("keyword", DEFAULT_KEYWORD)
        logger.info(f"Processing keyword: {keyword}")
    except Exception as e:
        logger.error(f"Failed to parse event: {e}")
        evt = {}
        keyword = DEFAULT_KEYWORD

    try:
        # 调用已有编排逻辑
        result = run_pipeline(keyword=keyword)
        
        # 检查pipeline是否成功
        pipeline_status = result.get("status", "unknown")
        
        if pipeline_status == "error":
            logger.error(f"Pipeline failed: {result.get('error', 'Unknown error')}")
            return {
                "run_id": run_id,
                "timestamp": timestamp,
                "status": "error",
                "error": result.get("error", "Pipeline execution failed"),
                "keyword": keyword,
                "message": result.get("message", "Pipeline failed"),
            }
        
        changes = result.get("changes", [])
        conflicts = result.get("conflicts", [])
        
        logger.info(f"Pipeline completed - Changes: {len(changes)}, Conflicts: {len(conflicts)}")

        summary = {
            "keyword": keyword,
            "raw_changes_count": len(changes),
            "conflicts_count": len(conflicts),
            "global_summary": result.get("global_summary", ""),
        }

        return {
            "run_id": run_id,
            "timestamp": timestamp,
            "status": "success",
            "keyword": keyword,
            "summary": summary,
            "raw_changes_count": summary["raw_changes_count"],
            "conflicts_count": summary["conflicts_count"],
            "global_summary": summary["global_summary"],
        }
        
    except Exception as e:
        logger.error(f"Handler error: {str(e)}", exc_info=True)
        return {
            "run_id": run_id,
            "timestamp": timestamp,
            "status": "error",
            "error": str(e),
            "keyword": keyword,
            "message": "Handler execution failed"
        }


def local_invoke(keyword: str = None) -> Dict[str, Any]:
    """本地调用入口，用于测试和调试
    
    使用示例:
        from trigger_layer import local_invoke
        result = local_invoke(keyword="半导体")
        print(result)
    """
    event = {"keyword": keyword or DEFAULT_KEYWORD}
    # context 在本地调用时为 None
    return handler(event, None)


if __name__ == "__main__":
    # 本地测试入口
    print("=" * 60)
    print("本地测试模式 - 行研雷达")
    print("=" * 60)
    result = local_invoke()
    print("\n运行结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
