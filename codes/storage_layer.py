from __future__ import annotations

import json
import os
import logging
from typing import List, Optional

from config import DATA_DIR, HISTORY_DIR, CURRENT_REPORT_FILE, LATEST_FETCH_FILE
from models import NewsItem, ReportSnapshot, now_ts

logger = logging.getLogger(__name__)


class StorageClient:
    """存储层：将快照写入对象存储（此处用本地文件模拟）。
    
    支持两种文件模式：
    - History/current_report.json: 保存上次成功的报告（作为旧结论）
    - Latest_fetch.json: 保存最新一次抓取结果
    """

    def __init__(self, base_dir: str = DATA_DIR, history_dir: str = HISTORY_DIR) -> None:
        self.base_dir = base_dir
        self.history_dir = history_dir
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.history_dir, exist_ok=True)
        logger.info(f"StorageClient initialized with base_dir={base_dir}, history_dir={history_dir}")

    def save_snapshot(self, keyword: str, items: List[NewsItem]) -> str:
        """保存快照到历史文件夹（带时间戳）。"""
        snapshot = ReportSnapshot(keyword=keyword, collected_at=now_ts(), items=items)
        filename = f"report_{snapshot.collected_at}.json"
        path = os.path.join(self.history_dir, filename)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._snapshot_to_dict(snapshot), f, ensure_ascii=False, indent=2)
            logger.info(f"Snapshot saved to {path}")
            return path
        except Exception as e:
            logger.error(f"Failed to save snapshot to {path}: {e}")
            raise

    def save_current_report(self, keyword: str, items: List[NewsItem]) -> str:
        """保存当前报告到 History/current_report.json（作为下次的旧结论）。"""
        snapshot = ReportSnapshot(keyword=keyword, collected_at=now_ts(), items=items)
        path = os.path.join(self.history_dir, CURRENT_REPORT_FILE)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._snapshot_to_dict(snapshot), f, ensure_ascii=False, indent=2)
            logger.info(f"Current report saved to {path}")
            return path
        except Exception as e:
            logger.error(f"Failed to save current report to {path}: {e}")
            raise

    def save_latest_fetch(self, keyword: str, items: List[NewsItem]) -> str:
        """保存最新抓取结果到 Latest_fetch.json。"""
        snapshot = ReportSnapshot(keyword=keyword, collected_at=now_ts(), items=items)
        path = os.path.join(self.base_dir, LATEST_FETCH_FILE)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._snapshot_to_dict(snapshot), f, ensure_ascii=False, indent=2)
            logger.info(f"Latest fetch saved to {path}")
            return path
        except Exception as e:
            logger.error(f"Failed to save latest fetch to {path}: {e}")
            raise

    def load_current_report(self) -> Optional[ReportSnapshot]:
        """加载 History/current_report.json 作为旧结论。"""
        path = os.path.join(self.history_dir, CURRENT_REPORT_FILE)
        if not os.path.exists(path):
            logger.info(f"No current report found at {path}")
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"Current report loaded from {path}")
            return self._dict_to_snapshot(data)
        except Exception as e:
            logger.error(f"Failed to load current report from {path}: {e}")
            return None

    def load_latest_snapshot(self) -> Optional[ReportSnapshot]:
        """向后兼容：加载最新快照（优先使用 current_report）。"""
        return self.load_current_report()

    def list_snapshots(self) -> List[str]:
        """列出历史文件夹中所有快照文件。"""
        if not os.path.isdir(self.history_dir):
            return []
        return [f for f in os.listdir(self.history_dir) if f.startswith("report_") and f.endswith(".json")]

    def _snapshot_to_dict(self, snapshot: ReportSnapshot) -> dict:
        return {
            "keyword": snapshot.keyword,
            "collected_at": snapshot.collected_at,
            "items": [
                {
                    "title": i.title,
                    "content": i.content,
                    "source": i.source.value if hasattr(i.source, 'value') else str(i.source),
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
