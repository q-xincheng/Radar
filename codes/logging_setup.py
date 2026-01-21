from __future__ import annotations

import logging
import os
from typing import Any


def setup_logging(context: Any | None = None) -> None:
    """设置统一的日志配置
    
    从环境变量 LOG_LEVEL 读取日志级别（默认 INFO），
    配置格式包含时间、级别、logger name，
    若能从 context 获取 request_id 则带上。
    
    Args:
        context: FC 运行时上下文对象（可选），可从中提取 request_id
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # 尝试从 context 获取 request_id
    request_id = ""
    if context is not None:
        try:
            # 阿里云 FC context 对象通常有 request_id 属性
            if hasattr(context, "request_id"):
                request_id = f" [RequestID: {context.request_id}]"
        except Exception:
            # 忽略获取 request_id 失败的情况
            pass
    
    # 配置日志格式
    log_format = f"%(asctime)s - %(levelname)s - %(name)s{request_id} - %(message)s"
    
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True  # Python 3.8+ 支持 force 参数，强制重新配置
    )
