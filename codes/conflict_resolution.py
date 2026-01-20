from __future__ import annotations
import logging
from typing import Dict, List
from models import ChangeItem, ConflictDecision, SOURCE_WEIGHTS, SourceType

logger = logging.getLogger(__name__)


def resolve_conflicts(changes: List[ChangeItem]) -> List[ConflictDecision]:
    """冲突仲裁逻辑：按权重选择结论，并将 AI 洞察包装为通俗建议
    
    权重定义：
    - 官方公告 (official) = 1.0
    - 权威媒体 (media) = 0.7
    - 市场传闻 (rumor) = 0.3
    
    当存在相同权重的冲突来源时，标记为"待核实"(to_be_verified)
    """
    if not changes:
        return []

    # 1. 按指标字段进行分组
    grouped: Dict[str, List[ChangeItem]] = {}
    for c in changes:
        grouped.setdefault(c.field, []).append(c)

    decisions: List[ConflictDecision] = []
    
    # 2. 针对每个指标进行仲裁
    for field, items in grouped.items():
        # 按预设的来源权重排序（官方 > 媒体 > 传闻）
        items_sorted = sorted(
            items,
            key=lambda x: SOURCE_WEIGHTS.get(SourceType(x.source), 0.0),
            reverse=True,
        )
        
        # 选择权重最高的条目作为最终结论
        chosen = items_sorted[0]
        chosen_weight = SOURCE_WEIGHTS.get(chosen.source, 0.0)
        
        # 记录被舍弃的低权重来源，供成员 C 进行"待核实"展示
        pending = [i.source for i in items_sorted[1:]]
        
        # 检查是否有相同权重的来源（需要标记为"待核实"）
        has_equal_weight = any(
            SOURCE_WEIGHTS.get(item.source, 0.0) == chosen_weight 
            for item in items_sorted[1:]
        )
        
        reason = chosen.insight if hasattr(chosen, 'insight') and chosen.insight else "指标发生变动"
        if has_equal_weight:
            reason = f"[待核实] {reason}"
        
        decision = ConflictDecision(
            field=field,
            final_value=chosen.new,
            chosen_source=chosen.source,
            pending_sources=pending,
            # 核心改进：理由不再是代码逻辑，而是 AI 生成的行业洞察
            reason=reason
        )
        
        # 添加额外的状态标记
        if has_equal_weight:
            decision.status = "to_be_verified"
        else:
            decision.status = "confirmed"
            
        decisions.append(decision)
        
        logger.info(f"Resolved conflict for '{field}': chose {chosen.source.value} "
                   f"(weight={chosen_weight}), status={decision.status}")
        
    return decisions
