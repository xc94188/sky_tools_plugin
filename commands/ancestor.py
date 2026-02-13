"""
光遇复刻先祖位置查询命令
"""
import asyncio
import base64
import re
import time
from typing import Tuple, Optional, Dict, Any

import aiohttp

from .base import SkyBaseCommand
from ..message_forward_helper import MessageForwardHelper


class AncestorQueryCommand(SkyBaseCommand):
    """光遇复刻先祖位置查询命令"""

    command_name = "ancestor"
    command_description = "获取光遇复刻先祖位置图片"
    command_pattern = r"^{escaped_prefix}(?:ancestor|fk|复刻|先祖|复刻先祖)$"

    async def execute(self) -> Tuple[bool, Optional[str], bool]:
        # 检查功能是否启用
        if not self.get_config("settings.enable_ancestor_query", True):
            await self.send_text("❌ 复刻先祖查询功能未启用")
            return False, "复刻先祖查询功能未启用", True

        try:
            ancestor_url = self.get_config("ancestor_api.url")
            ancestor_key = self.get_config("ancestor_api.key")
            timeout = self.get_config("ancestor_api.timeout")

            if not ancestor_key or ancestor_key == "你的复刻先祖API密钥":
                await self.send_text("❌ 插件未配置复刻先祖API密钥")
                return False, "复刻先祖API密钥未配置", True

            await self.send_text("🔄 正在获取复刻先祖信息...")

            result = await self._get_ancestor_info(ancestor_url, ancestor_key, timeout)

            if result["success"]:
                # 构建合并消息列表 [复刻图片, 复刻文本]
                merged_messages = []
                
                # 先加图片，再加文本（顺序可根据喜好调整）
                if result.get("image_data"):
                    merged_messages.append(result["image_data"])
                if result.get("text_info"):
                    merged_messages.append(result["text_info"])
                
                if merged_messages:
                    # 将文本和图片作为一条合并消息发送（列表形式）
                    success = await MessageForwardHelper.send_forward_message(
                        self, 
                        [merged_messages]  # 注意：外层再套一层列表，表示这是一个独立的合并消息节点
                    )
                    if success:
                        return True, "复刻先祖信息发送成功", True
                    else:
                        await self.send_text("❌ 发送图片失败")
                        return False, "发送图片失败", True
                else:
                    await self.send_text("❌ 未找到复刻先祖信息")
                    return False, "未找到复刻先祖信息", True
            else:
                await MessageForwardHelper.send_forward_message(self, [result["message"]])
                return False, result.get("error", "获取复刻先祖信息失败"), True

        except Exception as e:
            await MessageForwardHelper.send_forward_message(self, [f"❌ 获取错误: {str(e)}"])
            return False, f"获取复刻先祖信息错误: {str(e)}", True

    async def _get_ancestor_info(self, url: str, key: str, timeout: int) -> Dict[str, Any]:
        """调用复刻先祖信息API"""
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

                    data = await response.json()

                    if data.get("code") != 200:
                        error_msg = data.get("msg", "未知错误")
                        return {
                            "success": False,
                            "message": f"❌ API返回错误: {error_msg}",
                            "error": error_msg,
                            "image_data": None
                        }

                    image_data = await self._download_image_from_url(data)
                    text_info = self._build_ancestor_text(data)

                    return {
                        "success": True,
                        "image_data": image_data,
                        "text_info": text_info,
                        "message": "获取复刻先祖信息成功"
                    }

            except Exception as e:
                return {
                    "success": False,
                    "message": f"❌ 请求错误: {str(e)}",
                    "error": f"未知错误: {str(e)}",
                    "image_data": None
                }

    async def _download_image_from_url(self, data: Dict[str, Any]) -> Optional[str]:
        """从URL下载图片并转换为base64"""
        try:
            image_urls = data.get("data", {}).get("image", [])
            if not image_urls:
                return None

            image_url = image_urls[0]
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        if image_data:
                            return base64.b64encode(image_data).decode('utf-8')
            return None
        except Exception as e:
            return None

    def _build_ancestor_text(self, data: Dict[str, Any]) -> str:
        """构建复刻先祖文字信息"""
        try:
            data_info = data.get("data", {})
            duantext = data_info.get("duantext", "")
            event_start = data_info.get("event_start", "")
            event_end = data_info.get("event_end", "")
            screen_name = data_info.get("screen_name", "")

            clean_text = duantext.replace("#Sky光遇#", "").replace("#光遇旅行先祖#", "").replace("#sky光遇[超话]#", "").strip()
            clean_text = re.sub(r'\n+', '\n', clean_text)

            text_lines = [
                "✨ 本周复刻先祖信息",
                "━━━━━━━━━━━━━━━━",
                clean_text,
                "",
                f"📅 开始时间: {event_start}",
                f"📅 结束时间: {event_end}",
                f"📱 信息来源: {screen_name}",
                "━━━━━━━━━━━━━━━━"
            ]

            return "\n".join([line for line in text_lines if line.strip()])
        except Exception as e:
            return "✨ 本周复刻先祖信息已更新"

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