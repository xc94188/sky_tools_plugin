from typing import List, Tuple, Type, Any, Optional, Dict
import aiohttp
import asyncio
import re
import base64
import time
from src.plugin_system import (
    BasePlugin,
    register_plugin,
    BaseCommand,
    ComponentInfo,
    ConfigField,
    get_logger
)

logger = get_logger('sky_tools_plugin')

class HelpCommand(BaseCommand):
    """光遇工具帮助命令"""
    
    command_name = "skytools"
    command_description = "查看光遇工具插件所有功能"
    command_pattern = r"^/skytools$"
    
    async def execute(self) -> Tuple[bool, Optional[str], bool]:
        """显示帮助信息"""
        help_text = self._get_help_text()
        await self.send_text(help_text)
        return True, "显示帮助信息", True
    
    def _get_help_text(self) -> str:
        """生成帮助文本"""
        return """✨ 光遇工具插件使用说明 ✨

📋 可用命令:

📏 /height <游戏长ID> [好友码]
   → 查询光遇角色身高数据

🖼️ /task 或 /rw 或 /任务 或 /每日任务
   → 获取每日任务图片

🕯️ /candle 或 /dl 或 /大蜡 或 /大蜡烛
   → 获取大蜡烛位置图片

👴 /ancestor 或 /fk 或 /复刻 或 /复刻先祖
   → 获取复刻先祖位置

🔮 /magic 或 /mf 或 /魔法 或 /每日魔法
   → 获取每日魔法图片

🕯️ /scandel 或 /jl 或 /季蜡 或 /季节蜡烛 或 /季蜡位置
   → 获取每日季蜡位置图片

📅 /calendar 或 /rl 或 /日历 或 /活动日历
   → 获取光遇日历图片

🔴 /redstone 或 /hs 或 /红石 或 /红石位置
   → 获取红石位置图片

ℹ️ /skytools
   → 显示本帮助信息

🔧 配置说明:
• 功能需前往对应平台获取API密钥
• 请在插件配置文件中设置相应的API密钥

💡 获取游戏长ID:
游戏内右上角设置→精灵→询问"长id"

如有问题请检查插件配置或联系管理员"""

class HeightQueryCommand(BaseCommand):
    """光遇身高查询命令"""
    
    command_name = "height"
    command_description = "查询光遇国服玩家身高数据"
    command_pattern = r"^/height(?:\s+(?P<game_id>[^\s]+)(?:\s+(?P<friend_code>[^\s]+))?)?$"
    
    # 身高类型分类
    HEIGHT_TYPES = {
        "very_short": "非常矮",
        "short": "矮",
        "medium": "中等",
        "tall": "高",
        "very_tall": "非常高"
    }
    
    async def execute(self) -> Tuple[bool, Optional[str], bool]:
        """执行身高查询命令"""
        try:
            # 获取匹配的参数
            game_id = self.matched_groups.get("game_id")
            friend_code = self.matched_groups.get("friend_code")
            
            # 处理帮助命令
            if not game_id or game_id.lower() == "help":
                help_text = self._get_help_text()
                await self.send_text(help_text)
                return True, "显示帮助信息", True
            
            # 验证游戏ID格式 (UUID格式)
            if not self._validate_game_id(game_id):
                await self.send_text("❌ 游戏ID格式错误")
                return False, "游戏ID格式错误", True
            
            # 验证好友码格式 (可选)
            if friend_code and not self._validate_friend_code(friend_code):
                await self.send_text("❌ 好友码格式错误")
                return False, "好友码格式错误", True
            
            # 获取配置
            api_url = self.get_config("height_api.url")
            api_key = self.get_config("height_api.key")
            timeout = self.get_config("height_api.timeout")
            
            if not api_key or api_key == "你的身高API密钥":
                await self.send_text("❌ 插件未配置身高API密钥")
                return False, "身高API密钥未配置", True
            
            # 调用API查询身高数据
            result = await self._query_height_api(api_url, api_key, game_id, friend_code, timeout)
            
            if result["success"]:
                await self.send_text(result["message"])
                return True, "身高查询成功", True
            else:
                await self.send_text(result["message"])
                return False, result.get("error", "身高查询失败"), True
                
        except asyncio.TimeoutError:
            await self.send_text("❌ 查询超时")
            return False, "API请求超时", True
        except Exception as e:
            await self.send_text(f"❌ 查询错误: {str(e)}")
            return False, f"查询错误: {str(e)}", True
    
    @staticmethod
    def _validate_game_id(game_id: str) -> bool:
        """验证游戏ID格式 (UUID格式)"""
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        return re.match(uuid_pattern, game_id.lower()) is not None
    
    @staticmethod
    def _validate_friend_code(friend_code: str) -> bool:
        """验证好友码格式"""
        friend_code_pattern = r"^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$"
        return re.match(friend_code_pattern, friend_code.upper()) is not None
    
    def _get_help_text(self) -> str:
        """获取帮助文本"""
        return """📏 身高查询使用说明

使用方法:
/height <游戏长ID> [好友码]

参数说明:
• 游戏长ID: UUID格式的游戏ID
• 好友码: 可选的好友码参数

获取方式:
• 长ID: 游戏右上角设置→精灵→询问"长id"
• 好友码: 游戏右上角设置→好友→使用编号→设置昵称后获取

示例:
/height xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
/height xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx XXXX-XXXX-XXXX"""

    async def _query_height_api(self, url: str, key: str, game_id: str, 
                              friend_code: Optional[str], timeout: int) -> Dict[str, Any]:
        """调用身高查询API"""
        params = {
            "key": key,
            "id": game_id.lower()
        }
        
        if friend_code:
            params["inviteCode"] = friend_code.upper()
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=params, timeout=timeout) as response:
                    if response.status != 200:
                        error_detail = await self._parse_error_response(response)
                        if "用户数据已过期" in error_detail:
                            return {
                                "success": False,
                                "message": "❌ 用户数据已过期",
                                "error": f"HTTP {response.status}: {error_detail}"
                            }
                        return {
                            "success": False,
                            "message": f"❌ API请求失败: {error_detail}",
                            "error": f"HTTP {response.status}: {error_detail}"
                        }
                    
                    try:
                        data = await response.json()
                    except Exception as e:
                        return {
                            "success": False,
                            "message": f"❌ 解析响应失败: {str(e)}",
                            "error": f"解析错误: {str(e)}"
                        }
                    
                    if "data" not in data or not data["data"]:
                        error_msg = data.get("message", "未知错误")
                        return {
                            "success": False,
                            "message": f"❌ API返回错误: {error_msg}",
                            "error": error_msg
                        }
                    
                    formatted_result = self._format_height_data(data["data"])
                    return {
                        "success": True,
                        "message": formatted_result
                    }
                    
            except aiohttp.ClientError as e:
                return {
                    "success": False,
                    "message": f"❌ 网络请求错误: {str(e)}",
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
    
    def _format_height_data(self, data: Dict[str, Any]) -> str:
        """格式化身高数据"""
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
                "✨ 身高查询结果",
                "━━━━━━━━━━━━━━━━",
                f"📊 体型值(s值): {s_value:.8f}" if s_value is not None else "📊 体型值(s值): None",
                f"📊 身高值(h值): {h_value:.8f}" if h_value is not None else "📊 身高值(h值): None",
                f"📈 最高身高: {max_height:.8f}" if max_height is not None else "📈 最高身高: None",
                f"📉 最矮身高: {min_height:.8f}" if min_height is not None else "📉 最矮身高: None",
                f"✨ 当前身高: {height_value:.8f}" if height_value is not None else "✨ 当前身高: None",
                f"🏷️ 身高类型: {height_type}",
                "",
                f"🎯 距离最矮: {to_min_diff:.8f}" if to_min_diff > 0 else "🎯 已达到最矮身高",
                f"🎯 距离最高: {to_max_diff:.8f}" if to_max_diff > 0 else "🎯 已达到最高身高",
                "━━━━━━━━━━━━━━━━"
            ]
            
            return "\n".join(result)
        except (ValueError, TypeError) as e:
            return f"❌ 解析数据失败: {str(e)}"
    
    def _safe_float(self, value, default=None):
        """安全地将值转换为浮点数，处理 None 值"""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def _calculate_height_type(self, h_value: float, min_height: float, max_height: float) -> str:
        """计算身高类型"""
        if h_value is None or min_height is None or max_height is None:
            return "None"
        
        height_range = min_height - max_height
        if height_range <= 0:
            return self.HEIGHT_TYPES["medium"]
        
        position = (h_value - max_height) / height_range
        
        if position < 0.2:
            return self.HEIGHT_TYPES["very_tall"]
        elif position < 0.4:
            return self.HEIGHT_TYPES["tall"]
        elif position < 0.6:
            return self.HEIGHT_TYPES["medium"]
        elif position < 0.8:
            return self.HEIGHT_TYPES["short"]
        else:
            return self.HEIGHT_TYPES["very_short"]

class TaskQueryCommand(BaseCommand):
    """光遇任务图片查询命令"""
    
    command_name = "task"
    command_description = "获取光遇任务图片"
    command_pattern = r"^/(?:task|rw|任务|每日任务)$"
    
    async def execute(self) -> Tuple[bool, Optional[str], bool]:
        """执行任务图片查询命令"""
        try:
            task_url = self.get_config("task_api.url")
            task_key = self.get_config("task_api.key")
            timeout = self.get_config("task_api.timeout")
            
            if not task_key or task_key == "你的任务API密钥":
                await self.send_text("❌ 插件未配置任务API密钥")
                return False, "任务API密钥未配置", True
            
            await self.send_text("🔄 正在获取任务图片...")
            
            result = await self._get_task_image(task_url, task_key, timeout)
            
            if result["success"]:
                image_base64 = result["image_data"]
                if image_base64:
                    if image_base64.startswith('data:'):
                        import re
                        match = re.search(r'base64,(.*)', image_base64)
                        if match:
                            image_base64 = match.group(1)
                    
                    success = await self.send_image(image_base64)
                    if success:
                        return True, "任务图片发送成功", True
                    else:
                        await self.send_text("❌ 发送图片失败")
                        return False, "发送图片失败", True
                else:
                    await self.send_text("❌ 图片数据为空")
                    return False, "图片数据为空", True
            else:
                await self.send_text(result["message"])
                return False, result.get("error", "获取任务图片失败"), True
                
        except asyncio.TimeoutError:
            await self.send_text("❌ 获取超时")
            return False, "API请求超时", True
        except Exception as e:
            await self.send_text(f"❌ 获取错误: {str(e)}")
            return False, f"获取任务图片错误: {str(e)}", True
    
    async def _get_task_image(self, url: str, key: str, timeout: int) -> Dict[str, Any]:
        """调用任务图片API"""
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
                    
                    logger.info(f"成功获取任务图片，数据大小: {len(image_data)} 字节")
                    
                    return {
                        "success": True,
                        "image_data": image_base64,
                        "message": "获取任务图片成功"
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

class CandleQueryCommand(BaseCommand):
    """光遇大蜡烛位置查询命令"""
    
    command_name = "candle"
    command_description = "获取光遇大蜡烛位置图片"
    command_pattern = r"^/(?:candle|dl|大蜡|大蜡烛)$"
    
    async def execute(self) -> Tuple[bool, Optional[str], bool]:
        """执行大蜡烛位置查询命令"""
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
                    
                    success = await self.send_image(image_base64)
                    if success:
                        return True, "大蜡烛位置发送成功", True
                    else:
                        await self.send_text("❌ 发送图片失败")
                        return False, "发送图片失败", True
                else:
                    await self.send_text("❌ 图片数据为空")
                    return False, "图片数据为空", True
            else:
                await self.send_text(result["message"])
                return False, result.get("error", "获取大蜡烛位置失败"), True
                
        except asyncio.TimeoutError:
            await self.send_text("❌ 获取超时")
            return False, "API请求超时", True
        except Exception as e:
            await self.send_text(f"❌ 获取错误: {str(e)}")
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
                    
                    logger.info(f"成功获取大蜡烛位置图片，数据大小: {len(image_data)} 字节")
                    
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

class AncestorQueryCommand(BaseCommand):
    """光遇复刻先祖位置查询命令"""
    
    command_name = "ancestor"
    command_description = "获取光遇复刻先祖位置图片"
    command_pattern = r"^/(?:ancestor|fk|复刻|先祖|复刻先祖)$"
    
    async def execute(self) -> Tuple[bool, Optional[str], bool]:
        """执行复刻先祖位置查询命令"""
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
                if result["image_data"]:
                    success = await self.send_image(result["image_data"])
                    if success:
                        # 发送文字信息
                        text_info = result.get("text_info", "")
                        if text_info:
                            await self.send_text(text_info)
                        return True, "复刻先祖信息发送成功", True
                    else:
                        await self.send_text("❌ 发送图片失败")
                        return False, "发送图片失败", True
                else:
                    await self.send_text("❌ 未找到复刻先祖图片")
                    return False, "未找到复刻先祖图片", True
            else:
                await self.send_text(result["message"])
                return False, result.get("error", "获取复刻先祖信息失败"), True
                
        except Exception as e:
            await self.send_text(f"❌ 获取错误: {str(e)}")
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
                    
                    # 检查API返回状态
                    if data.get("code") != 200:
                        error_msg = data.get("msg", "未知错误")
                        return {
                            "success": False,
                            "message": f"❌ API返回错误: {error_msg}",
                            "error": error_msg,
                            "image_data": None
                        }
                    
                    # 获取图片数据
                    image_data = await self._download_image_from_url(data)
                    
                    # 构建文字信息
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
            
            # 使用第一个图片URL
            image_url = image_urls[0]
            
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        if image_data:
                            image_base64 = base64.b64encode(image_data).decode('utf-8')
                            logger.info(f"成功下载复刻先祖图片，数据大小: {len(image_data)} 字节")
                            return image_base64
            
            return None
        except Exception as e:
            logger.error(f"下载图片失败: {str(e)}")
            return None
    
    def _build_ancestor_text(self, data: Dict[str, Any]) -> str:
        """构建复刻先祖文字信息"""
        try:
            data_info = data.get("data", {})
            duantext = data_info.get("duantext", "")
            event_start = data_info.get("event_start", "")
            event_end = data_info.get("event_end", "")
            screen_name = data_info.get("screen_name", "")
            
            # 清理文本中的多余标签和换行
            clean_text = duantext.replace("#Sky光遇#", "").replace("#光遇旅行先祖#", "").replace("#sky光遇[超话]#", "").strip()
            clean_text = re.sub(r'\n+', '\n', clean_text)  # 合并多个换行
            
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
            logger.error(f"构建文字信息失败: {str(e)}")
            return "✨ 本周复刻先祖信息已更新"

class MagicQueryCommand(BaseCommand):
    """光遇每日魔法查询命令"""
    
    command_name = "magic"
    command_description = "获取光遇每日魔法图片"
    command_pattern = r"^/(?:magic|mf|魔法|每日魔法)$"
    
    async def execute(self) -> Tuple[bool, Optional[str], bool]:
        """执行每日魔法查询命令"""
        try:
            magic_url = self.get_config("magic_api.url")
            magic_key = self.get_config("magic_api.key")
            timeout = self.get_config("magic_api.timeout")
            
            if not magic_key or magic_key == "你的每日魔法API密钥":
                await self.send_text("❌ 插件未配置每日魔法API密钥")
                return False, "每日魔法API密钥未配置", True
            
            await self.send_text("🔄 正在获取每日魔法...")
            
            result = await self._get_magic_image(magic_url, magic_key, timeout)
            
            if result["success"]:
                image_base64 = result["image_data"]
                if image_base64:
                    if image_base64.startswith('data:'):
                        import re
                        match = re.search(r'base64,(.*)', image_base64)
                        if match:
                            image_base64 = match.group(1)
                    
                    success = await self.send_image(image_base64)
                    if success:
                        return True, "每日魔法发送成功", True
                    else:
                        await self.send_text("❌ 发送图片失败")
                        return False, "发送图片失败", True
                else:
                    await self.send_text("❌ 图片数据为空")
                    return False, "图片数据为空", True
            else:
                await self.send_text(result["message"])
                return False, result.get("error", "获取每日魔法失败"), True
                
        except Exception as e:
            await self.send_text(f"❌ 获取错误: {str(e)}")
            return False, f"获取每日魔法错误: {str(e)}", True
    
    async def _get_magic_image(self, url: str, key: str, timeout: int) -> Dict[str, Any]:
        """调用每日魔法API"""
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
                        "message": "获取每日魔法成功"
                    }
                    
            except Exception as e:
                return {
                    "success": False,
                    "message": f"❌ 请求错误: {str(e)}",
                    "error": f"未知错误: {str(e)}",
                    "image_data": None
                }

class SeasonCandleQueryCommand(BaseCommand):
    """光遇每日季蜡位置查询命令"""
    
    command_name = "season_candle"
    command_description = "获取光遇每日季蜡位置图片"
    command_pattern = r"^/(?:scandel|jl|季蜡|季节蜡烛|季蜡位置)$"
    
    async def execute(self) -> Tuple[bool, Optional[str], bool]:
        """执行每日季蜡位置查询命令"""
        try:
            season_candle_url = self.get_config("season_candle_api.url")
            season_candle_key = self.get_config("season_candle_api.key")
            timeout = self.get_config("season_candle_api.timeout")
            
            if not season_candle_key or season_candle_key == "你的季蜡API密钥":
                await self.send_text("❌ 插件未配置季蜡API密钥")
                return False, "季蜡API密钥未配置", True
            
            await self.send_text("🔄 正在获取季蜡位置...")
            
            result = await self._get_season_candle_image(season_candle_url, season_candle_key, timeout)
            
            if result["success"]:
                image_base64 = result["image_data"]
                if image_base64:
                    if image_base64.startswith('data:'):
                        import re
                        match = re.search(r'base64,(.*)', image_base64)
                        if match:
                            image_base64 = match.group(1)
                    
                    success = await self.send_image(image_base64)
                    if success:
                        return True, "季蜡位置发送成功", True
                    else:
                        await self.send_text("❌ 发送图片失败")
                        return False, "发送图片失败", True
                else:
                    await self.send_text("❌ 图片数据为空")
                    return False, "图片数据为空", True
            else:
                await self.send_text(result["message"])
                return False, result.get("error", "获取季蜡位置失败"), True
                
        except Exception as e:
            await self.send_text(f"❌ 获取错误: {str(e)}")
            return False, f"获取季蜡位置错误: {str(e)}", True
    
    async def _get_season_candle_image(self, url: str, key: str, timeout: int) -> Dict[str, Any]:
        """调用每日季蜡位置API"""
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
                        "message": "获取季蜡位置成功"
                    }
                    
            except Exception as e:
                return {
                    "success": False,
                    "message": f"❌ 请求错误: {str(e)}",
                    "error": f"未知错误: {str(e)}",
                    "image_data": None
                }

class CalendarQueryCommand(BaseCommand):
    """光遇日历查询命令"""
    
    command_name = "calendar"
    command_description = "获取光遇日历图片"
    command_pattern = r"^/(?:calendar|rl|日历|活动日历)$"
    
    async def execute(self) -> Tuple[bool, Optional[str], bool]:
        """执行光遇日历查询命令"""
        try:
            calendar_url = self.get_config("calendar_api.url")
            calendar_key = self.get_config("calendar_api.key")
            timeout = self.get_config("calendar_api.timeout")
            
            if not calendar_key or calendar_key == "你的日历API密钥":
                await self.send_text("❌ 插件未配置日历API密钥")
                return False, "日历API密钥未配置", True
            
            await self.send_text("🔄 正在获取光遇日历...")
            
            result = await self._get_calendar_image(calendar_url, calendar_key, timeout)
            
            if result["success"]:
                image_base64 = result["image_data"]
                if image_base64:
                    if image_base64.startswith('data:'):
                        import re
                        match = re.search(r'base64,(.*)', image_base64)
                        if match:
                            image_base64 = match.group(1)
                    
                    success = await self.send_image(image_base64)
                    if success:
                        return True, "光遇日历发送成功", True
                    else:
                        await self.send_text("❌ 发送图片失败")
                        return False, "发送图片失败", True
                else:
                    await self.send_text("❌ 图片数据为空")
                    return False, "图片数据为空", True
            else:
                await self.send_text(result["message"])
                return False, result.get("error", "获取光遇日历失败"), True
                
        except Exception as e:
            await self.send_text(f"❌ 获取错误: {str(e)}")
            return False, f"获取光遇日历错误: {str(e)}", True
    
    async def _get_calendar_image(self, url: str, key: str, timeout: int) -> Dict[str, Any]:
        """调用光遇日历API"""
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
                        "message": "获取光遇日历成功"
                    }
                    
            except Exception as e:
                return {
                    "success": False,
                    "message": f"❌ 请求错误: {str(e)}",
                    "error": f"未知错误: {str(e)}",
                    "image_data": None
                }

class RedStoneQueryCommand(BaseCommand):
    """光遇红石位置查询命令"""
    
    command_name = "redstone"
    command_description = "获取光遇红石位置图片"
    command_pattern = r"^/(?:redstone|hs|红石|红石位置)$"
    
    async def execute(self) -> Tuple[bool, Optional[str], bool]:
        """执行红石位置查询命令"""
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
                    
                    success = await self.send_image(image_base64)
                    if success:
                        return True, "红石位置发送成功", True
                    else:
                        await self.send_text("❌ 发送图片失败")
                        return False, "发送图片失败", True
                else:
                    await self.send_text("❌ 图片数据为空")
                    return False, "图片数据为空", True
            else:
                await self.send_text(result["message"])
                return False, result.get("error", "获取红石位置失败"), True
                
        except Exception as e:
            await self.send_text(f"❌ 获取错误: {str(e)}")
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

@register_plugin
class SkyToolsPlugin(BasePlugin):
    """光遇工具插件"""
    
    plugin_name = "sky_tools_plugin"
    enable_plugin = True
    dependencies = []
    python_dependencies = ["aiohttp"]
    config_file_name = "config.toml"
    
    config_section_descriptions = {
        "height_api": "身高查询API配置",
        "task_api": "任务图片API配置",
        "candle_api": "大蜡烛位置API配置",
        "settings": "插件通用设置"
    }
    
    config_schema = {
        "height_api": {
            "url": ConfigField(
                type=str, 
                default="https://api.mangotool.cn/sky/out/cn", 
                description="身高查询API地址"
            ),
            "key": ConfigField(
                type=str, 
                default="你的身高API密钥", 
                description="身高查询API密钥，获取方式：芒果工具： https://mangotool.cn/openAPI",
                required=True
            ),
            "timeout": ConfigField(
                type=int, 
                default=15, 
                description="身高API请求超时时间（秒）"
            )
        },
        "task_api": {
            "url": ConfigField(
                type=str, 
                default="https://ovoav.com/api/sky/rwtp/rwt", 
                description="任务图片API地址，应天API：https://api.t1qq.com/api/sky/sc/scrw，独角兽API：https://ovoav.com/api/sky/rwtp/rwt"
            ),
            "key": ConfigField(
                type=str, 
                default="你的任务API密钥", 
                description="任务图片API密钥，获取方式：应天API：https://api.t1qq.com，独角兽API：https://ovoav.com",
                required=True
            ),
            "timeout": ConfigField(
                type=int, 
                default=15, 
                description="任务API请求超时时间（秒）"
            )
        },
        "candle_api": {
            "url": ConfigField(
                type=str, 
                default="https://ovoav.com/api/sky/dlzwz/dl", 
                description="大蜡烛位置API地址，应天API：https://api.t1qq.com/api/sky/sc/scdl，独角兽API：https://ovoav.com/api/sky/dlzwz/dl"
            ),
            "key": ConfigField(
                type=str, 
                default="你的大蜡烛API密钥", 
                description="大蜡烛位置API密钥，获取方式：应天API：https://api.t1qq.com，独角兽API：https://ovoav.com",
                required=True
            ),
            "timeout": ConfigField(
                type=int, 
                default=15, 
                description="大蜡烛API请求超时时间（秒）"
            )
        },
        "ancestor_api": {
            "url": ConfigField(
                type=str, 
                default="https://ovoav.com/api/sky/fkxz/xz", 
                description="复刻先祖位置API地址，应天API：暂无，独角兽API：https://ovoav.com/api/sky/fkxz/xz"
            ),
            "key": ConfigField(
                type=str, 
                default="你的复刻先祖API密钥", 
                description="复刻先祖位置API密钥，获取方式：应天API：https://api.t1qq.com，独角兽API：https://ovoav.com",
                required=True
            ),
            "timeout": ConfigField(
                type=int, 
                default=15, 
                description="复刻先祖API请求超时时间（秒）"
            )
        },
        "magic_api": {
            "url": ConfigField(
                type=str, 
                default="https://ovoav.com/api/sky/mftp/mf", 
                description="每日魔法API地址，应天API：https://api.t1qq.com/api/sky/mf/magic，独角兽API：https://ovoav.com/api/sky/mftp/mf"
            ),
            "key": ConfigField(
                type=str, 
                default="你的每日魔法API密钥", 
                description="每日魔法API密钥，获取方式：应天API：https://api.t1qq.com，独角兽API：https://ovoav.com",
                required=True
            ),
            "timeout": ConfigField(
                type=int, 
                default=15, 
                description="每日魔法API请求超时时间（秒）"
            )
        },
        "season_candle_api": {
            "url": ConfigField(
                type=str, 
                default="https://ovoav.com/api/sky/jlwz/jl", 
                description="每日季蜡位置API地址，应天API：https://api.t1qq.com/api/sky/sc/scjl，独角兽API：https://ovoav.com/api/sky/jlwz/jl"
            ),
            "key": ConfigField(
                type=str, 
                default="你的季蜡API密钥", 
                description="每日季蜡位置API密钥，获取方式：应天API：https://api.t1qq.com，独角兽API：https://ovoav.com",
                required=True
            ),
            "timeout": ConfigField(
                type=int, 
                default=15, 
                description="季蜡API请求超时时间（秒）"
            )
        },
        "calendar_api": {
            "url": ConfigField(
                type=str, 
                default="https://ovoav.com/api/sky/rltp/rl", 
                description="光遇日历API地址，应天API：暂无，独角兽API：https://ovoav.com/api/sky/rltp/rl"
            ),
            "key": ConfigField(
                type=str, 
                default="你的日历API密钥", 
                description="光遇日历API密钥，获取方式：应天API：https://api.t1qq.com，独角兽API：https://ovoav.com",
                required=True
            ),
            "timeout": ConfigField(
                type=int, 
                default=15, 
                description="日历API请求超时时间（秒）"
            )
        },
        "redstone_api": {
            "url": ConfigField(
                type=str, 
                default="https://ovoav.com/api/sky/hstp/hs", 
                description="红石位置API地址，应天API：暂无，独角兽API：https://ovoav.com/api/sky/hstp/hs"
            ),
            "key": ConfigField(
                type=str, 
                default="你的红石API密钥", 
                description="红石位置API密钥，获取方式：应天API：https://api.t1qq.com，独角兽API：https://ovoav.com",
                required=True
            ),
            "timeout": ConfigField(
                type=int, 
                default=15, 
                description="红石API请求超时时间（秒）"
            )
        },
        "settings": {
            "enable_help": ConfigField(
                type=bool, 
                default=True, 
                description="是否启用帮助命令"
            ),
            "debug_mode": ConfigField(
                type=bool, 
                default=False, 
                description="是否启用调试模式"
            )
        }
    }

    def get_plugin_components(self) -> List[Tuple[ComponentInfo, Type]]:
        """返回插件包含的组件列表"""
        return [
            (HelpCommand.get_command_info(), HelpCommand),
            (HeightQueryCommand.get_command_info(), HeightQueryCommand),
            (TaskQueryCommand.get_command_info(), TaskQueryCommand),
            (CandleQueryCommand.get_command_info(), CandleQueryCommand),
            (AncestorQueryCommand.get_command_info(), AncestorQueryCommand),
            (MagicQueryCommand.get_command_info(), MagicQueryCommand),
            (SeasonCandleQueryCommand.get_command_info(), SeasonCandleQueryCommand),
            (CalendarQueryCommand.get_command_info(), CalendarQueryCommand),
            (RedStoneQueryCommand.get_command_info(), RedStoneQueryCommand),
        ]
