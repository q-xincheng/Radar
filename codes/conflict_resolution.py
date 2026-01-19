from __future__ import annotations

from typing import Dict, List

from models import ChangeItem, ConflictDecision, SOURCE_WEIGHTS, SourceType


def resolve_conflicts(changes: List[ChangeItem]) -> List[ConflictDecision]:
    """冲突仲裁：当同一字段有多来源冲突时，按权重选择最终结论。"""
    grouped: Dict[str, List[ChangeItem]] = {}
    for c in changes:
        grouped.setdefault(c.field, []).append(c)

    decisions: List[ConflictDecision] = []
    for field, items in grouped.items():
        items_sorted = sorted(
            items,
            key=lambda x: SOURCE_WEIGHTS.get(SourceType(x.source), 0.0) if isinstance(x.source, SourceType) else 0.0,
            reverse=True,
        )
        chosen = items_sorted[0]
        pending = [i.source for i in items_sorted[1:]]
        decisions.append(
            ConflictDecision(
                field=field,
                final_value=chosen.new,
                chosen_source=chosen.source if isinstance(chosen.source, SourceType) else SourceType.MEDIA,
                pending_sources=pending,  # 待核实来源
                reason="权重最高来源优先",
            )
        )
    return decisions
