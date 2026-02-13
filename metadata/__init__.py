"""
命令元数据包
导出元数据注册表和所有命令的元数据定义
"""
from .registry import CommandMetadataRegistry, registry
from .command_metadata import ALL_COMMAND_METADATA

__all__ = [
    "CommandMetadataRegistry",
    "registry",
    "ALL_COMMAND_METADATA",
]