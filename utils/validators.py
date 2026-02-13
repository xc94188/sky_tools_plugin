"""
通用验证函数
"""
import re


def validate_game_id(game_id: str) -> bool:
    """验证游戏ID格式 (UUID)"""
    uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    return re.match(uuid_pattern, game_id.lower()) is not None


def validate_friend_code(friend_code: str) -> bool:
    """验证好友码格式 (XXXX-XXXX-XXXX)"""
    pattern = r"^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$"
    return re.match(pattern, friend_code.upper()) is not None