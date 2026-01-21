from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class SourceType(str, Enum):
    """数据来源类型枚举"""
    OFFICIAL = "official"  # 官方公告
    MEDIA = "media"       # 权威媒体
    RUMOR = "rumor"       # 市场传闻


# 来源权重配置（硬编码）：官方 1.0 > 媒体 0.7 > 传闻 0.3
SOURCE_WEIGHTS = {
    SourceType.OFFICIAL: 1.0,
    SourceType.MEDIA: 0.7,
    SourceType.RUMOR: 0.3,
}


@dataclass
class NewsItem:
    """新闻条目"""
    title: str
    content: str
    source: SourceType
    url: Optional[str] = None
    published_at: Optional[str] = None


@dataclass
class ReportSnapshot:
    """报告快照"""
    keyword: str
    collected_at: str
    items: List[NewsItem] = field(default_factory=list)


@dataclass
class ChangeItem:
    """变更条目"""
    field: str
    old: str
    new: str
    status: str
    source: SourceType
    insight: str = ""  # AI 对变动的通俗化解读
    confidence: float = 0.0


@dataclass
class ConflictDecision:
    """冲突仲裁决策"""
    field: str
    final_value: str
    chosen_source: SourceType
    pending_sources: List[SourceType] = field(default_factory=list)  # 待核实来源
    reason: str = ""  # 最终采纳的 insight


def now_ts() -> str:
    """生成当前时间戳"""
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")
