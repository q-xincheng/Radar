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
    """阿里云 FC 的入口函数（兼容定时触发器 payload 与手动触发）。
    
    支持：
    - Cron 定时触发（event 可能为 bytes/str/dict）
    - 手动触发（event 为 dict，可包含自定义参数）
    - 异常处理与日志记录
    
    Args:
        event: 触发事件，可能是 bytes、str 或 dict
        context: FC 上下文对象
    
    Returns:
        Dict 包含执行结果和状态
    """
    logger.info("=== FC Handler Started ===")
    logger.info(f"Event type: {type(event)}")
    logger.info(f"Event content: {event}")
    
    keyword = DEFAULT_KEYWORD
    
    try:
        # 解析 event 参数
        if isinstance(event, (bytes, bytearray)):
            evt = json.loads(event.decode("utf-8") or "{}")
        elif isinstance(event, str):
            evt = json.loads(event or "{}")
        elif isinstance(event, dict):
            evt = event
        else:
            logger.warning(f"Unexpected event type: {type(event)}, using default")
            evt = {}
        
        # 从事件中提取关键词（如果有）
        keyword = evt.get("keyword", DEFAULT_KEYWORD)
        logger.info(f"Using keyword: {keyword}")
        
    except Exception as e:
        logger.error(f"Failed to parse event: {e}")
        evt = {}
        keyword = DEFAULT_KEYWORD
    
    try:
        # 调用主流程编排逻辑
        logger.info("Invoking run_pipeline...")
        result = run_pipeline(keyword=keyword)
        
        # 检查结果状态
        if result.get("status") == "error":
            logger.error(f"Pipeline failed: {result.get('error')}")
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "status": "error",
                    "message": result.get("error", "Unknown error"),
                    "keyword": keyword
                }, ensure_ascii=False)
            }
        
        # 构造成功响应
        decisions = result.get("decisions", [])
        changes_count = result.get("raw_changes_count", 0)
        global_summary = result.get("global_summary", "")
        
        # 统计待核实的决策
        to_be_verified_count = sum(
            1 for d in decisions 
            if hasattr(d, 'status') and d.status == "to_be_verified"
        )
        
        response = {
            "statusCode": 200,
            "body": json.dumps({
                "status": "success",
                "keyword": keyword,
                "summary": {
                    "total_changes": changes_count,
                    "total_decisions": len(decisions),
                    "to_be_verified": to_be_verified_count,
                    "confirmed": len(decisions) - to_be_verified_count
                },
                "global_summary": global_summary,
                "message": f"成功分析 {keyword} 行业动态，发现 {changes_count} 项变化"
            }, ensure_ascii=False, indent=2)
        }
        
        logger.info("=== FC Handler Completed Successfully ===")
        return response
        
    except Exception as e:
        logger.error(f"Handler failed with exception: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "status": "error",
                "message": f"执行失败: {str(e)}",
                "keyword": keyword
            }, ensure_ascii=False)
        }


def simulate_cron_trigger(keyword: str = None) -> Dict[str, Any]:
    """模拟 Cron 定时触发，用于本地测试
    
    Args:
        keyword: 可选的关键词，默认使用配置中的默认值
    
    Returns:
        FC handler 的返回结果
    """
    logger.info("=== Simulating Cron Trigger ===")
    
    # 构造模拟事件
    event = {
        "keyword": keyword or DEFAULT_KEYWORD,
        "triggerType": "cron",
        "triggerTime": "2026-01-20T15:00:00Z"
    }
    
    # 构造模拟上下文（简化版）
    class MockContext:
        request_id = "mock-request-id-12345"
        function_name = "industry-radar"
        function_handler = "trigger_layer.handler"
    
    context = MockContext()
    
    return handler(event, context)


if __name__ == "__main__":
    # 本地测试入口
    print("Testing FC handler locally...")
    result = simulate_cron_trigger()
    print(json.dumps(result, ensure_ascii=False, indent=2))
