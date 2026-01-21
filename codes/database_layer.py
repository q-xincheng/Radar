"""数据库层：使用 SQLite 持久化指标状态和冲突决策历史"""
from __future__ import annotations

import os
import sqlite3
from typing import List, Optional

from config import DATA_DIR
from models import ConflictDecision, SourceType, now_ts


class DatabaseClient:
    """SQLite 数据库客户端，用于持久化指标状态和决策历史"""

    def __init__(self, db_path: Optional[str] = None) -> None:
        """初始化数据库客户端
        
        Args:
            db_path: 数据库文件路径，默认使用 ${DATA_DIR}/radar.db
        """
        if db_path is None:
            db_path = os.getenv("DB_PATH", os.path.join(DATA_DIR, "radar.db"))
        
        self.db_path = db_path
        
        # 确保数据目录存在
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        
        # 初始化数据库表
        self._init_tables()

    def _init_tables(self) -> None:
        """初始化数据库表结构（如果不存在）"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 创建指标状态表（按 keyword + field_name 唯一）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS indicator_states (
                    keyword TEXT NOT NULL,
                    field_name TEXT NOT NULL,
                    final_value TEXT NOT NULL,
                    chosen_source TEXT NOT NULL,
                    reason TEXT,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (keyword, field_name)
                )
            """)
            
            # 创建冲突决策历史表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conflict_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    keyword TEXT NOT NULL,
                    field_name TEXT NOT NULL,
                    final_value TEXT NOT NULL,
                    chosen_source TEXT NOT NULL,
                    pending_sources TEXT,
                    reason TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            
            # 为常用查询创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conflict_decisions_run_id 
                ON conflict_decisions(run_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conflict_decisions_keyword 
                ON conflict_decisions(keyword)
            """)
            
            conn.commit()

    def save_decisions(
        self, 
        run_id: str, 
        keyword: str, 
        decisions: List[ConflictDecision]
    ) -> None:
        """保存决策到数据库
        
        Args:
            run_id: 本次运行的唯一标识
            keyword: 关键词
            decisions: 决策列表
        """
        if not decisions:
            return
        
        now = now_ts()  # Use consistent timestamp format from models.py
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for decision in decisions:
                # 1. 插入到决策历史表
                pending_sources_str = ",".join([s.value for s in decision.pending_sources])
                cursor.execute("""
                    INSERT INTO conflict_decisions 
                    (run_id, keyword, field_name, final_value, chosen_source, 
                     pending_sources, reason, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run_id,
                    keyword,
                    decision.field_name,
                    decision.final_value,
                    decision.chosen_source.value,
                    pending_sources_str,
                    decision.reason,
                    now
                ))
                
                # 2. Upsert 到指标状态表（保留最新状态）
                cursor.execute("""
                    INSERT INTO indicator_states 
                    (keyword, field_name, final_value, chosen_source, reason, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(keyword, field_name) DO UPDATE SET
                        final_value = excluded.final_value,
                        chosen_source = excluded.chosen_source,
                        reason = excluded.reason,
                        updated_at = excluded.updated_at
                """, (
                    keyword,
                    decision.field_name,
                    decision.final_value,
                    decision.chosen_source.value,
                    decision.reason,
                    now
                ))
            
            conn.commit()

    def get_latest_states(self, keyword: str) -> List[dict]:
        """获取指定关键词的最新指标状态
        
        Args:
            keyword: 关键词
            
        Returns:
            指标状态列表
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT keyword, field_name, final_value, chosen_source, reason, updated_at
                FROM indicator_states
                WHERE keyword = ?
                ORDER BY updated_at DESC
            """, (keyword,))
            
            return [dict(row) for row in cursor.fetchall()]

    def get_decision_history(
        self, 
        keyword: Optional[str] = None, 
        run_id: Optional[str] = None,
        limit: int = 100
    ) -> List[dict]:
        """获取决策历史
        
        Args:
            keyword: 可选，按关键词过滤
            run_id: 可选，按运行 ID 过滤
            limit: 返回结果数量限制
            
        Returns:
            决策历史列表
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = """
                SELECT id, run_id, keyword, field_name, final_value, 
                       chosen_source, pending_sources, reason, created_at
                FROM conflict_decisions
                WHERE 1=1
            """
            params = []
            
            if keyword:
                query += " AND keyword = ?"
                params.append(keyword)
            
            if run_id:
                query += " AND run_id = ?"
                params.append(run_id)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            
            return [dict(row) for row in cursor.fetchall()]
