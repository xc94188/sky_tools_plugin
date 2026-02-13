"""
芒果工具平台身高查询实现
"""
import asyncio
from typing import Dict, Any, Optional

import aiohttp

from .base import BasePlatformHandler
from .registry import register_platform
from ..utils.validators import validate_game_id, validate_friend_code


@register_platform(name="mango", aliases=["mg", "芒果"])
class MangoPlatformHandler(BasePlatformHandler):
    """芒果平台处理器"""

    def __init__(self):
        self.height_types = {
            "very_short": "非常矮",
            "short": "矮",
            "medium": "中等",
            "tall": "高",
            "very_tall": "非常高",
        }

    async def query(
        self, url: str, key: str, game_id: str, friend_code: Optional[str], timeout: int
    ) -> Dict[str, Any]:
        params = {
            "key": key,
            "id": game_id.lower(),
        }
        if friend_code:
            params["inviteCode"] = friend_code.upper()

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=params, timeout=timeout) as resp:
                    return await self._handle_response(resp)
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
            data = await response.json()
            if "data" not in data or not data["data"]:
                error_msg = data.get("message", "未知错误")
                return {
                    "success": False,
                    "message": f"❌ API返回错误: {error_msg}",
                    "error": error_msg,
                }
            return {"success": True, "message": self._format_data(data["data"])}
        except Exception as e:
            return {
                "success": False,
                "message": f"❌ 解析响应失败: {str(e)}",
                "error": f"解析错误: {str(e)}",
            }

    def _format_data(self, data: Dict[str, Any]) -> str:
        """格式化数据"""
        try:
            s_value = self._safe_float(data.get("s"))
            h_value = self._safe_float(data.get("h"))
            height_value = self._safe_float(data.get("height"), h_value)
            max_height = self._safe_float(data.get("max"), 1.0)
            min_height = self._safe_float(data.get("min"), 14.0)

            height_type = self._calculate_height_type(height_value, min_height, max_height)
            to_min_diff = max(0, min_height - height_value) if height_value is not None and min_height is not None else 0
            to_max_diff = max(0, height_value - max_height) if height_value is not None and max_height is not None else 0

            result = [
                "✨ 芒果平台 - 身高查询结果",
                "━━━━━━━━━━━━━━━━━━━━",
                f"📊 体型值(s值): {s_value:.8f}" if s_value is not None else "📊 体型值(s值): 未知",
                f"📊 身高值(h值): {h_value:.8f}" if h_value is not None else "📊 身高值(h值): 未知",
                f"📈 最高身高: {max_height:.8f}" if max_height is not None else "📈 最高身高: 未知",
                f"📉 最矮身高: {min_height:.8f}" if min_height is not None else "📉 最矮身高: 未知",
                f"✨ 当前身高: {height_value:.8f}" if height_value is not None else "✨ 当前身高: 未知",
                f"🏷️ 身高类型: {height_type}",
                "",
                f"🎯 距离最矮: {to_min_diff:.8f}" if to_min_diff > 0 else "🎯 已达到最矮身高",
                f"🎯 距离最高: {to_max_diff:.8f}" if to_max_diff > 0 else "🎯 已达到最高身高",
                "━━━━━━━━━━━━━━━━━━━━"
            ]

            return "\n".join(result)
        except Exception as e:
            return f"❌ 解析芒果平台数据失败: {str(e)}"

    def _safe_float(self, value, default=None):
        """安全转换浮点数"""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def _calculate_height_type(self, h_value: float, min_height: float, max_height: float) -> str:
        """计算身高类型"""
        if h_value is None or min_height is None or max_height is None:
            return "未知"

        height_range = min_height - max_height
        if height_range <= 0:
            return self.height_types["medium"]

        position = (h_value - max_height) / height_range

        if position < 0.2:
            return self.height_types["very_tall"]
        elif position < 0.4:
            return self.height_types["tall"]
        elif position < 0.6:
            return self.height_types["medium"]
        elif position < 0.8:
            return self.height_types["short"]
        else:
            return self.height_types["very_short"]

    async def _parse_error_response(self, response) -> str:
        """解析错误响应"""
        try:
            error_data = await response.json()
            if "message" in error_data:
                return error_data["message"]
            return str(error_data)
        except:
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