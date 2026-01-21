from __future__ import annotations
from typing import Dict, List
from models import ChangeItem, ConflictDecision, SOURCE_WEIGHTS, SourceType

# 固定来源标签映射（Decision 模块）
SOURCE_TAGS = [
    (SourceType.OFFICIAL, "官方公告/监管文件"),
    (SourceType.MEDIA, "权威媒体/研究机构"),
    (SourceType.RUMOR, "传闻/社交媒体"),
]
_SOURCE_TAG_MAP = dict(SOURCE_TAGS)

def resolve_conflicts(changes: List[ChangeItem]) -> List[ConflictDecision]:
    """冲突仲裁逻辑：按权重选择结论，并将 AI 洞察包装为通俗建议"""
    if not changes:
        return []

    # 1. 按指标字段进行分组
    grouped: Dict[str, List[ChangeItem]] = {}
    for c in changes:
        grouped.setdefault(c.field_name, []).append(c)

    decisions: List[ConflictDecision] = []
    
    # 2. 针对每个指标进行仲裁
    for field_name, items in grouped.items():
        # 按预设的来源权重排序（官方 > 媒体 > 传闻）
        items_sorted = sorted(
            items,
            key=lambda x: SOURCE_WEIGHTS.get(SourceType(x.source), 0.0),
            reverse=True,
        )
        
        # 选择权重最高的条目作为最终结论
        chosen = items_sorted[0]
        
        # 记录被舍弃的低权重来源，供成员 C 进行“待核实”展示
        pending = [i.source for i in items_sorted[1:]]
        
        decisions.append(
            ConflictDecision(
                field_name=field_name,
                final_value=chosen.new,
                chosen_source=chosen.source,
                pending_sources=pending,
                # 核心改进：理由不再是代码逻辑，而是 AI 生成的行业洞察
                reason=f"[{_SOURCE_TAG_MAP.get(chosen.source, chosen.source)}] {chosen.insight}"
            )
        )
        
    return decisions
