from __future__ import annotations

import json
import os
import logging
import shutil
from typing import List, Optional, Dict, Any

from config import DATA_DIR, HISTORY_DIR
from models import NewsItem, ReportSnapshot, now_ts, ConflictDecision

logger = logging.getLogger(__name__)


class StorageClient:
    """存储层：将快照写入对象存储（此处用本地文件模拟）。
    
    支持：
    - history/ 文件夹保存历史镜像
    - latest_fetch.json 保存最新抓取的原始数据
    - latest_report.json 保存最新的分析报告（用于下一轮增量对比）
    - 历史归档到 history/current_report_YYYYMMDD_HHMMSS.json
    """

    def __init__(self, base_dir: str = DATA_DIR, history_dir: str = HISTORY_DIR) -> None:
        self.base_dir = base_dir
        self.history_dir = history_dir
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.history_dir, exist_ok=True)
        
        self.latest_fetch_path = os.path.join(self.base_dir, "latest_fetch.json")
        self.latest_report_path = os.path.join(self.base_dir, "latest_report.json")
        self.current_report_path = os.path.join(self.history_dir, "current_report.json")

    def save_snapshot(self, keyword: str, items: List[NewsItem]) -> str:
        """保存快照，包括历史归档"""
        snapshot = ReportSnapshot(keyword=keyword, collected_at=now_ts(), items=items)
        
        # 1. 保存到 data/ 文件夹（向后兼容）
        filename = f"report_{snapshot.collected_at}.json"
        path = os.path.join(self.base_dir, filename)
        snapshot_dict = self._snapshot_to_dict(snapshot)
        
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(snapshot_dict, f, ensure_ascii=False, indent=2)
            
            # 2. 保存最新抓取的原始数据到 latest_fetch.json
            with open(self.latest_fetch_path, "w", encoding="utf-8") as f:
                json.dump(snapshot_dict, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Snapshot saved to {path} and {self.latest_fetch_path}")
            return path
        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")
            raise

    def save_report(self, keyword: str, decisions: List[ConflictDecision], 
                    global_summary: str, changes_count: int) -> str:
        """保存分析报告，并归档到 history/ 文件夹"""
        timestamp = now_ts()
        report = {
            "keyword": keyword,
            "generated_at": timestamp,
            "global_summary": global_summary,
            "decisions": [
                {
                    "field": d.field,
                    "final_value": d.final_value,
                    "chosen_source": d.chosen_source.value,
                    "pending_sources": [s.value for s in d.pending_sources],
                    "reason": d.reason,
                    "status": "to_be_verified" if len(d.pending_sources) > 0 and 
                             self._has_equal_weights(d) else "confirmed"
                }
                for d in decisions
            ],
            "changes_count": changes_count
        }
        
        try:
            # 1. 如果存在旧的 current_report.json，归档到 history/
            if os.path.exists(self.current_report_path):
                archive_name = f"current_report_{timestamp}.json"
                archive_path = os.path.join(self.history_dir, archive_name)
                shutil.copy2(self.current_report_path, archive_path)
                logger.info(f"Archived old report to {archive_path}")
            
            # 2. 保存新报告到 latest_report.json
            with open(self.latest_report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            # 3. 同时保存到 history/current_report.json
            with open(self.current_report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Report saved to {self.latest_report_path} and {self.current_report_path}")
            return self.latest_report_path
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
            raise
    
    def _has_equal_weights(self, decision: ConflictDecision) -> bool:
        """检查是否存在权重相等的冲突来源"""
        from models import SOURCE_WEIGHTS
        if not decision.pending_sources:
            return False
        chosen_weight = SOURCE_WEIGHTS.get(decision.chosen_source, 0.0)
        for source in decision.pending_sources:
            if SOURCE_WEIGHTS.get(source, 0.0) == chosen_weight:
                return True
        return False

    def load_latest_snapshot(self) -> Optional[ReportSnapshot]:
        """加载最新快照，优先从 latest_report.json 读取"""
        # 优先尝试从 latest_report.json 加载
        if os.path.exists(self.latest_report_path):
            try:
                with open(self.latest_report_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # latest_report.json 是分析报告，需要转换格式
                # 这里我们尝试从 latest_fetch.json 读取原始数据
                if os.path.exists(self.latest_fetch_path):
                    with open(self.latest_fetch_path, "r", encoding="utf-8") as f:
                        fetch_data = json.load(f)
                    return self._dict_to_snapshot(fetch_data)
            except Exception as e:
                logger.warning(f"Failed to load from latest files: {e}")
        
        # 回退到旧方式：从 data/ 文件夹读取最新的 report_*.json
        files = self.list_snapshots()
        if not files:
            return None
        latest = sorted(files)[-1]
        path = os.path.join(self.base_dir, latest)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return self._dict_to_snapshot(data)
        except Exception as e:
            logger.error(f"Failed to load snapshot from {path}: {e}")
            return None

    def list_snapshots(self) -> List[str]:
        if not os.path.isdir(self.base_dir):
            return []
        return [f for f in os.listdir(self.base_dir) if f.startswith("report_") and f.endswith(".json")]

    def _snapshot_to_dict(self, snapshot: ReportSnapshot) -> dict:
        return {
            "keyword": snapshot.keyword,
            "collected_at": snapshot.collected_at,
            "items": [
                {
                    "title": i.title,
                    "content": i.content,
                    "source": i.source.value,
                    "url": i.url,
                    "published_at": i.published_at,
                }
                for i in snapshot.items
            ],
        }

    def _dict_to_snapshot(self, data: dict) -> ReportSnapshot:
        items = [
            NewsItem(
                title=i.get("title", ""),
                content=i.get("content", ""),
                source=i.get("source", "media"),
                url=i.get("url"),
                published_at=i.get("published_at"),
            )
            for i in data.get("items", [])
        ]
        # 兼容 source 字符串
        for item in items:
            if not hasattr(item.source, "value"):
                item.source = item.source  # type: ignore[assignment]
        return ReportSnapshot(
            keyword=data.get("keyword", ""),
            collected_at=data.get("collected_at", ""),
            items=items,
        )
