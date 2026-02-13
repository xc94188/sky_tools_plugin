"""
应天平台身高查询实现
"""
import asyncio
import json
from typing import Dict, Any, Optional

import aiohttp

from .base import BasePlatformHandler
from .registry import register_platform
from ..utils.validators import validate_game_id, validate_friend_code


@register_platform(name="yingtian", aliases=["应天", "yt"])
class YingtianPlatformHandler(BasePlatformHandler):
    """应天平台处理器"""

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
        params = {"key": key}

        if not game_id or not validate_game_id(game_id):
            return {
                "success": False,
                "message": "❌ 请提供有效的游戏长ID",
                "error": "缺少游戏长ID",
            }

        params["cx"] = game_id.lower()

        if friend_code:
            if not validate_friend_code(friend_code):
                return {
                    "success": False,
                    "message": "❌ 好友码格式错误",
                    "error": "好友码格式错误",
                }
            params["code"] = friend_code.upper()

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
            data = json.loads(response_text)

            if data.get("code") != 200:
                error_msg = data.get("msg", "未知错误")
                return {
                    "success": False,
                    "message": f"❌ API返回错误: {error_msg}",
                    "error": error_msg,
                }

            return {"success": True, "message": self._format_data(data)}
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "message": f"❌ 解析JSON失败: {str(e)}",
                "error": f"JSON解析错误: {str(e)}",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"❌ 解析响应失败: {str(e)}",
                "error": f"解析错误: {str(e)}",
            }

    def _format_data(self, data: Dict[str, Any]) -> str:
        """格式化数据"""
        try:
            data_info = data.get("data", {})
            score_info = data.get("score", {})
            adorn_info = data.get("adorn", {})
            action_info = data.get("action", {})

            scale = self._safe_float(data_info.get("scale"))
            height = self._safe_float(data_info.get("height"))
            current_height = self._safe_float(data_info.get("currentHeight"))
            max_height = self._safe_float(data_info.get("maxHeight"))
            min_height = self._safe_float(data_info.get("minHeight"))
            height_desc = data_info.get("heightDesc", "未知")

            if height_desc.startswith("当前身高："):
                height_desc = height_desc.replace("当前身高：", "").strip()

            result = [
                "✨ 应天平台 - 身高查询结果",
                "━━━━━━━━━━━━━━━━━━━━",
                f"📊 体型值(s值): {scale}" if scale is not None else "📊 体型值(s值): 未知",
                f"📊 身高值(h值): {height}" if height is not None else "📊 身高值(h值): 未知",
                f"✨ 当前身高: {current_height}" if current_height is not None else "✨ 当前身高: 未知",
                f"📈 最高身高: {max_height}" if max_height is not None else "📈 最高身高: 未知",
                f"📉 最矮身高: {min_height}" if min_height is not None else "📉 最矮身高: 未知",
                f"🏷️ 身高描述: {height_desc}",
                "",
                "📊 评分信息:",
                f"  • 体型值评分: {score_info.get('scaleScore', '未知')}分",
                f"  • 身高值评分: {score_info.get('heightScore', '未知')}分",
                f"  • 当前身高评分: {score_info.get('currentHeightScore', '未知')}分",
                f"  • 最高身高评分: {score_info.get('maxHeightScore', '未知')}分",
                f"  • 最矮身高评分: {score_info.get('minHeightScore', '未知')}分",
                "",
                "👗 装扮信息:",
                f"  • 斗篷: {adorn_info.get('cloak', '未知')}",
                f"  • 发型: {adorn_info.get('hair', '未知')}",
                f"  • 面具: {adorn_info.get('mask', '未知')}",
                f"  • 裤子: {adorn_info.get('pants', '未知')}",
                f"  • 道具: {adorn_info.get('prop', '未知')}",
                f"  • 头饰: {adorn_info.get('horn', '未知')}",
                f"  • 项链: {adorn_info.get('neck', '未知')}",
                "",
                "🎭 动作信息:",
                f"  • 站姿: {action_info.get('attitude', '未知')}",
                f"  • 叫声: {action_info.get('voice', '未知')}",
                "━━━━━━━━━━━━━━━━━━━━",
            ]

            return "\n".join([line for line in result if line.strip()])
        except Exception as e:
            return f"❌ 解析应天平台数据失败: {str(e)}"

    def _safe_float(self, value, default=None):
        """安全转换浮点数"""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    async def _parse_error_response(self, response) -> str:
        """解析错误响应"""
        try:
            error_data = await response.json()
            return error_data.get("msg", str(error_data))
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