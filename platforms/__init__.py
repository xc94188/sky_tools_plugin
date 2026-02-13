"""
平台处理器包初始化
导入所有已注册的平台处理器，使其在注册表中生效
"""
from . import mango
from . import ovoav
from . import yingtian
from .registry import registry, register_platform
from .base import BasePlatformHandler

__all__ = [
    "mango",
    "ovoav",
    "yingtian",
    "registry",
    "register_platform",
    "BasePlatformHandler",
]