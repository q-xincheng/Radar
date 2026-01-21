"""
Mock test script for trigger_layer.handler()

用于本地快速验证 FC 触发器入口函数的行为：
- 测试不同 event 类型的解析（bytes, str, dict）
- 测试返回字段的完整性
- 测试 keyword 获取优先级
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

# Mock the orchestrator module before importing trigger_layer
sys.modules['orchestrator'] = MagicMock()
sys.modules['config'] = MagicMock()

# Import after mocking
from trigger_layer import handler


def mock_run_pipeline(keyword: str):
    """Mock implementation of run_pipeline"""
    return {
        "keyword": keyword,
        "run_id": "20260121_120000",
        "global_summary": f"这是{keyword}行业的全局总结分析报告。",
        "decisions": [
            {"field_name": "产能利用率", "final_value": "92%", "reason": "行业景气度上升"},
            {"field_name": "原材料成本", "final_value": "1850元/吨", "reason": "供应链紧张"},
        ],
        "raw_changes_count": 5
    }


def test_dict_event():
    """测试 event 为 dict 类型"""
    print("\n" + "="*60)
    print("测试 1: event 为 dict 类型")
    print("="*60)
    
    event = {"keyword": "半导体"}
    context = {}
    
    with patch('trigger_layer.run_pipeline', side_effect=mock_run_pipeline):
        result = handler(event, context)
    
    print(f"输入 event: {event}")
    print(f"返回结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # 验证返回字段
    assert result["status"] == "success", "status 应为 success"
    assert result["keyword"] == "半导体", "keyword 应为 '半导体'"
    assert result["run_id"] == "20260121_120000", "run_id 应为 '20260121_120000'"
    assert result["raw_changes_count"] == 5, "raw_changes_count 应为 5"
    assert result["conflicts_count"] == 2, "conflicts_count 应为 2 (len(decisions))"
    assert "这是半导体行业的全局总结分析报告" in result["global_summary"], "global_summary 应包含关键词"
    
    print("✅ 测试通过")


def test_bytes_event():
    """测试 event 为 bytes 类型"""
    print("\n" + "="*60)
    print("测试 2: event 为 bytes 类型")
    print("="*60)
    
    event_dict = {"keyword": "新能源汽车"}
    event = json.dumps(event_dict).encode("utf-8")
    context = {}
    
    with patch('trigger_layer.run_pipeline', side_effect=mock_run_pipeline):
        result = handler(event, context)
    
    print(f"输入 event (bytes): {event}")
    print(f"返回结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    assert result["status"] == "success", "status 应为 success"
    assert result["keyword"] == "新能源汽车", "keyword 应为 '新能源汽车'"
    assert result["conflicts_count"] == 2, "conflicts_count 应为 2"
    
    print("✅ 测试通过")


def test_str_event():
    """测试 event 为 str 类型"""
    print("\n" + "="*60)
    print("测试 3: event 为 str 类型")
    print("="*60)
    
    event = json.dumps({"keyword": "人工智能"})
    context = {}
    
    with patch('trigger_layer.run_pipeline', side_effect=mock_run_pipeline):
        result = handler(event, context)
    
    print(f"输入 event (str): {event}")
    print(f"返回结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    assert result["status"] == "success", "status 应为 success"
    assert result["keyword"] == "人工智能", "keyword 应为 '人工智能'"
    
    print("✅ 测试通过")


def test_empty_event():
    """测试 event 为空或无效时使用默认 keyword"""
    print("\n" + "="*60)
    print("测试 4: event 为空，使用默认 keyword")
    print("="*60)
    
    # Mock config.DEFAULT_KEYWORD
    with patch('trigger_layer.DEFAULT_KEYWORD', "半导体"):
        event = {}
        context = {}
        
        with patch('trigger_layer.run_pipeline', side_effect=mock_run_pipeline):
            result = handler(event, context)
    
    print(f"输入 event: {event}")
    print(f"返回结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    assert result["status"] == "success", "status 应为 success"
    assert result["keyword"] == "半导体", "keyword 应为默认值 '半导体'"
    
    print("✅ 测试通过")


def test_env_default_keyword():
    """测试环境变量 DEFAULT_KEYWORD 优先级"""
    print("\n" + "="*60)
    print("测试 5: 环境变量 DEFAULT_KEYWORD 优先级")
    print("="*60)
    
    # Set environment variable
    os.environ["DEFAULT_KEYWORD"] = "量子计算"
    
    # Mock config.DEFAULT_KEYWORD
    with patch('trigger_layer.DEFAULT_KEYWORD', "半导体"):
        event = {}
        context = {}
        
        with patch('trigger_layer.run_pipeline', side_effect=mock_run_pipeline):
            result = handler(event, context)
    
    print(f"环境变量 DEFAULT_KEYWORD: 量子计算")
    print(f"config.DEFAULT_KEYWORD: 半导体")
    print(f"输入 event: {event}")
    print(f"返回结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    assert result["status"] == "success", "status 应为 success"
    assert result["keyword"] == "量子计算", "keyword 应使用环境变量值 '量子计算'"
    
    # Clean up
    del os.environ["DEFAULT_KEYWORD"]
    
    print("✅ 测试通过")


def test_pipeline_error():
    """测试 pipeline 异常处理"""
    print("\n" + "="*60)
    print("测试 6: pipeline 执行异常")
    print("="*60)
    
    def mock_run_pipeline_error(keyword: str):
        raise Exception("模拟的 pipeline 执行错误")
    
    event = {"keyword": "半导体"}
    context = {}
    
    with patch('trigger_layer.run_pipeline', side_effect=mock_run_pipeline_error):
        result = handler(event, context)
    
    print(f"输入 event: {event}")
    print(f"返回结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    assert result["status"] == "error", "status 应为 error"
    assert result["keyword"] == "半导体", "keyword 应保留"
    assert "error" in result, "应包含 error 字段"
    assert "模拟的 pipeline 执行错误" in result["error"], "error 应包含异常信息"
    
    print("✅ 测试通过")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "#"*60)
    print("# 开始运行 trigger_layer 单元测试")
    print("#"*60)
    
    tests = [
        test_dict_event,
        test_bytes_event,
        test_str_event,
        test_empty_event,
        test_env_default_keyword,
        test_pipeline_error,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ 测试失败: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            failed += 1
    
    print("\n" + "#"*60)
    print(f"# 测试完成: {passed} 通过, {failed} 失败")
    print("#"*60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
