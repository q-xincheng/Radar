from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class SourceType(str, Enum):
    OFFICIAL = "official"
    MEDIA = "media"
    RUMOR = "rumor"


SOURCE_WEIGHTS = {
    SourceType.OFFICIAL: 1.0,
    SourceType.MEDIA: 0.7,
    SourceType.RUMOR: 0.3,
}


@dataclass
class NewsItem:
    title: str
    content: str
    source: SourceType
    url: Optional[str] = None
    published_at: Optional[str] = None


@dataclass
class ReportSnapshot:
    keyword: str
    collected_at: str
    items: List[NewsItem] = field(default_factory=list)


@dataclass
class ChangeItem:
    """表示单个指标的变化项"""
    field_name: str  # 使用 field_name 避免与 dataclass.field 命名冲突
    old: str
    new: str
    status: str
    source: SourceType
    insight: str = ""  # 存储 AI 对变动的通俗化解读
    confidence: float = 0.0


@dataclass
class ConflictDecision:
    """表示冲突仲裁的决策结果"""
    field_name: str  # 使用 field_name 避免与 dataclass.field 命名冲突
    final_value: str
    chosen_source: SourceType
    pending_sources: List[SourceType] = field(default_factory=list)
    reason: str = ""  # 存储最终采纳的 insight


def now_ts() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")