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
    
    Args:
        event: 触发器传入的事件数据，可能是 bytes/str/dict
               定时触发器示例: {"keyword": "半导体"}
        context: FC 运行时上下文（包含 request_id 等信息）
    
    Returns:
        Dict: 包含执行状态和结果的字典
        
    Cron 触发器配置示例（在 s.yaml 中）:
        triggers:
          - name: timer-trigger
            type: timer
            config:
              cronExpression: '0 0 */6 * * *'  # 每6小时执行一次
              payload: '{"keyword": "半导体"}'
              enable: true
    
    本地调试方式：
        1. 直接调用（模拟 FC）:
           python -c "from codes.trigger_layer import handler; print(handler({}, None))"
        
        2. 带参数调用:
           python -c "from codes.trigger_layer import handler; print(handler({'keyword': '新能源'}, None))"
        
        3. 使用 s CLI 本地调用:
           s local invoke -e '{"keyword": "半导体"}'
    """
    request_id = getattr(context, 'request_id', 'local-debug') if context else 'local-debug'
    logger.info(f"函数开始执行 [request_id={request_id}]")
    
    keyword = DEFAULT_KEYWORD
    max_retries = 2  # 最大重试次数
    
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
            logger.warning(f"未识别的 event 类型: {type(event)}")
        
        keyword = evt.get("keyword", DEFAULT_KEYWORD)
        logger.info(f"目标关键词: {keyword}")
        
    except Exception as e:
        logger.error(f"解析 event 失败: {e}")
        evt = {}
        keyword = DEFAULT_KEYWORD

    # 重试逻辑：最多重试 max_retries 次
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                logger.info(f"第 {attempt} 次重试...")
            
            # 调用主流程
            result = run_pipeline(keyword=keyword)
            
            # 检查执行状态
            if result.get("status") == "error":
                logger.error(f"Pipeline 执行失败: {result.get('message', 'Unknown error')}")
                last_error = result.get('message', 'Unknown error')
                if attempt < max_retries:
                    continue  # 重试
                else:
                    # 最后一次重试失败，返回错误
                    return {
                        "statusCode": 500,
                        "status": "error",
                        "message": f"执行失败（已重试 {max_retries} 次）: {last_error}",
                        "keyword": keyword,
                        "request_id": request_id
                    }
            
            elif result.get("status") == "skipped":
                logger.warning(f"Pipeline 跳过: {result.get('message', 'No data')}")
                return {
                    "statusCode": 200,
                    "status": "skipped",
                    "message": result.get("message", "采集失败或无新数据"),
                    "keyword": keyword,
                    "request_id": request_id
                }
            
            else:
                # 成功执行
                logger.info(f"Pipeline 执行成功: 发现 {result.get('raw_changes_count', 0)} 项变化")
                return {
                    "statusCode": 200,
                    "status": "success",
                    "keyword": keyword,
                    "global_summary": result.get("global_summary", ""),
                    "raw_changes_count": result.get("raw_changes_count", 0),
                    "decisions_count": len(result.get("decisions", [])),
                    "request_id": request_id
                }
                
        except Exception as e:
            logger.error(f"Handler 异常 (attempt {attempt + 1}/{max_retries + 1}): {e}", exc_info=True)
            last_error = str(e)
            if attempt < max_retries:
                continue  # 重试
    
    # 所有重试都失败了
    logger.error(f"函数执行最终失败，已重试 {max_retries} 次")
    return {
        "statusCode": 500,
        "status": "error",
        "message": f"执行失败（已重试 {max_retries} 次）: {last_error}",
        "keyword": keyword,
        "request_id": request_id
    }


# 本地测试入口
if __name__ == "__main__":
    import sys
    
    # 支持命令行传参
    test_keyword = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_KEYWORD
    
    print(f"\n{'='*60}")
    print(f"本地测试 - 关键词: {test_keyword}")
    print(f"{'='*60}\n")
    
    # 模拟 FC 调用
    test_event = {"keyword": test_keyword}
    test_context = None
    
    result = handler(test_event, test_context)
    
    print(f"\n{'='*60}")
    print("执行结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"{'='*60}\n")
