from __future__ import annotations

import json
import os
import logging
from typing import List, Optional, Dict, Any

from config import DATA_DIR
from models import NewsItem, ReportSnapshot, ConflictDecision, now_ts

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StorageClient:
    """存储层：将快照写入对象存储（此处用本地文件模拟）。
    
    支持三种存储结构：
    1. history/ - 历史报告归档（按时间戳）
    2. latest_fetch.json - 最新采集的原始数据
    3. latest_report.json - 最新生成的分析报告（用于增量对比）
    """

    def __init__(self, base_dir: str = DATA_DIR) -> None:
        self.base_dir = base_dir
        self.history_dir = os.path.join(self.base_dir, "history")
        self.latest_fetch_path = os.path.join(self.base_dir, "latest_fetch.json")
        self.latest_report_path = os.path.join(self.base_dir, "latest_report.json")
        
        # 确保目录存在
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.history_dir, exist_ok=True)

    def save_snapshot(self, keyword: str, items: List[NewsItem]) -> str:
        """保存快照到 history/ 目录（归档用）"""
        try:
            snapshot = ReportSnapshot(keyword=keyword, collected_at=now_ts(), items=items)
            filename = f"report_{snapshot.collected_at}.json"
            path = os.path.join(self.history_dir, filename)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._snapshot_to_dict(snapshot), f, ensure_ascii=False, indent=2)
            logger.info(f"快照已保存到: {path}")
            return path
        except Exception as e:
            logger.error(f"保存快照失败: {e}")
            raise

    def save_latest_fetch(self, keyword: str, items: List[NewsItem]) -> None:
        """保存最新采集的原始数据到 latest_fetch.json
        
        这是增量对比的 new_items 输入源
        """
        try:
            snapshot = ReportSnapshot(keyword=keyword, collected_at=now_ts(), items=items)
            with open(self.latest_fetch_path, "w", encoding="utf-8") as f:
                json.dump(self._snapshot_to_dict(snapshot), f, ensure_ascii=False, indent=2)
            logger.info(f"最新采集数据已保存到: {self.latest_fetch_path}")
        except Exception as e:
            logger.error(f"保存最新采集数据失败: {e}")
            raise

    def save_latest_report(self, keyword: str, decisions: List[ConflictDecision], 
                          global_summary: str = "") -> None:
        """保存最新分析报告到 latest_report.json
        
        这将在下次增量对比时作为 old_snapshot 使用
        """
        try:
            report = {
                "keyword": keyword,
                "generated_at": now_ts(),
                "global_summary": global_summary,
                "decisions": [
                    {
                        "field": d.field,
                        "final_value": d.final_value,
                        "chosen_source": d.chosen_source.value if hasattr(d.chosen_source, 'value') else str(d.chosen_source),
                        "pending_sources": [s.value if hasattr(s, 'value') else str(s) for s in d.pending_sources],
                        "reason": d.reason
                    }
                    for d in decisions
                ]
            }
            with open(self.latest_report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            logger.info(f"最新分析报告已保存到: {self.latest_report_path}")
        except Exception as e:
            logger.error(f"保存最新报告失败: {e}")
            raise

    def load_latest_snapshot(self) -> Optional[ReportSnapshot]:
        """加载最新的历史快照（从 history/ 目录）"""
        try:
            files = self.list_snapshots()
            if not files:
                logger.warning("未找到历史快照")
                return None
            latest = sorted(files)[-1]
            path = os.path.join(self.history_dir, latest)
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"已加载历史快照: {path}")
            return self._dict_to_snapshot(data)
        except Exception as e:
            logger.error(f"加载历史快照失败: {e}")
            return None

    def load_latest_fetch(self) -> Optional[ReportSnapshot]:
        """加载最新采集的原始数据（latest_fetch.json）"""
        try:
            if not os.path.exists(self.latest_fetch_path):
                logger.warning(f"最新采集文件不存在: {self.latest_fetch_path}")
                return None
            with open(self.latest_fetch_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"已加载最新采集数据: {self.latest_fetch_path}")
            return self._dict_to_snapshot(data)
        except Exception as e:
            logger.error(f"加载最新采集数据失败: {e}")
            return None

    def load_current_report(self) -> Optional[Dict[str, Any]]:
        """加载当前报告（latest_report.json）
        
        返回上次分析的结论，用于增量对比的 old_snapshot
        """
        try:
            if not os.path.exists(self.latest_report_path):
                logger.warning(f"当前报告文件不存在: {self.latest_report_path}")
                return None
            with open(self.latest_report_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"已加载当前报告: {self.latest_report_path}")
            return data
        except Exception as e:
            logger.error(f"加载当前报告失败: {e}")
            return None

    def list_snapshots(self) -> List[str]:
        """列出 history/ 目录中的所有快照文件"""
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
        from models import SourceType
        items = []
        for i in data.get("items", []):
            source_str = i.get("source", "media")
            try:
                source = SourceType(source_str)
            except ValueError:
                source = SourceType.MEDIA  # 默认为媒体
            items.append(NewsItem(
                title=i.get("title", ""),
                content=i.get("content", ""),
                source=source,
                url=i.get("url"),
                published_at=i.get("published_at"),
            ))
        return ReportSnapshot(
            keyword=data.get("keyword", ""),
            collected_at=data.get("collected_at", ""),
            items=items,
        )

