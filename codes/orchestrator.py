from __future__ import annotations
import logging
from typing import Dict, List, Any

from scraper_layer import ScraperAgent
from storage_layer import StorageClient
from incremental_analysis import incremental_compare, generate_global_summary
from conflict_resolution import resolve_conflicts
from models import ChangeItem, ConflictDecision

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_pipeline(keyword: str) -> Dict[str, Any]:
    """主流程编排：采集 -> 增量对比 -> 冲突仲裁 -> 生成全局总结 -> 存储
    
    采用失败保护策略：采集失败时不覆盖旧数据
    """
    scraper = ScraperAgent()
    storage = StorageClient()
    
    try:
        # 1. 采集最新资讯
        logger.info(f"Starting data collection for keyword: {keyword}")
        new_items = scraper.fetch(keyword=keyword)
        
        if not new_items:
            logger.warning("No new items fetched, aborting pipeline")
            return {
                "keyword": keyword,
                "status": "warning",
                "message": "No new items fetched",
                "global_summary": "",
                "decisions": [],
                "raw_changes_count": 0,
                "changes": [],
                "conflicts": []
            }
        
        # 2. 保存最新抓取数据到 Latest_fetch.json
        logger.info("Saving latest fetch data")
        storage.save_latest_fetch(keyword=keyword, items=new_items)
        
        # 3. 加载旧快照（从 History/current_report.json）
        logger.info("Loading previous snapshot")
        old_snapshot = storage.load_current_report()
        
        # 4. 成员 B 的核心逻辑：增量对比
        logger.info("Performing incremental analysis")
        changes: List[ChangeItem] = incremental_compare(old_snapshot, new_items)
        
        # 5. 成员 B 的核心逻辑：冲突仲裁
        logger.info("Resolving conflicts")
        conflicts: List[ConflictDecision] = resolve_conflicts(changes)
        
        # 6. 新增：基于所有决策生成全局总评价
        logger.info("Generating global summary")
        global_report = generate_global_summary(keyword, conflicts)
        
        # 7. 存储当前采集的内容作为未来的"旧快照"
        # 只有在成功完成所有处理后才更新 current_report
        logger.info("Saving current report to history")
        storage.save_current_report(keyword=keyword, items=new_items)
        
        # 8. 同时保存一份到 data 目录（向后兼容）
        storage.save_snapshot(keyword=keyword, items=new_items)
        
        logger.info("Pipeline completed successfully")
        
        # 返回给成员 C 进行展示的完整数据包
        return {
            "keyword": keyword,
            "status": "success",
            "global_summary": global_report,  # 全局总决策
            "decisions": conflicts,           # 各指标详细决策
            "raw_changes_count": len(changes),
            "changes": changes,               # 原始变化列表
            "conflicts": conflicts            # 向后兼容
        }
    
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
        # 失败时不覆盖任何旧数据，返回错误信息
        return {
            "keyword": keyword,
            "status": "error",
            "error": str(e),
            "message": "Pipeline failed, old data preserved",
            "global_summary": "",
            "decisions": [],
            "raw_changes_count": 0,
            "changes": [],
            "conflicts": []
        }
