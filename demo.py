#!/usr/bin/env python3
"""
示例脚本：演示完整的行研雷达工作流程

运行前请设置环境变量：
export SILICONFLOW_API_KEY="your-api-key"
"""

import os
import sys
import json
from pathlib import Path

# 添加 codes 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent / "codes"))

def main():
    # 检查环境变量
    api_key = os.getenv("SILICONFLOW_API_KEY")
    if not api_key:
        print("❌ 错误: 未设置 SILICONFLOW_API_KEY 环境变量")
        print("请运行: export SILICONFLOW_API_KEY='your-api-key'")
        return 1
    
    print("=" * 60)
    print("行研雷达 - 完整工作流程演示")
    print("=" * 60)
    
    # 方式一：直接调用主流程
    print("\n【方式一】直接调用 run_pipeline")
    print("-" * 60)
    
    from orchestrator import run_pipeline
    
    result = run_pipeline(keyword="半导体")
    print(f"✓ 状态: {result.get('status')}")
    print(f"✓ 关键词: {result.get('keyword')}")
    print(f"✓ 变化数: {result.get('raw_changes_count')}")
    print(f"✓ 决策数: {len(result.get('decisions', []))}")
    print(f"✓ 全局总结: {result.get('global_summary')}")
    
    # 方式二：模拟 FC handler 调用
    print("\n【方式二】模拟阿里云 FC Handler 调用")
    print("-" * 60)
    
    from trigger_layer import simulate_cron_trigger
    
    fc_result = simulate_cron_trigger(keyword="人工智能")
    print(f"✓ HTTP 状态码: {fc_result.get('statusCode')}")
    
    body = json.loads(fc_result.get('body', '{}'))
    print(f"✓ 执行状态: {body.get('status')}")
    print(f"✓ 消息: {body.get('message')}")
    
    # 查看生成的文件
    print("\n【查看生成的文件】")
    print("-" * 60)
    
    data_dir = Path("data")
    history_dir = Path("history")
    
    # 检查 latest_fetch.json
    latest_fetch = data_dir / "latest_fetch.json"
    if latest_fetch.exists():
        print(f"✓ {latest_fetch} (最新抓取数据)")
        with open(latest_fetch, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"  - 关键词: {data.get('keyword')}")
            print(f"  - 采集时间: {data.get('collected_at')}")
            print(f"  - 条目数: {len(data.get('items', []))}")
    else:
        print(f"⚠ {latest_fetch} 不存在")
    
    # 检查 latest_report.json
    latest_report = data_dir / "latest_report.json"
    if latest_report.exists():
        print(f"✓ {latest_report} (最新分析报告)")
        with open(latest_report, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"  - 关键词: {data.get('keyword')}")
            print(f"  - 生成时间: {data.get('generated_at')}")
            print(f"  - 决策数: {len(data.get('decisions', []))}")
    else:
        print(f"⚠ {latest_report} 不存在")
    
    # 检查 history/current_report.json
    current_report = history_dir / "current_report.json"
    if current_report.exists():
        print(f"✓ {current_report} (当前报告)")
    else:
        print(f"⚠ {current_report} 不存在")
    
    # 列出所有历史快照
    report_files = list(data_dir.glob("report_*.json"))
    if report_files:
        print(f"✓ 历史快照文件: {len(report_files)} 个")
        for f in sorted(report_files)[-3:]:  # 显示最近3个
            print(f"  - {f.name}")
    
    # 列出所有历史归档
    history_files = list(history_dir.glob("current_report_*.json"))
    if history_files:
        print(f"✓ 历史归档文件: {len(history_files)} 个")
        for f in sorted(history_files)[-3:]:
            print(f"  - {f.name}")
    
    print("\n" + "=" * 60)
    print("✓ 演示完成！")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
