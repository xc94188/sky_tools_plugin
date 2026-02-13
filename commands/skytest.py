"""
光遇服务器状态查询命令
"""
import asyncio
import time
from typing import Tuple, Optional, Dict, Any

import aiohttp

from src.plugin_system import BaseCommand

from ..message_forward_helper import MessageForwardHelper


class SkyTestCommand(BaseCommand):
    """光遇服务器状态查询命令"""

    command_name = "skytest"
    command_description = "查询光遇服务器状态"
    command_pattern = r"^{escaped_prefix}skytest$"

    async def execute(self) -> Tuple[bool, Optional[str], bool]:
        # 检查功能是否启用
        if not self.get_config("settings.enable_skytest_query", True):
            await self.send_text("❌ 服务器状态查询功能未启用")
            return False, "服务器状态查询功能未启用", True

        try:
            skytest_url = self.get_config("skytest_api.url")
            skytest_key = self.get_config("skytest_api.key")
            timeout = self.get_config("skytest_api.timeout")

            if not skytest_key or skytest_key == "你的服务器状态API密钥":
                await self.send_text("❌ 插件未配置服务器状态API密钥")
                return False, "服务器状态API密钥未配置", True

            result = await self._get_server_status(skytest_url, skytest_key, timeout)

            if result["success"]:
                await MessageForwardHelper.send_forward_message(self, [result["message"]])
                return True, "服务器状态查询成功", True
            else:
                await MessageForwardHelper.send_forward_message(self, [result["message"]])
                return False, result.get("error", "服务器状态查询失败"), True

        except Exception as e:
            await MessageForwardHelper.send_forward_message(self, [f"❌ 查询错误: {str(e)}"])
            return False, f"服务器状态查询错误: {str(e)}", True

    async def _get_server_status(self, url: str, key: str, timeout: int) -> Dict[str, Any]:
        """调用服务器状态API"""
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
                            "error": f"HTTP {response.status}: {error_detail}"
                        }

                    data = await response.json()
                    if "msg" not in data:
                        return {
                            "success": False,
                            "message": "❌ API返回数据格式错误",
                            "error": "缺少msg字段"
                        }

                    server_status = data["msg"]
                    return {
                        "success": True,
                        "message": f"🔍 服务器状态查询结果：\n━━━━━━━━━━━━━━━━\n{server_status}\n━━━━━━━━━━━━━━━━"
                    }

            except aiohttp.ClientError as e:
                return {
                    "success": False,
                    "message": f"❌ 网络错误: {str(e)}",
                    "error": f"网络错误: {str(e)}"
                }
            except asyncio.TimeoutError:
                return {
                    "success": False,
                    "message": "❌ 请求超时",
                    "error": "请求超时"
                }
            except Exception as e:
                return {
                    "success": False,
                    "message": f"❌ 请求错误: {str(e)}",
                    "error": f"未知错误: {str(e)}"
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