from __future__ import annotations
from typing import Dict, List, Any
import logging

from scraper_layer import ScraperAgent
from storage_layer import StorageClient
from incremental_analysis import incremental_compare, generate_global_summary
from conflict_resolution import resolve_conflicts
from models import ChangeItem, ConflictDecision

logger = logging.getLogger(__name__)

def run_pipeline(keyword: str) -> Dict[str, Any]:
    """主流程编排：采集 -> 增量对比 -> 冲突仲裁 -> 生成全局总结 -> 存储
    
    可靠性保证：
    1. 采集失败时不覆盖 current_report
    2. 全流程异常捕获与日志
    3. 失败时返回错误状态
    """
    scraper = ScraperAgent()
    storage = StorageClient()
    
    try:
        # 1. 采集最新资讯
        logger.info(f"Starting pipeline for keyword: {keyword}")
        new_items = scraper.fetch(keyword=keyword)
        
        if not new_items:
            logger.warning(f"No items fetched for keyword: {keyword}")
            return {
                "status": "no_data",
                "keyword": keyword,
                "message": "未采集到新数据",
                "global_summary": "",
                "decisions": [],
                "raw_changes_count": 0
            }
        
        # 保存最新抓取结果
        storage.save_latest_fetch(keyword=keyword, items=new_items)
        logger.info(f"Fetched {len(new_items)} items")
        
        # 2. 加载旧快照（从 current_report）
        old_snapshot = storage.load_current_report()
        
        # 3. 成员 B 的核心逻辑：增量对比
        changes: List[ChangeItem] = incremental_compare(old_snapshot, new_items)
        logger.info(f"Identified {len(changes)} changes")
        
        # 4. 成员 B 的核心逻辑：冲突仲裁
        conflicts: List[ConflictDecision] = resolve_conflicts(changes)
        logger.info(f"Resolved {len(conflicts)} conflicts")
        
        # 5. 新增：基于所有决策生成全局总评价
        global_report = generate_global_summary(keyword, conflicts)
        
        # 6. 成功后，更新 current_report（仅在成功时覆盖）
        storage.save_current_report(keyword=keyword, items=new_items)
        
        # 7. 同时保存带时间戳的历史快照
        storage.save_snapshot(keyword=keyword, items=new_items)
        logger.info("Pipeline completed successfully")
        
        # 返回给成员 C 进行展示的完整数据包
        return {
            "status": "success",
            "keyword": keyword,
            "global_summary": global_report,  # 全局总决策
            "decisions": conflicts,           # 各指标详细决策
            "changes": changes,               # 原始变动列表
            "raw_changes_count": len(changes)
        }
        
    except Exception as e:
        logger.error(f"Pipeline failed for keyword {keyword}: {e}", exc_info=True)
        return {
            "status": "error",
            "keyword": keyword,
            "message": f"流程执行失败: {str(e)}",
            "global_summary": "",
            "decisions": [],
            "raw_changes_count": 0
        }
