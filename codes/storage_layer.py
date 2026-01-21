from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import List, Optional

from config import DATA_DIR
from models import NewsItem, ReportSnapshot, SourceType, now_ts


class StorageBackend(ABC):
    """存储后端抽象基类"""
    
    @abstractmethod
    def save_snapshot(self, keyword: str, items: List[NewsItem]) -> str:
        """保存快照并返回路径/key"""
        pass
    
    @abstractmethod
    def load_latest_snapshot(self) -> Optional[ReportSnapshot]:
        """加载最新快照"""
        pass
    
    @abstractmethod
    def list_snapshots(self) -> List[str]:
        """列出所有快照文件名/key"""
        pass


class LocalStorageBackend(StorageBackend):
    """本地文件存储后端（用于本地调试）"""
    
    def __init__(self, base_dir: str = DATA_DIR) -> None:
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self.history_dir = os.path.join(self.base_dir, "history")
        os.makedirs(self.history_dir, exist_ok=True)
    
    def save_snapshot(self, keyword: str, items: List[NewsItem]) -> str:
        snapshot = ReportSnapshot(keyword=keyword, collected_at=now_ts(), items=items)
        filename = f"report_{snapshot.collected_at}.json"
        path = os.path.join(self.base_dir, filename)
        snapshot_dict = self._snapshot_to_dict(snapshot)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(snapshot_dict, f, ensure_ascii=False, indent=2)
        # also keep history copy for incremental diff inputs
        history_path = os.path.join(self.history_dir, filename)
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(snapshot_dict, f, ensure_ascii=False, indent=2)
        return path
    
    def load_latest_snapshot(self) -> Optional[ReportSnapshot]:
        files = self.list_snapshots()
        if not files:
            return None
        latest = sorted(files)[-1]
        path = os.path.join(self.base_dir, latest)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self._dict_to_snapshot(data)
    
    def list_snapshots(self) -> List[str]:
        if not os.path.isdir(self.base_dir):
            return []
        return [f for f in os.listdir(self.base_dir) if f.startswith("report_") and f.endswith(".json")]
    
    def _snapshot_to_dict(self, snapshot: ReportSnapshot) -> dict:
        return {
            "keyword": snapshot.keyword,
            "collected_at": snapshot.collected_at,
            "items": [
                {
                    "title": i.title,
                    "content": i.content,
                    "source": i.source.value,
                    "url": i.url,
                    "published_at": i.published_at,
                }
                for i in snapshot.items
            ],
        }
    
    def _dict_to_snapshot(self, data: dict) -> ReportSnapshot:
        items = []
        for i in data.get("items", []):
            source_str = i.get("source", "media")
            # Convert string to SourceType enum
            try:
                source = SourceType(source_str) if isinstance(source_str, str) else source_str
            except ValueError:
                source = SourceType.MEDIA  # Default to MEDIA if invalid
            
            items.append(NewsItem(
                title=i.get("title", ""),
                content=i.get("content", ""),
                source=source,
                url=i.get("url"),
                published_at=i.get("published_at"),
            ))
        
        return ReportSnapshot(
            keyword=data.get("keyword", ""),
            collected_at=data.get("collected_at", ""),
            items=items,
        )


class OSSStorageBackend(StorageBackend):
    """阿里云 OSS 存储后端（支持 RAM 角色认证）"""
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        bucket_name: Optional[str] = None,
        prefix: str = "radar/"
    ) -> None:
        """初始化 OSS 存储后端
        
        Args:
            endpoint: OSS endpoint，默认从环境变量 OSS_ENDPOINT 读取
            bucket_name: OSS bucket 名称，默认从环境变量 OSS_BUCKET 读取
            prefix: OSS 对象 key 前缀，默认从环境变量 OSS_PREFIX 读取（默认 "radar/"）
        """
        try:
            import oss2
            from oss2.credentials import EnvironmentVariableCredentialsProvider
        except ImportError:
            raise RuntimeError(
                "OSS 存储后端需要 oss2 库。请运行: pip install oss2\n"
                "或在 requirements.txt 中添加 oss2 并重新安装依赖。"
            )
        
        self.endpoint = endpoint or os.getenv("OSS_ENDPOINT")
        self.bucket_name = bucket_name or os.getenv("OSS_BUCKET")
        self.prefix = os.getenv("OSS_PREFIX", prefix)
        
        if not self.endpoint:
            raise ValueError(
                "OSS_ENDPOINT 环境变量未设置。\n"
                "请设置: export OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com"
            )
        
        if not self.bucket_name:
            raise ValueError(
                "OSS_BUCKET 环境变量未设置。\n"
                "请设置: export OSS_BUCKET=your-bucket-name"
            )
        
        # 使用 RAM 角色认证（优先）或 AK/SK（兜底）
        # FC 环境会自动提供 RAM 角色凭证
        try:
            # 尝试使用环境变量凭证提供者（支持 RAM 角色和 AK/SK）
            auth = oss2.ProviderAuth(EnvironmentVariableCredentialsProvider())
            self.bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)
            # 测试连接
            self.bucket.get_bucket_info()
        except Exception as e:
            # 如果 RAM 角色失败，尝试使用 AK/SK（兜底方案）
            access_key_id = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID")
            access_key_secret = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
            
            if access_key_id and access_key_secret:
                auth = oss2.Auth(access_key_id, access_key_secret)
                self.bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)
                try:
                    self.bucket.get_bucket_info()
                except Exception as e2:
                    raise RuntimeError(
                        f"OSS 连接失败（RAM 角色和 AK/SK 均失败）: {e2}\n"
                        "请检查：\n"
                        "1. OSS_ENDPOINT 和 OSS_BUCKET 是否正确\n"
                        "2. 在 FC 环境中是否配置了 RAM 角色权限\n"
                        "3. 在本地环境中是否设置了 ALIBABA_CLOUD_ACCESS_KEY_ID 和 ALIBABA_CLOUD_ACCESS_KEY_SECRET"
                    )
            else:
                raise RuntimeError(
                    f"OSS 认证失败: {e}\n"
                    "请设置以下环境变量之一：\n"
                    "1. 使用 RAM 角色（FC 环境推荐）- 无需额外配置\n"
                    "2. 使用 AK/SK（本地调试）:\n"
                    "   export ALIBABA_CLOUD_ACCESS_KEY_ID=your_key_id\n"
                    "   export ALIBABA_CLOUD_ACCESS_KEY_SECRET=your_key_secret"
                )
    
    def save_snapshot(self, keyword: str, items: List[NewsItem]) -> str:
        snapshot = ReportSnapshot(keyword=keyword, collected_at=now_ts(), items=items)
        filename = f"report_{snapshot.collected_at}.json"
        key = self.prefix + filename
        
        snapshot_dict = self._snapshot_to_dict(snapshot)
        content = json.dumps(snapshot_dict, ensure_ascii=False, indent=2)
        
        self.bucket.put_object(key, content.encode("utf-8"))
        return key
    
    def load_latest_snapshot(self) -> Optional[ReportSnapshot]:
        files = self.list_snapshots()
        if not files:
            return None
        
        # 获取最新的快照
        latest = sorted(files)[-1]
        key = self.prefix + latest
        
        obj = self.bucket.get_object(key)
        content = obj.read().decode("utf-8")
        data = json.loads(content)
        
        return self._dict_to_snapshot(data)
    
    def list_snapshots(self) -> List[str]:
        """列出所有 report_*.json 快照（不含前缀）"""
        import oss2  # Import oss2 locally to handle the case where it's not installed
        
        snapshots = []
        for obj in oss2.ObjectIterator(self.bucket, prefix=self.prefix):
            key = obj.key
            # 提取文件名（去掉前缀）
            if key.startswith(self.prefix):
                filename = key[len(self.prefix):]
                if filename.startswith("report_") and filename.endswith(".json"):
                    snapshots.append(filename)
        return snapshots
    
    def _snapshot_to_dict(self, snapshot: ReportSnapshot) -> dict:
        return {
            "keyword": snapshot.keyword,
            "collected_at": snapshot.collected_at,
            "items": [
                {
                    "title": i.title,
                    "content": i.content,
                    "source": i.source.value,
                    "url": i.url,
                    "published_at": i.published_at,
                }
                for i in snapshot.items
            ],
        }
    
    def _dict_to_snapshot(self, data: dict) -> ReportSnapshot:
        items = []
        for i in data.get("items", []):
            source_str = i.get("source", "media")
            # Convert string to SourceType enum
            try:
                source = SourceType(source_str) if isinstance(source_str, str) else source_str
            except ValueError:
                source = SourceType.MEDIA  # Default to MEDIA if invalid
            
            items.append(NewsItem(
                title=i.get("title", ""),
                content=i.get("content", ""),
                source=source,
                url=i.get("url"),
                published_at=i.get("published_at"),
            ))
        
        return ReportSnapshot(
            keyword=data.get("keyword", ""),
            collected_at=data.get("collected_at", ""),
            items=items,
        )


class StorageClient:
    """存储客户端：根据配置选择存储后端"""
    
    def __init__(self, backend: Optional[StorageBackend] = None) -> None:
        """初始化存储客户端
        
        Args:
            backend: 可选，指定存储后端。如果为 None，则根据环境变量 STORAGE_BACKEND 自动选择
        """
        if backend is None:
            backend_type = os.getenv("STORAGE_BACKEND", "local").lower()
            
            if backend_type == "oss":
                backend = OSSStorageBackend()
            elif backend_type == "local":
                backend = LocalStorageBackend()
            else:
                raise ValueError(
                    f"不支持的存储后端: {backend_type}\n"
                    f"请设置 STORAGE_BACKEND 为 'local' 或 'oss'"
                )
        
        self.backend = backend
    
    def save_snapshot(self, keyword: str, items: List[NewsItem]) -> str:
        """保存快照并返回路径/key"""
        return self.backend.save_snapshot(keyword, items)
    
    def load_latest_snapshot(self) -> Optional[ReportSnapshot]:
        """加载最新快照"""
        return self.backend.load_latest_snapshot()
    
    def list_snapshots(self) -> List[str]:
        """列出所有快照文件名/key"""
        return self.backend.list_snapshots()

