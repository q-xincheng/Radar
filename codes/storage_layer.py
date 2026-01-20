from __future__ import annotations

import json
import os
import shutil
from typing import List, Optional

from config import DATA_DIR, HISTORY_DIR
from models import NewsItem, ReportSnapshot, now_ts


class StorageClient:
    """存储层：将快照写入对象存储（此处用本地文件模拟）。
    
    支持：
    - History/current_report.json: 当前报告快照
    - Latest_fetch.json: 最新抓取的原始数据
    - 历史归档在 History/ 目录
    """

    def __init__(self, base_dir: str = DATA_DIR) -> None:
        self.base_dir = base_dir
        self.history_dir = HISTORY_DIR
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.history_dir, exist_ok=True)
        
    def save_latest_fetch(self, keyword: str, items: List[NewsItem]) -> str:
        """保存最新抓取的原始数据到 Latest_fetch.json"""
        snapshot = ReportSnapshot(keyword=keyword, collected_at=now_ts(), items=items)
        path = os.path.join(self.base_dir, "Latest_fetch.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._snapshot_to_dict(snapshot), f, ensure_ascii=False, indent=2)
            return path
        except Exception as e:
            raise IOError(f"Failed to save latest fetch: {e}")

    def load_latest_fetch(self) -> Optional[ReportSnapshot]:
        """加载最新抓取的数据"""
        path = os.path.join(self.base_dir, "Latest_fetch.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return self._dict_to_snapshot(data)
        except Exception as e:
            print(f"Warning: Failed to load latest fetch: {e}")
            return None

    def save_current_report(self, keyword: str, items: List[NewsItem]) -> str:
        """保存当前报告到 History/current_report.json
        
        注意：只有在成功完成所有处理后才调用此方法
        """
        snapshot = ReportSnapshot(keyword=keyword, collected_at=now_ts(), items=items)
        current_path = os.path.join(self.history_dir, "current_report.json")
        
        # 如果存在旧的 current_report，先归档
        if os.path.exists(current_path):
            try:
                with open(current_path, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                old_ts = old_data.get("collected_at", "unknown")
                archive_path = os.path.join(self.history_dir, f"report_{old_ts}.json")
                shutil.copy2(current_path, archive_path)
            except Exception as e:
                print(f"Warning: Failed to archive old report: {e}")
        
        # 保存新的 current_report
        try:
            with open(current_path, "w", encoding="utf-8") as f:
                json.dump(self._snapshot_to_dict(snapshot), f, ensure_ascii=False, indent=2)
            return current_path
        except Exception as e:
            raise IOError(f"Failed to save current report: {e}")
    
    def load_current_report(self) -> Optional[ReportSnapshot]:
        """加载当前报告快照（用于增量对比）"""
        path = os.path.join(self.history_dir, "current_report.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return self._dict_to_snapshot(data)
        except Exception as e:
            print(f"Warning: Failed to load current report: {e}")
            return None

    def save_snapshot(self, keyword: str, items: List[NewsItem]) -> str:
        """保存快照到 data 目录（保持向后兼容）"""
        snapshot = ReportSnapshot(keyword=keyword, collected_at=now_ts(), items=items)
        filename = f"report_{snapshot.collected_at}.json"
        path = os.path.join(self.base_dir, filename)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._snapshot_to_dict(snapshot), f, ensure_ascii=False, indent=2)
            return path
        except Exception as e:
            raise IOError(f"Failed to save snapshot: {e}")

    def load_latest_snapshot(self) -> Optional[ReportSnapshot]:
        """加载最新快照（优先从 History/current_report.json 读取）"""
        # 优先读取 History/current_report.json
        current = self.load_current_report()
        if current:
            return current
            
        # 回退到 data 目录的最新文件
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
            print(f"Warning: Failed to load snapshot: {e}")
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
