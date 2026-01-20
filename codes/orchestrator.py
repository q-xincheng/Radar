from __future__ import annotations
from typing import Dict, List, Any
import logging

from scraper_layer import ScraperAgent
from storage_layer import StorageClient
from incremental_analysis import incremental_compare, generate_global_summary
from conflict_resolution import resolve_conflicts
from models import ChangeItem, ConflictDecision

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_pipeline(keyword: str) -> Dict[str, Any]:
    """主流程编排：采集 -> 增量对比 -> 冲突仲裁 -> 生成全局总结 -> 存储
    
    流程说明：
    1. 采集最新资讯 (new_items)
    2. 保存到 latest_fetch.json（失败保护：如果采集失败，不会覆盖）
    3. 加载旧快照 (old_snapshot) 用于增量对比
    4. 执行增量对比，识别变化
    5. 冲突仲裁，选择最可信结论
    6. 生成全局总结
    7. 保存快照到 history/ 归档
    8. 保存最新报告到 latest_report.json
    
    异常处理：全流程捕获，确保一个环节失败不影响其他环节
    """
    scraper = ScraperAgent()
    storage = StorageClient()

    try:
        # 1. 采集最新资讯
        logger.info(f"开始采集关键词: {keyword}")
        new_items = scraper.fetch(keyword=keyword)
        
        if not new_items:
            logger.warning("采集失败或无新数据，跳过本次处理")
            return {
                "status": "skipped",
                "keyword": keyword,
                "message": "采集失败或无新数据",
                "global_summary": "",
                "decisions": [],
                "raw_changes_count": 0
            }
        
        logger.info(f"采集到 {len(new_items)} 条数据")
        
        # 2. 保存最新采集数据（失败保护：只有采集成功才保存）
        try:
            storage.save_latest_fetch(keyword=keyword, items=new_items)
        except Exception as e:
            logger.error(f"保存最新采集数据失败: {e}")
            # 继续处理，但记录错误
        
        # 3. 加载旧快照（优先使用 latest_report，其次使用 history 最新）
        old_snapshot = None
        try:
            old_report = storage.load_current_report()
            if old_report:
                # 从 latest_report 构建 old_snapshot（用于增量对比）
                logger.info("使用 latest_report 作为旧快照")
                # 将 decisions 转换为类似 snapshot 的格式供对比
                old_snapshot = old_report
            else:
                # 如果没有 latest_report，尝试从 history 加载
                old_snapshot = storage.load_latest_snapshot()
                if old_snapshot:
                    logger.info("使用 history 最新快照作为旧快照")
        except Exception as e:
            logger.error(f"加载旧快照失败: {e}")
            old_snapshot = None

        # 4. 成员 B 的核心逻辑：增量对比
        logger.info("开始增量对比")
        changes: List[ChangeItem] = []
        try:
            changes = incremental_compare(old_snapshot, new_items)
            logger.info(f"识别到 {len(changes)} 项变化")
        except Exception as e:
            logger.error(f"增量对比失败: {e}")
            changes = []
        
        # 5. 成员 B 的核心逻辑：冲突仲裁
        logger.info("开始冲突仲裁")
        conflicts: List[ConflictDecision] = []
        try:
            conflicts = resolve_conflicts(changes)
            logger.info(f"仲裁得出 {len(conflicts)} 项决策")
        except Exception as e:
            logger.error(f"冲突仲裁失败: {e}")
            conflicts = []

        # 6. 新增：基于所有决策生成全局总评价
        global_report = ""
        try:
            global_report = generate_global_summary(keyword, conflicts)
            logger.info(f"全局总结: {global_report[:100]}...")
        except Exception as e:
            logger.error(f"生成全局总结失败: {e}")
            global_report = "生成总结失败"

        # 7. 存储当前采集的内容到 history/ 归档
        try:
            storage.save_snapshot(keyword=keyword, items=new_items)
        except Exception as e:
            logger.error(f"保存历史快照失败: {e}")
            # 继续处理
        
        # 8. 保存最新报告到 latest_report.json（用于下次增量对比）
        try:
            storage.save_latest_report(
                keyword=keyword, 
                decisions=conflicts,
                global_summary=global_report
            )
        except Exception as e:
            logger.error(f"保存最新报告失败: {e}")
            # 继续处理

        # 返回给成员 C 进行展示的完整数据包
        return {
            "status": "success",
            "keyword": keyword,
            "global_summary": global_report, # 全局总决策
            "decisions": conflicts,          # 各指标详细决策
            "raw_changes_count": len(changes)
        }
        
    except Exception as e:
        logger.error(f"pipeline 执行失败: {e}", exc_info=True)
        return {
            "status": "error",
            "keyword": keyword,
            "message": str(e),
            "global_summary": "",
            "decisions": [],
            "raw_changes_count": 0
        }
