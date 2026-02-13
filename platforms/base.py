"""
平台处理器抽象基类
定义所有身高查询平台必须实现的接口
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BasePlatformHandler(ABC):
    """平台处理器基类"""

    @abstractmethod
    async def query(
        self, url: str, key: str, game_id: str, friend_code: Optional[str], timeout: int
    ) -> Dict[str, Any]:
        """
        执行身高查询
        Returns:
            Dict: 包含 success, message, 可能包含 error
        """
        pass