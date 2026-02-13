"""
平台注册表
管理所有身高查询平台的处理器类和别名
"""
from typing import Dict, List, Optional, Type

from .base import BasePlatformHandler


class PlatformRegistry:
    """平台注册表（单例）"""

    _instance = None
    _handlers: Dict[str, Type[BasePlatformHandler]] = {}
    _aliases: Dict[str, str] = {}  # 别名 -> 主名

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(
        self,
        name: str,
        handler_class: Type[BasePlatformHandler],
        aliases: Optional[List[str]] = None,
    ):
        """
        注册平台处理器
        Args:
            name: 平台主名称（唯一标识）
            handler_class: 处理器类
            aliases: 别名列表（如 ["mg", "芒果"]）
        """
        if name in self._handlers:
            raise ValueError(f"平台 {name} 已注册")
        self._handlers[name] = handler_class
        self._aliases[name] = name  # 主名自身
        if aliases:
            for alias in aliases:
                self._aliases[alias] = name
        return handler_class  # 方便用作装饰器

    def get_handler(self, name_or_alias: str) -> Optional[Type[BasePlatformHandler]]:
        """根据名称或别名获取处理器类"""
        main_name = self._aliases.get(name_or_alias)
        if main_name:
            return self._handlers.get(main_name)
        return None

    def get_all_platforms(self) -> List[str]:
        """获取所有已注册的平台主名称"""
        return list(self._handlers.keys())

    def get_platform_info(self) -> Dict[str, List[str]]:
        """获取所有平台及其别名（用于帮助信息）"""
        info = {}
        for main_name in self._handlers:
            aliases = [
                alias for alias, main in self._aliases.items() if main == main_name and alias != main_name
            ]
            info[main_name] = aliases
        return info


# 全局单例
registry = PlatformRegistry()


# 便捷装饰器
def register_platform(name: str, aliases: Optional[List[str]] = None):
    def decorator(cls):
        registry.register(name, cls, aliases)
        return cls
    return decorator