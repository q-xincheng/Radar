from __future__ import annotations

from typing import List, Optional

from models import NewsItem, ReportSnapshot
from storage_layer import StorageClient

# 全局单例实例
_storage_client: Optional[StorageClient] = None


def _get_storage_client() -> StorageClient:
    """获取存储客户端单例"""
    global _storage_client
    if _storage_client is None:
        _storage_client = StorageClient()
    return _storage_client


def save_snapshot(keyword: str, items: List[NewsItem]) -> str:
    """保存快照并返回路径/key
    
    Args:
        keyword: 关键词
        items: 新闻条目列表
        
    Returns:
        快照存储路径或 OSS key
    """
    client = _get_storage_client()
    return client.save_snapshot(keyword, items)


def load_latest_snapshot() -> Optional[ReportSnapshot]:
    """加载最新快照
    
    Returns:
        最新快照对象，如果不存在则返回 None
    """
    client = _get_storage_client()
    return client.load_latest_snapshot()


def list_snapshots() -> List[str]:
    """列出所有快照文件名/key
    
    Returns:
        快照文件名列表
    """
    client = _get_storage_client()
    return client.list_snapshots()
