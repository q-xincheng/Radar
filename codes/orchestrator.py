from __future__ import annotations

from typing import Dict, List

from scraper_layer import ScraperAgent
from storage_layer import StorageClient
from incremental_analysis import incremental_compare
from conflict_resolution import resolve_conflicts
from models import ChangeItem, ConflictDecision


def run_pipeline(keyword: str) -> Dict[str, List]:
    """主流程编排：采集 -> 增量对比 -> 冲突仲裁 -> 存储快照"""
    scraper = ScraperAgent()
    storage = StorageClient()

    new_items = scraper.fetch(keyword=keyword)
    old_snapshot = storage.load_latest_snapshot()

    changes: List[ChangeItem] = incremental_compare(old_snapshot, new_items)
    conflicts: List[ConflictDecision] = resolve_conflicts(changes)

    storage.save_snapshot(keyword=keyword, items=new_items)

    return {
        "changes": changes,
        "conflicts": conflicts,
    }
