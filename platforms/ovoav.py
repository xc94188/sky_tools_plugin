"""
独角兽平台身高查询实现
"""
import asyncio
import re
from typing import Dict, Any, Optional

import aiohttp

from .base import BasePlatformHandler
from .registry import register_platform
from ..utils.validators import validate_game_id, validate_friend_code


@register_platform(name="ovoav", aliases=["独角兽", "djs"])
class OvoavPlatformHandler(BasePlatformHandler):
    """独角兽平台处理器"""

    async def query(
        self, url: str, key: str, game_id: str, friend_code: Optional[str], timeout: int
    ) -> Dict[str, Any]:
        params = {"key": key}
        if game_id and not validate_game_id(game_id) and validate_friend_code(game_id):
            params["id"] = game_id.upper()
        elif game_id and validate_game_id(game_id):
            params["id"] = game_id.lower()
        elif friend_code and validate_friend_code(friend_code):
            params["id"] = friend_code.upper()
        else:
            return {
                "success": False,
                "message": "❌ 请提供有效的游戏长ID或好友码",
                "error": "缺少有效参数",
            }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params, timeout=timeout) as response:
                    return await self._handle_response(response)
            except Exception as e:
                return self._handle_error(e)

    async def _handle_response(self, response) -> Dict[str, Any]:
        if response.status != 200:
            error_detail = await self._parse_error_response(response)
            return {
                "success": False,
                "message": f"❌ API请求失败: {error_detail}",
                "error": f"HTTP {response.status}: {error_detail}",
            }

        try:
            response_text = await response.text()
            cleaned_text = self._clean_html_response(response_text)
            return {
                "success": True,
                "message": cleaned_text,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"❌ 解析响应失败: {str(e)}",
                "error": f"解析错误: {str(e)}",
            }

    def _clean_html_response(self, html_text: str) -> str:
        """清理HTML响应"""
        cleaned = re.sub(r"<[^>]+>", "", html_text)
        cleaned = re.sub(r"[ ]+", " ", cleaned)
        return cleaned.strip()

    async def _parse_error_response(self, response) -> str:
        """解析错误响应"""
        try:
            return await response.text()
        except:
            return f"状态码: {response.status}"

    def _handle_error(self, error) -> Dict[str, Any]:
        """处理错误"""
        if isinstance(error, aiohttp.ClientError):
            return {
                "success": False,
                "message": f"❌ 网络请求错误: {str(error)}",
                "error": f"网络错误: {str(error)}",
            }
        elif isinstance(error, asyncio.TimeoutError):
            return {"success": False, "message": "❌ 请求超时", "error": "请求超时"}
        else:
            return {
                "success": False,
                "message": f"❌ 请求错误: {str(error)}",
                "error": f"未知错误: {str(error)}",
            }