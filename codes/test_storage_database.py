#!/usr/bin/env python3
"""Integration test for storage and database layers"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add codes directory to path
sys.path.insert(0, os.path.dirname(__file__))

from storage_layer import StorageClient, LocalStorageBackend, OSSStorageBackend
from database_layer import DatabaseClient
from models import NewsItem, SourceType, ConflictDecision


def test_local_storage_backend():
    """Test local storage backend functionality"""
    print("=" * 60)
    print("Testing Local Storage Backend")
    print("=" * 60)
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = LocalStorageBackend(base_dir=tmpdir)
        
        # Test save_snapshot
        test_items = [
            NewsItem(
                title="Test News 1",
                content="Test content 1",
                source=SourceType.OFFICIAL,
                url="https://example.com/1",
                published_at="2026-01-21"
            ),
            NewsItem(
                title="Test News 2",
                content="Test content 2",
                source=SourceType.MEDIA,
                url="https://example.com/2",
                published_at="2026-01-21"
            )
        ]
        
        print("\n1. Testing save_snapshot...")
        path = backend.save_snapshot(keyword="test_keyword", items=test_items)
        print(f"   ✓ Snapshot saved to: {path}")
        
        # Test list_snapshots
        print("\n2. Testing list_snapshots...")
        snapshots = backend.list_snapshots()
        print(f"   ✓ Found {len(snapshots)} snapshot(s): {snapshots}")
        assert len(snapshots) == 1, "Should have exactly one snapshot"
        
        # Test load_latest_snapshot
        print("\n3. Testing load_latest_snapshot...")
        loaded = backend.load_latest_snapshot()
        assert loaded is not None, "Should load snapshot"
        assert loaded.keyword == "test_keyword", "Keyword should match"
        assert len(loaded.items) == 2, "Should have 2 items"
        print(f"   ✓ Loaded snapshot: keyword={loaded.keyword}, items={len(loaded.items)}")
        
    print("\n✅ Local storage backend tests PASSED\n")


def test_storage_client_local():
    """Test StorageClient with local backend"""
    print("=" * 60)
    print("Testing StorageClient (local mode)")
    print("=" * 60)
    
    # Set environment variable for local backend
    os.environ["STORAGE_BACKEND"] = "local"
    
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["DATA_DIR"] = tmpdir
        
        client = StorageClient()
        
        test_items = [
            NewsItem(
                title="Client Test",
                content="Client test content",
                source=SourceType.OFFICIAL
            )
        ]
        
        print("\n1. Testing StorageClient.save_snapshot...")
        path = client.save_snapshot(keyword="client_test", items=test_items)
        print(f"   ✓ Snapshot saved via client: {path}")
        
        print("\n2. Testing StorageClient.list_snapshots...")
        snapshots = client.list_snapshots()
        print(f"   ✓ Found {len(snapshots)} snapshot(s)")
        
        print("\n3. Testing StorageClient.load_latest_snapshot...")
        loaded = client.load_latest_snapshot()
        assert loaded is not None, "Should load snapshot"
        print(f"   ✓ Loaded via client: keyword={loaded.keyword}")
        
    print("\n✅ StorageClient local mode tests PASSED\n")


def test_database_client():
    """Test DatabaseClient functionality"""
    print("=" * 60)
    print("Testing Database Client")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_radar.db")
        db = DatabaseClient(db_path=db_path)
        
        # Test save_decisions
        test_decisions = [
            ConflictDecision(
                field_name="产能利用率",
                final_value="92%",
                chosen_source=SourceType.OFFICIAL,
                pending_sources=[SourceType.MEDIA],
                reason="官方数据更可信"
            ),
            ConflictDecision(
                field_name="全固态电池进度",
                final_value="样件装车路测",
                chosen_source=SourceType.MEDIA,
                pending_sources=[],
                reason="媒体报道进度"
            )
        ]
        
        print("\n1. Testing save_decisions...")
        db.save_decisions(
            run_id="test_run_001",
            keyword="半导体",
            decisions=test_decisions
        )
        print(f"   ✓ Saved {len(test_decisions)} decisions")
        
        # Test get_latest_states
        print("\n2. Testing get_latest_states...")
        states = db.get_latest_states(keyword="半导体")
        print(f"   ✓ Retrieved {len(states)} indicator states")
        assert len(states) == 2, "Should have 2 indicator states"
        
        for state in states:
            print(f"      - {state['field_name']}: {state['final_value']}")
        
        # Test get_decision_history
        print("\n3. Testing get_decision_history...")
        history = db.get_decision_history(keyword="半导体")
        print(f"   ✓ Retrieved {len(history)} decision records")
        assert len(history) == 2, "Should have 2 decision records"
        
        # Test upsert (save again with updated values)
        print("\n4. Testing upsert (update existing indicator)...")
        updated_decisions = [
            ConflictDecision(
                field_name="产能利用率",
                final_value="95%",
                chosen_source=SourceType.OFFICIAL,
                pending_sources=[],
                reason="最新官方数据"
            )
        ]
        db.save_decisions(
            run_id="test_run_002",
            keyword="半导体",
            decisions=updated_decisions
        )
        
        states = db.get_latest_states(keyword="半导体")
        capacity_states = [s for s in states if s['field_name'] == "产能利用率"]
        assert len(capacity_states) > 0, "Should find capacity state"
        capacity_state = capacity_states[0]
        assert capacity_state['final_value'] == "95%", "Should update to new value"
        print(f"   ✓ Indicator updated: 产能利用率 = {capacity_state['final_value']}")
        
        # Verify history now has 3 records (2 from first run + 1 from second run)
        history = db.get_decision_history(keyword="半导体")
        print(f"   ✓ History now has {len(history)} records (after update)")
        assert len(history) == 3, "Should have 3 total decision records"
        
    print("\n✅ Database client tests PASSED\n")


def test_oss_storage_configuration():
    """Test OSS storage configuration and error handling"""
    print("=" * 60)
    print("Testing OSS Storage Configuration")
    print("=" * 60)
    
    # Test missing configuration error handling
    print("\n1. Testing missing OSS_ENDPOINT error...")
    os.environ.pop("OSS_ENDPOINT", None)
    os.environ.pop("OSS_BUCKET", None)
    
    try:
        backend = OSSStorageBackend()
        print("   ✗ Should have raised ValueError for missing OSS_ENDPOINT")
        assert False, "Should raise error"
    except ValueError as e:
        print(f"   ✓ Correctly raised ValueError: {str(e)[:80]}...")
    
    # Test missing bucket error handling
    print("\n2. Testing missing OSS_BUCKET error...")
    os.environ["OSS_ENDPOINT"] = "oss-cn-hangzhou.aliyuncs.com"
    os.environ.pop("OSS_BUCKET", None)
    
    try:
        backend = OSSStorageBackend()
        print("   ✗ Should have raised ValueError for missing OSS_BUCKET")
        assert False, "Should raise error"
    except ValueError as e:
        print(f"   ✓ Correctly raised ValueError: {str(e)[:80]}...")
    
    print("\n✅ OSS configuration tests PASSED\n")


def test_storage_backend_selection():
    """Test StorageClient backend selection"""
    print("=" * 60)
    print("Testing Storage Backend Selection")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["DATA_DIR"] = tmpdir
        
        # Test local backend selection
        print("\n1. Testing STORAGE_BACKEND=local...")
        os.environ["STORAGE_BACKEND"] = "local"
        client = StorageClient()
        assert isinstance(client.backend, LocalStorageBackend), "Should use LocalStorageBackend"
        print("   ✓ Correctly selected LocalStorageBackend")
        
        # Test invalid backend error
        print("\n2. Testing invalid STORAGE_BACKEND...")
        os.environ["STORAGE_BACKEND"] = "invalid"
        try:
            client = StorageClient()
            print("   ✗ Should have raised ValueError for invalid backend")
            assert False, "Should raise error"
        except ValueError as e:
            print(f"   ✓ Correctly raised ValueError: {str(e)[:80]}...")
        
    print("\n✅ Backend selection tests PASSED\n")


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("RADAR STORAGE & DATABASE INTEGRATION TESTS")
    print("=" * 60 + "\n")
    
    try:
        # Run all tests
        test_local_storage_backend()
        test_storage_client_local()
        test_database_client()
        test_oss_storage_configuration()
        test_storage_backend_selection()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60 + "\n")
        return 0
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60 + "\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
