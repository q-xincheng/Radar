from __future__ import annotations
import logging
from typing import Dict, List, Any

from scraper_layer import ScraperAgent
from storage_layer import StorageClient
from incremental_analysis import incremental_compare, generate_global_summary
from conflict_resolution import resolve_conflicts
from models import ChangeItem, ConflictDecision

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_pipeline(keyword: str) -> Dict[str, Any]:
    """主流程编排：采集 -> 增量对比 -> 冲突仲裁 -> 生成全局总结 -> 存储
    
    包含完整的异常处理和可靠性保障：
    - 采集失败时不覆盖旧数据
    - 全流程异常捕获
    - 详细日志记录
    """
    logger.info(f"Starting pipeline for keyword: {keyword}")
    
    scraper = ScraperAgent()
    storage = StorageClient()
    
    new_items = []
    old_snapshot = None
    changes: List[ChangeItem] = []
    conflicts: List[ConflictDecision] = []
    global_report = ""
    
    try:
        # 1. 采集最新资讯
        logger.info("Step 1: Fetching new data...")
        try:
            new_items = scraper.fetch(keyword=keyword)
            if not new_items:
                logger.warning("No new items fetched, pipeline may not proceed")
            else:
                logger.info(f"Fetched {len(new_items)} new items")
        except Exception as e:
            logger.error(f"Failed to fetch new items: {e}")
            raise  # 采集失败应该中止流程，不覆盖旧数据
        
        # 2. 加载旧快照
        logger.info("Step 2: Loading old snapshot...")
        try:
            old_snapshot = storage.load_latest_snapshot()
            if old_snapshot:
                logger.info(f"Loaded snapshot with {len(old_snapshot.items)} items")
            else:
                logger.info("No old snapshot found, this is the first run")
        except Exception as e:
            logger.warning(f"Failed to load old snapshot (may be first run): {e}")
            old_snapshot = None
        
        # 3. 成员 B 的核心逻辑：增量对比
        logger.info("Step 3: Performing incremental comparison...")
        try:
            changes = incremental_compare(old_snapshot, new_items)
            logger.info(f"Found {len(changes)} changes")
        except Exception as e:
            logger.error(f"Incremental comparison failed: {e}")
            # 对比失败不影响存储新数据，继续执行
            changes = []
        
        # 4. 成员 B 的核心逻辑：冲突仲裁
        logger.info("Step 4: Resolving conflicts...")
        try:
            conflicts = resolve_conflicts(changes)
            logger.info(f"Resolved {len(conflicts)} conflicts")
        except Exception as e:
            logger.error(f"Conflict resolution failed: {e}")
            conflicts = []
        
        # 5. 新增：基于所有决策生成全局总评价
        logger.info("Step 5: Generating global summary...")
        try:
            global_report = generate_global_summary(keyword, conflicts)
            logger.info("Global summary generated successfully")
        except Exception as e:
            logger.error(f"Failed to generate global summary: {e}")
            global_report = f"针对 {keyword} 行业，本次巡检发现 {len(changes)} 项变动。"
        
        # 6. 存储当前采集的内容作为未来的"旧快照"
        logger.info("Step 6: Saving snapshot and report...")
        try:
            # 保存原始抓取数据
            storage.save_snapshot(keyword=keyword, items=new_items)
            # 保存分析报告
            storage.save_report(
                keyword=keyword,
                decisions=conflicts,
                global_summary=global_report,
                changes_count=len(changes)
            )
            logger.info("Snapshot and report saved successfully")
        except Exception as e:
            logger.error(f"Failed to save snapshot/report: {e}")
            # 存储失败是严重错误，但不应该影响返回结果
            # 用户仍然可以看到本次分析的结果
        
        logger.info("Pipeline completed successfully")
        
    except Exception as e:
        logger.error(f"Pipeline failed with error: {e}", exc_info=True)
        # 返回错误信息，但不抛出异常
        return {
            "keyword": keyword,
            "status": "error",
            "error": str(e),
            "global_summary": f"分析失败: {str(e)}",
            "decisions": [],
            "raw_changes_count": 0
        }
    
    # 返回给成员 C 进行展示的完整数据包
    return {
        "keyword": keyword,
        "status": "success",
        "global_summary": global_report,  # 全局总决策
        "decisions": conflicts,           # 各指标详细决策
        "raw_changes_count": len(changes)
    }
