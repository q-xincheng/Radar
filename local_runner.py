#!/usr/bin/env python3
"""本地运行脚本 - 行研雷达

用于在本地环境测试完整的巡检流程，无需部署到阿里云 FC。

使用方法:
    python local_runner.py [关键词]

示例:
    python local_runner.py 半导体
    python local_runner.py 新能源
"""

import sys
import json
from pathlib import Path

# 添加 codes 目录到 Python 路径
codes_dir = Path(__file__).parent / "codes"
sys.path.insert(0, str(codes_dir))

from trigger_layer import local_invoke


def main():
    """主函数：运行本地测试"""
    keyword = sys.argv[1] if len(sys.argv) > 1 else None
    
    print("=" * 80)
    print("行研雷达 - 本地运行模式")
    print("=" * 80)
    
    if keyword:
        print(f"\n使用关键词: {keyword}\n")
    else:
        print(f"\n使用默认关键词（从环境变量或配置文件读取）\n")
    
    try:
        result = local_invoke(keyword=keyword)
        
        print("\n" + "=" * 80)
        print("运行结果")
        print("=" * 80)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        if result.get("status") == "success":
            print("\n✅ 运行成功！")
            print(f"\n📊 全局总结:")
            print(result.get("global_summary", "无"))
            print(f"\n📈 发现 {result.get('raw_changes_count', 0)} 项变化")
            print(f"⚖️  解决 {result.get('conflicts_count', 0)} 项冲突")
        elif result.get("status") == "error":
            print("\n❌ 运行失败！")
            print(f"错误信息: {result.get('error', '未知错误')}")
            sys.exit(1)
        else:
            print(f"\n⚠️  运行状态: {result.get('status', 'unknown')}")
            print(f"消息: {result.get('message', '无')}")
            
    except Exception as e:
        print(f"\n❌ 运行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
