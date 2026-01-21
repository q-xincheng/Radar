#!/usr/bin/env python3
"""
示例：演示冲突仲裁的权重系统

本脚本展示当同一指标出现多个不同来源的数据时，
系统如何根据权重（官方1.0 > 媒体0.7 > 传闻0.3）自动选择最可信的结论。
"""

import sys
sys.path.insert(0, '/home/runner/work/Radar/Radar/codes')

from models import ChangeItem, SourceType, SOURCE_WEIGHTS
from conflict_resolution import resolve_conflicts


def main():
    print("=" * 60)
    print("冲突仲裁权重系统演示")
    print("=" * 60)
    
    # 模拟场景：同一个指标"芯片良率"有三个不同来源的数据
    changes = [
        ChangeItem(
            field="芯片良率",
            old="85%",
            new="88%",
            status="increased",
            source=SourceType.RUMOR,
            insight="市场传言某厂商良率小幅提升至88%"
        ),
        ChangeItem(
            field="芯片良率",
            old="85%",
            new="92%",
            status="increased",
            source=SourceType.MEDIA,
            insight="行业媒体报道良率突破90%，达到92%"
        ),
        ChangeItem(
            field="芯片良率",
            old="85%",
            new="95%",
            status="increased",
            source=SourceType.OFFICIAL,
            insight="官方财报披露良率已达95%，创历史新高"
        ),
    ]
    
    print("\n【冲突数据】")
    print("同一指标「芯片良率」有三个不同来源的数据：")
    for c in changes:
        weight = SOURCE_WEIGHTS[c.source]
        print(f"  • 来源: {c.source.value:8s} (权重: {weight}) -> 新值: {c.new}")
        print(f"    分析: {c.insight}")
    
    print("\n【权重规则】")
    print("  官方公告 (official): 1.0 - 最可信")
    print("  权威媒体 (media):    0.7 - 较可信")
    print("  市场传闻 (rumor):    0.3 - 待核实")
    
    # 执行冲突仲裁
    decisions = resolve_conflicts(changes)
    
    print("\n【仲裁结果】")
    for d in decisions:
        print(f"  指标: {d.field}")
        print(f"  最终采纳值: {d.final_value}")
        print(f"  选中来源: {d.chosen_source.value} (权重: {SOURCE_WEIGHTS[d.chosen_source]})")
        print(f"  待核实来源: {', '.join([s.value for s in d.pending_sources])}")
        print(f"  AI分析: {d.reason}")
    
    print("\n" + "=" * 60)
    print("✓ 系统自动选择了权重最高的官方来源作为最终结论")
    print("✓ 其他低权重来源被标记为「待核实」供后续人工审核")
    print("=" * 60)


if __name__ == "__main__":
    main()
