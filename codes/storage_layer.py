from __future__ import annotations

import json
import os
from typing import List, Optional

from config import DATA_DIR
from models import NewsItem, ReportSnapshot, now_ts


class StorageClient:
    """存储层：将快照写入对象存储（此处用本地文件模拟）。"""

    def __init__(self, base_dir: str = DATA_DIR) -> None:
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self.history_dir = os.path.join(self.base_dir, "history")
        os.makedirs(self.history_dir, exist_ok=True)

    def save_snapshot(self, keyword: str, items: List[NewsItem]) -> str:
        snapshot = ReportSnapshot(keyword=keyword, collected_at=now_ts(), items=items)
        filename = f"report_{snapshot.collected_at}.json"
        path = os.path.join(self.base_dir, filename)
        snapshot_dict = self._snapshot_to_dict(snapshot)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(snapshot_dict, f, ensure_ascii=False, indent=2)
        # also keep history copy for incremental diff inputs
        history_path = os.path.join(self.history_dir, filename)
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(snapshot_dict, f, ensure_ascii=False, indent=2)
        return path

    def load_latest_snapshot(self) -> Optional[ReportSnapshot]:
        files = self.list_snapshots()
        if not files:
            return None
        latest = sorted(files)[-1]
        path = os.path.join(self.base_dir, latest)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self._dict_to_snapshot(data)

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
