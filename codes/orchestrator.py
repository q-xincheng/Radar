from __future__ import annotations
from typing import Dict, List, Any

from scraper_layer import ScraperAgent
from storage_layer import StorageClient
from database_layer import DatabaseClient
from incremental_analysis import incremental_compare, generate_global_summary
from conflict_resolution import resolve_conflicts
from models import ChangeItem, ConflictDecision, now_ts

def run_pipeline(keyword: str) -> Dict[str, Any]:
    """主流程编排：采集 -> 增量对比 -> 冲突仲裁 -> 生成全局总结 -> 存储"""
    scraper = ScraperAgent()
    storage = StorageClient()
    database = DatabaseClient()

    # 生成本次运行的唯一标识
    run_id = now_ts()

    # 1. 采集最新资讯
    new_items = scraper.fetch(keyword=keyword)
    
    # 2. 加载旧快照
    old_snapshot = storage.load_latest_snapshot()

    # 3. 成员 B 的核心逻辑：增量对比
    changes: List[ChangeItem] = incremental_compare(old_snapshot, new_items)
    
    # 4. 成员 B 的核心逻辑：冲突仲裁
    conflicts: List[ConflictDecision] = resolve_conflicts(changes)

    # 5. 新增：基于所有决策生成全局总评价
    global_report = generate_global_summary(keyword, conflicts)

    # 6. 存储当前采集的内容作为未来的"旧快照"
    storage.save_snapshot(keyword=keyword, items=new_items)

    # 7. 新增：将决策结果落库（conflict_decisions + indicator_states）
    database.save_decisions(run_id=run_id, keyword=keyword, decisions=conflicts)

    # 返回给成员 C 进行展示的完整数据包
    return {
        "keyword": keyword,
        "run_id": run_id,
        "global_summary": global_report, # 全局总决策
        "decisions": conflicts,          # 各指标详细决策
        "raw_changes_count": len(changes)
    }
