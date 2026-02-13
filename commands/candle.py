"""
光遇大蜡烛位置查询命令
"""
import asyncio
import base64
import time
from typing import Tuple, Optional, Dict, Any

import aiohttp

from .base import SkyBaseCommand
from ..message_forward_helper import MessageForwardHelper


class CandleQueryCommand(SkyBaseCommand):
    """光遇大蜡烛位置查询命令"""

    command_name = "candle"
    command_description = "获取光遇大蜡烛位置图片"
    command_pattern = r"^{escaped_prefix}(?:candle|dl|大蜡|大蜡烛)$"

    async def execute(self) -> Tuple[bool, Optional[str], bool]:
        # 检查功能是否启用
        if not self.get_config("settings.enable_candle_query", True):
            await self.send_text("❌ 大蜡烛查询功能未启用")
            return False, "大蜡烛查询功能未启用", True

        try:
            candle_url = self.get_config("candle_api.url")
            candle_key = self.get_config("candle_api.key")
            timeout = self.get_config("candle_api.timeout")

            if not candle_key or candle_key == "你的大蜡烛API密钥":
                await self.send_text("❌ 插件未配置大蜡烛API密钥")
                return False, "大蜡烛API密钥未配置", True

            await self.send_text("🔄 正在获取大蜡烛位置...")

            result = await self._get_candle_image(candle_url, candle_key, timeout)

            if result["success"]:
                image_base64 = result["image_data"]
                if image_base64:
                    if image_base64.startswith('data:'):
                        import re
                        match = re.search(r'base64,(.*)', image_base64)
                        if match:
                            image_base64 = match.group(1)

                    success = await MessageForwardHelper.send_forward_message(self, [image_base64])
                    if success:
                        return True, "大蜡烛位置发送成功", True
                    else:
                        await self.send_text("❌ 发送图片失败")
                        return False, "发送图片失败", True
                else:
                    await self.send_text("❌ 图片数据为空")
                    return False, "图片数据为空", True
            else:
                await MessageForwardHelper.send_forward_message(self, [result["message"]])
                return False, result.get("error", "获取大蜡烛位置失败"), True

        except asyncio.TimeoutError:
            await self.send_text("❌ 获取超时")
            return False, "API请求超时", True
        except Exception as e:
            await MessageForwardHelper.send_forward_message(self, [f"❌ 获取错误: {str(e)}"])
            return False, f"获取大蜡烛位置错误: {str(e)}", True

    async def _get_candle_image(self, url: str, key: str, timeout: int) -> Dict[str, Any]:
        """调用大蜡烛位置API"""
        params = {
            "key": key,
            "time": str(int(time.time()))
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params, timeout=timeout) as response:
                    if response.status != 200:
                        error_detail = await self._parse_error_response(response)
                        return {
                            "success": False,
                            "message": f"❌ API请求失败: {error_detail}",
                            "error": f"HTTP {response.status}: {error_detail}",
                            "image_data": None
                        }

                    image_data = await response.read()
                    if not image_data:
                        return {
                            "success": False,
                            "message": "❌ 图片数据为空",
                            "error": "空图片数据",
                            "image_data": None
                        }

                    if len(image_data) < 1024:
                        return {
                            "success": False,
                            "message": "❌ 图片数据过小",
                            "error": "图片数据过小",
                            "image_data": None
                        }

                    image_base64 = base64.b64encode(image_data).decode('utf-8')
                    return {
                        "success": True,
                        "image_data": image_base64,
                        "message": "获取大蜡烛位置成功"
                    }

            except aiohttp.ClientError as e:
                return {
                    "success": False,
                    "message": f"❌ 网络错误: {str(e)}",
                    "error": f"网络错误: {str(e)}",
                    "image_data": None
                }
            except asyncio.TimeoutError:
                return {
                    "success": False,
                    "message": "❌ 请求超时",
                    "error": "请求超时",
                    "image_data": None
                }
            except Exception as e:
                return {
                    "success": False,
                    "message": f"❌ 请求错误: {str(e)}",
                    "error": f"未知错误: {str(e)}",
                    "image_data": None
                }

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