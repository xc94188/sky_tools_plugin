"""
命令元数据注册表（单例）
提供命令元数据的注册、查询和启用状态过滤
"""
from typing import Dict, List, Optional, Callable


class CommandMetadataRegistry:
    """命令元数据注册表（单例）"""

    _instance = None
    _metadata: Dict[str, dict] = {}
    _alias_map: Dict[str, str] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # 避免重复初始化
        pass

    def register(self, metadata: dict) -> None:
        """
        注册单个命令的元数据
        Args:
            metadata: 命令元数据字典，必须包含 name 字段
        Raises:
            ValueError: 命令名或别名冲突
        """
        name = metadata["name"]

        # 检查命令名冲突
        if name in self._metadata:
            raise ValueError(f"命令名称冲突: {name}")

        # 注册命令
        self._metadata[name] = metadata

        # 注册别名
        for alias in metadata.get("aliases", []):
            if alias in self._alias_map:
                other = self._alias_map[alias]
                raise ValueError(f"别名冲突: '{alias}' 同时用于 '{name}' 和 '{other}'")
            self._alias_map[alias] = name

    def register_many(self, metadata_list: List[dict]) -> None:
        """批量注册多个命令的元数据"""
        for meta in metadata_list:
            self.register(meta)

    def get_by_name(self, name: str) -> Optional[dict]:
        """通过命令名获取元数据"""
        return self._metadata.get(name)

    def get_by_alias(self, alias: str) -> Optional[dict]:
        """通过别名获取元数据"""
        name = self._alias_map.get(alias)
        if name:
            return self._metadata.get(name)
        return None

    def get_all(self) -> Dict[str, dict]:
        """获取所有元数据（不进行启用过滤）"""
        return self._metadata.copy()

    def get_all_enabled(self, config_getter: Callable) -> Dict[str, dict]:
        """
        获取所有启用的命令元数据
        Args:
            config_getter: 配置获取函数，如 self.get_config
        Returns:
            过滤后的元数据字典
        """
        enabled = {}
        for name, meta in self._metadata.items():
            config_key = meta.get("config_key")
            # 调试日志：打印每个命令的 config_key 和获取到的值
            if config_key:
                config_value = config_getter(config_key, True)
                # 这里无法直接打印日志，可以在外部调用时处理
            else:
                config_value = True
            if not config_key or config_value:
                enabled[name] = meta
        return enabled

    def clear(self):
        """清空注册表（主要用于热重载）"""
        self._metadata.clear()
        self._alias_map.clear()


# 全局单例实例
registry = CommandMetadataRegistry()