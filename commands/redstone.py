"""
光遇红石位置查询命令
"""
import asyncio
import base64
import time
from typing import Tuple, Optional, Dict, Any

import aiohttp

from .base import SkyBaseCommand
from ..message_forward_helper import MessageForwardHelper


class RedStoneQueryCommand(SkyBaseCommand):
    """光遇红石位置查询命令"""

    command_name = "redstone"
    command_description = "获取光遇红石位置图片"
    command_pattern = r"^{escaped_prefix}(?:redstone|hs|红石|红石位置)$"

    async def execute(self) -> Tuple[bool, Optional[str], bool]:
        # 检查功能是否启用
        if not self.get_config("settings.enable_redstone_query", True):
            await self.send_text("❌ 红石查询功能未启用")
            return False, "红石查询功能未启用", True

        try:
            redstone_url = self.get_config("redstone_api.url")
            redstone_key = self.get_config("redstone_api.key")
            timeout = self.get_config("redstone_api.timeout")

            if not redstone_key or redstone_key == "你的红石API密钥":
                await self.send_text("❌ 插件未配置红石API密钥")
                return False, "红石API密钥未配置", True

            await self.send_text("🔄 正在获取红石位置...")

            result = await self._get_redstone_image(redstone_url, redstone_key, timeout)

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
                        return True, "红石位置发送成功", True
                    else:
                        await self.send_text("❌ 发送图片失败")
                        return False, "发送图片失败", True
                else:
                    await self.send_text("❌ 图片数据为空")
                    return False, "图片数据为空", True
            else:
                await MessageForwardHelper.send_forward_message(self, [result["message"]])
                return False, result.get("error", "获取红石位置失败"), True

        except Exception as e:
            await MessageForwardHelper.send_forward_message(self, [f"❌ 获取错误: {str(e)}"])
            return False, f"获取红石位置错误: {str(e)}", True

    async def _get_redstone_image(self, url: str, key: str, timeout: int) -> Dict[str, Any]:
        """调用红石位置API"""
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
                    image_base64 = base64.b64encode(image_data).decode('utf-8')
                    return {
                        "success": True,
                        "image_data": image_base64,
                        "message": "获取红石位置成功"
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