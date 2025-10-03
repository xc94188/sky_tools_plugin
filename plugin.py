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

🖼️ /task 或 /任务 或 /每日任务
   → 获取每日任务图片

🕯️ /大蜡 或 /蜡烛 或 /大蜡烛
   → 获取大蜡烛位置图片

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
    command_pattern = r"^/(?:task|任务|每日任务)$"
    
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
    command_pattern = r"^/(?:大蜡|蜡烛|大蜡烛)$"
    
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
                default="https://api.t1qq.com/api/sky/sc/scrw", 
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
                default="https://api.t1qq.com/api/sky/sc/scdl", 
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
        ]
