from typing import List, Tuple, Type, Any, Optional, Dict
import aiohttp
import asyncio
import re
import base64
import time
import json
from src.plugin_system import (
    BasePlugin,
    register_plugin,
    BaseCommand,
    ComponentInfo,
    ConfigField,
    get_logger
)
from src.plugin_system.apis import plugin_manage_api
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading

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
        # 检查各个功能是否启用
        height_enabled = self.get_config("settings.enable_height_query", True)
        task_enabled = self.get_config("settings.enable_task_query", True)
        candle_enabled = self.get_config("settings.enable_candle_query", True)
        ancestor_enabled = self.get_config("settings.enable_ancestor_query", True)
        magic_enabled = self.get_config("settings.enable_magic_query", True)
        season_candle_enabled = self.get_config("settings.enable_season_candle_query", True)
        calendar_enabled = self.get_config("settings.enable_calendar_query", True)
        redstone_enabled = self.get_config("settings.enable_redstone_query", True)
        skytest_enabled = self.get_config("settings.enable_skytest_query", True)
        
        help_lines = ["✨ 光遇工具插件使用说明 ✨", "", "📋 可用命令:"]
        
        if height_enabled:
            help_lines.extend([
                "📏 /height <游戏长ID> [好友码]",
                "   → 查询光遇角色身高数据",
                ""
            ])
        
        if task_enabled:
            help_lines.extend([
                "🖼️ /task 或 /rw 或 /任务 或 /每日任务",
                "   → 获取每日任务图片",
                ""
            ])
        
        if candle_enabled:
            help_lines.extend([
                "🕯️ /candle 或 /dl 或 /大蜡 或 /大蜡烛",
                "   → 获取大蜡烛位置图片",
                ""
            ])
        
        if ancestor_enabled:
            help_lines.extend([
                "👴 /ancestor 或 /fk 或 /复刻 或 /复刻先祖",
                "   → 获取复刻先祖位置",
                ""
            ])
        
        if magic_enabled:
            help_lines.extend([
                "🔮 /magic 或 /mf 或 /魔法 或 /每日魔法",
                "   → 获取每日魔法图片",
                ""
            ])
        
        if season_candle_enabled:
            help_lines.extend([
                "🕯️ /scandel 或 /jl 或 /季蜡 或 /季节蜡烛 或 /季蜡位置",
                "   → 获取每日季蜡位置图片",
                ""
            ])
        
        if calendar_enabled:
            help_lines.extend([
                "📅 /calendar 或 /rl 或 /日历 或 /活动日历",
                "   → 获取光遇日历图片",
                ""
            ])
        
        if redstone_enabled:
            help_lines.extend([
                "🔴 /redstone 或 /hs 或 /红石 或 /红石位置",
                "   → 获取红石位置图片",
                ""
            ])
        
        if skytest_enabled:
            help_lines.extend([
                "🔍 /skytest",
                "   → 查看光遇服务器状态(是否炸服)",
                ""
            ])
        
        help_lines.extend([
            "ℹ️ /skytools",
            "   → 显示本帮助信息",
            "",
            "💡 提示: 部分功能可能已被管理员禁用"
        ])
        
        return "\n".join(help_lines)

class HeightQueryCommand(BaseCommand):
    """光遇身高查询命令"""
    
    command_name = "height"
    command_description = "查询光遇国服玩家身高数据"
    command_pattern = r"^/(?:height|身高)(?:\s+(?P<platform>\w+))?(?:\s+(?P<game_id>[^\s]+)(?:\s+(?P<friend_code>[^\s]+))?)?$"
    
    # 身高类型分类
    HEIGHT_TYPES = {
        "very_short": "非常矮",
        "short": "矮",
        "medium": "中等",
        "tall": "高",
        "very_tall": "非常高"
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.platform_manager = PlatformManager(self)
    
    async def execute(self) -> Tuple[bool, Optional[str], bool]:
        """执行身高查询命令"""
        try:
            # 获取匹配的参数
            platform = self.matched_groups.get("platform")
            game_id = self.matched_groups.get("game_id")
            friend_code = self.matched_groups.get("friend_code")
            
            # 处理帮助命令
            if not game_id or game_id.lower() == "help":
                help_text = self._get_help_text()
                await self.send_text(help_text)
                return True, "显示帮助信息", True
            
            # 检查是否有启用的平台
            enabled_platforms = self.platform_manager.get_enabled_platforms()
            if not enabled_platforms:
                await self.send_text("❌ 所有身高查询平台都未启用，请联系管理员启用")
                return False, "所有平台未启用", True
            
            # 解析平台
            query_platform = self.platform_manager.resolve_platform(platform)
            if not query_platform:
                await self.send_text("❌ 平台名称错误或该平台未启用")
                return False, "平台错误或禁用", True
            
            # 验证参数格式
            validation_result = self._validate_parameters(query_platform, game_id, friend_code)
            if not validation_result["success"]:
                await self.send_text(validation_result["message"])
                return False, validation_result["error"], True
            
            # 获取平台配置
            platform_config = self._get_platform_config(query_platform)
            if not platform_config:
                await self.send_text(f"❌ 插件未配置{query_platform}平台API密钥")
                return False, f"{query_platform}平台API密钥未配置", True
            
            # 调用平台处理器
            platform_handler = self._get_platform_handler(query_platform)
            result = await platform_handler.query(
                platform_config["url"],
                platform_config["key"],
                game_id,
                friend_code,
                platform_config["timeout"]
            )
            
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
    
    def _validate_parameters(self, platform: str, game_id: str, friend_code: Optional[str]) -> Dict[str, Any]:
        """验证参数格式"""
        # 芒果平台：必须提供游戏长ID，好友码可选
        if platform == "mango":
            if not game_id or not self._validate_game_id(game_id):
                return {
                    "success": False,
                    "message": "❌ 游戏ID格式错误",
                    "error": "游戏ID格式错误"
                }
            if friend_code and not self._validate_friend_code(friend_code):
                return {
                    "success": False,
                    "message": "❌ 好友码格式错误",
                    "error": "好友码格式错误"
                }
            return {"success": True}
        
        # 独角兽和应天平台：游戏长ID或好友码任选其一
        elif platform in ["ovoav", "yingtian"]:
            # 检查第一个参数（game_id）是否为有效的游戏长ID
            is_valid_game_id = self._validate_game_id(game_id)
            
            # 如果不是游戏长ID，检查是否为好友码
            if not is_valid_game_id:
                is_valid_friend_code = self._validate_friend_code(game_id)
                if is_valid_friend_code:
                    # 第一个参数是好友码，将参数重新分配
                    friend_code = game_id.upper()  # 转换为大写
                    game_id = None
                else:
                    # 既不是游戏长ID也不是好友码
                    return {
                        "success": False,
                        "message": "❌ 需要提供有效的游戏长ID或好友码",
                        "error": "缺少有效参数"
                    }
            
            # 如果提供了额外的friend_code参数，验证其格式并转换为大写
            if friend_code:
                if not self._validate_friend_code(friend_code):
                    return {
                        "success": False,
                        "message": "❌ 好友码格式错误",
                        "error": "好友码格式错误"
                    }
                friend_code = friend_code.upper()  # 转换为大写
            
            return {"success": True}
        
        return {"success": True}
    
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
        platforms_info = self.platform_manager.get_platforms_info()
        enabled_platforms = self.platform_manager.get_enabled_platforms()
        default_platform = self.get_config("height_api.default_platform", "获取失败")
        
        help_text = [
            "📏 身高查询使用说明",
            "",
            "使用方法（两种格式）:",
            "",
            f"1. 使用默认平台(当前默认:{default_platform}):",
            "   /height <游戏长ID> [好友码]",
            "",
            "2. 指定平台:",
            "   /height <平台名> <游戏长ID> [好友码]",
            "",
            "参数说明:",
            "• 平台名: 支持以下平台和别名",
        ]
        
        for platform_info in platforms_info.values():
            help_text.append(f"  • {platform_info}")
        
        help_text.extend([
            "• 游戏长ID: UUID格式的游戏ID",
            "• 好友码: 可选的好友码参数",
            "",
            "平台要求:",
        ])
        
        # 只显示启用的平台要求
        if "mango" in enabled_platforms:
            help_text.append("• 芒果平台: 必须提供游戏长ID，好友码可选(若提供好友码,长id也要一并提供)")
        if "ovoav" in enabled_platforms:
            help_text.append("• 独角兽平台: 提供游戏长ID或好友码任选其一")
        if "yingtian" in enabled_platforms:
            help_text.append("• 应天平台: 必须提供游戏长ID，好友码可选(若提供好友码,长id也要一并提供)")
        
        help_text.extend([
            "",
            "获取方式:",
            "• 长ID: 游戏右上角设置→精灵→询问'长id'",
            "• 好友码: 游戏右上角设置→好友→使用编号→设置昵称后获取",
            "",
            "示例:",
        ])
        
        # 只显示启用的平台示例
        if "mango" in enabled_platforms:
            help_text.extend([
                "芒果平台:",
                "/height mango xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "/height mg xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx XXXX-XXXX-XXXX",
                ""
            ])
        
        if "ovoav" in enabled_platforms:
            help_text.extend([
                "独角兽平台:",
                "/height ovoav xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "/height djs XXXX-XXXX-XXXX",
                ""
            ])
        
        if "yingtian" in enabled_platforms:
            help_text.extend([
                "应天平台:",
                "/height yingtian xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "/height yt xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx XXXX-XXXX-XXXX",
                ""
            ])
        
        help_text.extend([
            "注意:",
            "• 首次查询请提供好友码",
            "• 请勿拉黑测身高好友，否则后续无法查询"
        ])
        
        return "\n".join(help_text)
    
    def _get_platform_config(self, platform: str) -> Optional[Dict[str, Any]]:
        """获取平台配置"""
        if not self.platform_manager.is_platform_enabled(platform):
            return None
            
        url = self.get_config(f"height_api.{platform}_url")
        key = self.get_config(f"height_api.{platform}_key")
        timeout = self.get_config("height_api.timeout", 15)
        
        if not key or key.startswith("你的"):
            return None
        
        return {
            "url": url,
            "key": key,
            "timeout": timeout
        }
    
    def _get_platform_handler(self, platform: str):
        """获取平台处理器"""
        handlers = {
            "mango": MangoPlatformHandler(self.HEIGHT_TYPES),
            "ovoav": OvoavPlatformHandler(),
            "yingtian": YingtianPlatformHandler(self.HEIGHT_TYPES)
        }
        return handlers.get(platform)


class PlatformManager:
    """平台管理器"""
    
    def __init__(self, command_instance):
        self.command = command_instance
        self.platforms = self._parse_platform_choices()
    
    def _parse_platform_choices(self) -> Dict[str, List[str]]:
        """解析平台选择配置"""
        choices_config = self.command.get_config("height_api.platform_aliases", 
                                               ["mango:mg,芒果", "ovoav:独角兽,djs", "yingtian:应天,yt"])
        
        platforms = {}
        for choice in choices_config:
            if ":" in choice:
                main_name, aliases = choice.split(":", 1)
                aliases_list = [alias.strip() for alias in aliases.split(",")]
                platforms[main_name] = [main_name] + aliases_list
            else:
                platforms[choice] = [choice]
        
        return platforms
    
    def resolve_platform(self, platform_input: Optional[str]) -> Optional[str]:
        """解析平台输入"""
        if not platform_input:
            # 使用默认平台
            default_platform = self.command.get_config("height_api.default_platform", "mango")
            if self.is_platform_enabled(default_platform):
                return default_platform
            return self._get_first_enabled_platform()
        
        platform_input = platform_input.lower()
        
        for main_name, aliases in self.platforms.items():
            if platform_input in aliases and self.is_platform_enabled(main_name):
                return main_name
        
        return None
    
    def is_platform_enabled(self, platform: str) -> bool:
        """检查平台是否启用"""
        return self.command.get_config(f"height_api.enable_{platform}", True)
    
    def _get_first_enabled_platform(self) -> Optional[str]:
        """获取第一个启用的平台"""
        for platform in self.platforms.keys():
            if self.is_platform_enabled(platform):
                return platform
        return None
    
    def get_platforms_info(self) -> Dict[str, str]:
        """获取平台信息"""
        info = {}
        for main_name, aliases in self.platforms.items():
            aliases_str = ", ".join(aliases[1:]) if len(aliases) > 1 else "无别名"
            enabled = self.is_platform_enabled(main_name)
            status = "✅ 启用" if enabled else "❌ 禁用"
            info[main_name] = f"{main_name} (别名: {aliases_str}) - {status}"
        return info
    
    def get_enabled_platforms(self) -> List[str]:
        """获取所有启用的平台"""
        return [platform for platform in self.platforms.keys() if self.is_platform_enabled(platform)]

class BasePlatformHandler:
    """平台处理器基类"""
    
    async def query(self, url: str, key: str, game_id: str, friend_code: Optional[str], timeout: int) -> Dict[str, Any]:
        """查询身高数据"""
        raise NotImplementedError


class MangoPlatformHandler(BasePlatformHandler):
    """芒果平台处理器"""
    
    def __init__(self, height_types):
        self.height_types = height_types
    
    async def query(self, url: str, key: str, game_id: str, friend_code: Optional[str], timeout: int) -> Dict[str, Any]:
        """芒果平台查询"""
        params = {
            "key": key,
            "id": game_id.lower()
        }
        # 好友码是可选的，有就加上
        if friend_code:
            params["inviteCode"] = friend_code.upper()
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=params, timeout=timeout) as response:
                    return await self._handle_response(response)
            except Exception as e:
                return self._handle_error(e)
    
    async def _handle_response(self, response) -> Dict[str, Any]:
        """处理响应"""
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
            if "data" not in data or not data["data"]:
                error_msg = data.get("message", "未知错误")
                return {
                    "success": False,
                    "message": f"❌ API返回错误: {error_msg}",
                    "error": error_msg
                }
            
            formatted_result = self._format_data(data["data"])
            return {
                "success": True,
                "message": formatted_result
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"❌ 解析响应失败: {str(e)}",
                "error": f"解析错误: {str(e)}"
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
                "error": f"网络错误: {str(error)}"
            }
        elif isinstance(error, asyncio.TimeoutError):
            return {
                "success": False,
                "message": "❌ 请求超时",
                "error": "请求超时"
            }
        else:
            return {
                "success": False,
                "message": f"❌ 请求错误: {str(error)}",
                "error": f"未知错误: {str(error)}"
            }


class OvoavPlatformHandler(BasePlatformHandler):
    """独角兽平台处理器"""
    
    async def query(self, url: str, key: str, game_id: str, friend_code: Optional[str], timeout: int) -> Dict[str, Any]:
        """独角兽平台查询"""
        params = {"key": key}
        if game_id and not self._validate_game_id(game_id) and self._validate_friend_code(game_id):
            params["id"] = game_id.upper()
        elif game_id and self._validate_game_id(game_id):
            params["id"] = game_id.lower()
        elif friend_code and self._validate_friend_code(friend_code):
            params["id"] = friend_code.upper()
        else:
            return {
                "success": False,
                "message": "❌ 请提供有效的游戏长ID或好友码",
                "error": "缺少有效参数"
            }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params, timeout=timeout) as response:
                    return await self._handle_response(response)
            except Exception as e:
                return self._handle_error(e)
    
    async def _handle_response(self, response) -> Dict[str, Any]:
        """处理响应"""
        if response.status != 200:
            error_detail = await self._parse_error_response(response)
            return {
                "success": False,
                "message": f"❌ API请求失败: {error_detail}",
                "error": f"HTTP {response.status}: {error_detail}"
            }
        
        try:
            response_text = await response.text()
            cleaned_text = self._clean_html_response(response_text)
            return {
                "success": True,
                "message": cleaned_text
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"❌ 解析响应失败: {str(e)}",
                "error": f"解析错误: {str(e)}"
            }
    
    def _clean_html_response(self, html_text: str) -> str:
        """清理HTML响应"""
        cleaned = re.sub(r'<[^>]+>', '', html_text)
        cleaned = re.sub(r'[ ]+', ' ', cleaned)
        return cleaned.strip()
    
    @staticmethod
    def _validate_game_id(game_id: str) -> bool:
        """验证游戏ID格式"""
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        return re.match(uuid_pattern, game_id.lower()) is not None
    
    @staticmethod
    def _validate_friend_code(friend_code: str) -> bool:
        """验证好友码格式"""
        friend_code_pattern = r"^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$"
        return re.match(friend_code_pattern, friend_code.upper()) is not None
    
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
                "error": f"网络错误: {str(error)}"
            }
        elif isinstance(error, asyncio.TimeoutError):
            return {
                "success": False,
                "message": "❌ 请求超时",
                "error": "请求超时"
            }
        else:
            return {
                "success": False,
                "message": f"❌ 请求错误: {str(error)}",
                "error": f"未知错误: {str(error)}"
            }


class YingtianPlatformHandler(BasePlatformHandler):
    """应天平台处理器"""
    
    def __init__(self, height_types):
        self.height_types = height_types
    
    async def query(self, url: str, key: str, game_id: str, friend_code: Optional[str], timeout: int) -> Dict[str, Any]:
        """应天平台查询"""
        params = {"key": key}
        
        # 必须提供游戏长ID
        if not game_id or not self._validate_game_id(game_id):
            return {
                "success": False,
                "message": "❌ 请提供有效的游戏长ID",
                "error": "缺少游戏长ID"
            }
        
        # 设置cx参数（游戏长ID）
        params["cx"] = game_id.lower()
        
        # 好友码可选，如果提供了就加上
        if friend_code:
            if not self._validate_friend_code(friend_code):
                return {
                    "success": False,
                    "message": "❌ 好友码格式错误",
                    "error": "好友码格式错误"
                }
            params["code"] = friend_code.upper()
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params, timeout=timeout) as response:
                    return await self._handle_response(response)
            except Exception as e:
                return self._handle_error(e)
    
    async def _handle_response(self, response) -> Dict[str, Any]:
        """处理响应"""
        if response.status != 200:
            error_detail = await self._parse_error_response(response)
            return {
                "success": False,
                "message": f"❌ API请求失败: {error_detail}",
                "error": f"HTTP {response.status}: {error_detail}"
            }
        
        try:
            # 手动读取响应文本并解析JSON，避免Content-Type问题
            response_text = await response.text()
            data = json.loads(response_text)
            
            if data.get("code") != 200:
                error_msg = data.get("msg", "未知错误")
                return {
                    "success": False,
                    "message": f"❌ API返回错误: {error_msg}",
                    "error": error_msg
                }
            
            formatted_result = self._format_data(data)
            return {
                "success": True,
                "message": formatted_result
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "message": f"❌ 解析JSON失败: {str(e)}",
                "error": f"JSON解析错误: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"❌ 解析响应失败: {str(e)}",
                "error": f"解析错误: {str(e)}"
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
                "━━━━━━━━━━━━━━━━━━━━"
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
    
    @staticmethod
    def _validate_game_id(game_id: str) -> bool:
        """验证游戏ID格式"""
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        return re.match(uuid_pattern, game_id.lower()) is not None
    
    @staticmethod
    def _validate_friend_code(friend_code: str) -> bool:
        """验证好友码格式"""
        friend_code_pattern = r"^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$"
        return re.match(friend_code_pattern, friend_code.upper()) is not None
    
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
                "error": f"网络错误: {str(error)}"
            }
        elif isinstance(error, asyncio.TimeoutError):
            return {
                "success": False,
                "message": "❌ 请求超时",
                "error": "请求超时"
            }
        else:
            return {
                "success": False,
                "message": f"❌ 请求错误: {str(error)}",
                "error": f"未知错误: {str(error)}"
            }

class TaskQueryCommand(BaseCommand):
    """光遇任务图片查询命令"""

    command_name = "task"
    command_description = "获取光遇任务图片"
    command_pattern = r"^/(?:task|rw|任务|每日任务)$"
    
    async def execute(self) -> Tuple[bool, Optional[str], bool]:
        """执行任务图片查询命令"""

        # 检查功能是否启用
        if not self.get_config("settings.enable_task_query", True):
            await self.send_text("❌ 任务查询功能未启用")
            return False, "任务查询功能未启用", True
        
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

        # 检查功能是否启用
        if not self.get_config("settings.enable_magic_query", True):
            await self.send_text("❌ 每日魔法查询功能未启用")
            return False, "每日魔法查询功能未启用", True

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

        # 检查功能是否启用
        if not self.get_config("settings.enable_season_candle_query", True):
            await self.send_text("❌ 季蜡查询功能未启用")
            return False, "季蜡查询功能未启用", True

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
        
        # 检查功能是否启用
        if not self.get_config("settings.enable_calendar_query", True):
            await self.send_text("❌ 日历查询功能未启用")
            return False, "日历查询功能未启用", True

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
class SkyTestCommand(BaseCommand):
    """光遇服务器状态查询命令"""

    command_name = "skytest"
    command_description = "查询光遇服务器状态"
    command_pattern = r"^/skytest$"
    
    async def execute(self) -> Tuple[bool, Optional[str], bool]:
        """执行服务器状态查询命令"""
        
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
            
            # await self.send_text("🔄 正在查询服务器状态...")
            
            result = await self._get_server_status(skytest_url, skytest_key, timeout)
            
            if result["success"]:
                await self.send_text(result["message"])
                return True, "服务器状态查询成功", True
            else:
                await self.send_text(result["message"])
                return False, result.get("error", "服务器状态查询失败"), True
                
        except Exception as e:
            await self.send_text(f"❌ 查询错误: {str(e)}")
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
                    
                    # 检查返回数据格式
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

# class ConfigMonitor:
#     """安全的配置文件监控器 - 避免卡死主程序"""
    
#     def __init__(self, plugin):
#         self.plugin = plugin
#         self.is_running = False
#         self.task = None
#         self._reload_in_progress = False
#         self.config_path = self._get_config_path()
    
#     async def start(self):
#         """安全启动配置监控任务"""
#         if self.is_running:
#             return
        
#         self.is_running = True
#         # 使用create_task而不是直接await，避免阻塞
#         self.task = asyncio.create_task(self._safe_monitor_loop())
#         logger.info("安全配置监控已启动")
    
#     async def stop(self):
#         """安全停止配置监控任务"""
#         if not self.is_running:
#             return
        
#         self.is_running = False
#         if self.task and not self.task.done():
#             self.task.cancel()
#             try:
#                 # 设置超时，避免无限等待
#                 await asyncio.wait_for(self.task, timeout=5.0)
#             except (asyncio.CancelledError, asyncio.TimeoutError):
#                 logger.warning("配置监控任务停止超时，强制取消")
        
#         logger.info("配置监控已安全停止")
    
#     async def _safe_monitor_loop(self):
#         """安全的监控循环"""
#         check_interval = 10  # 10秒检查一次
        
#         logger.info(f"开始安全监控配置文件，检查间隔: {check_interval}秒")
        
#         last_successful_check = time.time()
        
#         while self.is_running:
#             try:
#                 # 使用可中断的sleep
#                 await asyncio.sleep(check_interval)
                
#                 # 检查是否过于频繁
#                 if time.time() - last_successful_check < check_interval:
#                     continue
                
#                 # 执行安全检查
#                 await self._safe_check_config()
#                 last_successful_check = time.time()
                
#             except asyncio.CancelledError:
#                 break
#             except Exception as e:
#                 logger.error(f"配置监控出错，等待恢复: {str(e)}")
#                 # 出错后延长等待时间
#                 await asyncio.sleep(60)
    
#     async def _safe_check_config(self):
#         """安全的配置检查"""
#         if self._reload_in_progress:
#             logger.debug("重载操作正在进行中，跳过检查")
#             return
        
#         if not os.path.exists(self.config_path):
#             return
        
#         try:
#             # 快速检查文件状态（非阻塞）
#             current_mtime = os.path.getmtime(self.config_path)
            
#             # 使用属性存储状态，避免复杂初始化
#             if not hasattr(self, '_last_mtime'):
#                 self._last_mtime = current_mtime
#                 return
            
#             # 只有当修改时间确实变化时才继续
#             if current_mtime <= self._last_mtime:
#                 return
            
#             # 标记重载进行中
#             self._reload_in_progress = True
            
#             # 延迟读取文件内容，避免频繁IO
#             await asyncio.sleep(1)  # 给文件系统时间完成写入
            
#             # 读取文件内容（在try中确保异常处理）
#             with open(self.config_path, 'r', encoding='utf-8') as f:
#                 current_content = f.read()
            
#             # 比较内容
#             if not hasattr(self, '_last_content') or current_content != self._last_content:
#                 logger.info("检测到配置变化，准备安全重载...")
                
#                 # 更新状态
#                 self._last_mtime = current_mtime
#                 self._last_content = current_content
                
#                 # 在重载前先停止当前监控
#                 await self.stop()
                
#                 # 安全重载插件（带超时）
#                 await self._safe_reload_plugin()
#             else:
#                 # 只更新时间戳
#                 self._last_mtime = current_mtime
                
#         except Exception as e:
#             logger.error(f"配置检查失败: {str(e)}")
#         finally:
#             # 确保标志被重置
#             self._reload_in_progress = False
    
#     async def _safe_reload_plugin(self):
#         """安全重载插件"""

#         try:
#             # 设置重载超时
#             logger.info("开始安全重载插件...")
            
#             # 使用wait_for设置超时
#             success = await asyncio.wait_for(
#                 plugin_manage_api.reload_plugin(self.plugin.plugin_name),
#                 timeout=30.0  # 30秒超时
#             )
            
#             if success:
#                 logger.info("插件安全重载成功")
#             else:
#                 logger.error("插件重载失败")
                
#         except asyncio.TimeoutError:
#             logger.error("插件重载超时，可能卡死，已取消操作")
#         except Exception as e:
#             logger.error(f"重载插件时出错: {str(e)}")
    
#     def _get_config_path(self):
#         """获取配置文件路径"""
#         plugin_dir = getattr(self.plugin, 'plugin_directory', os.path.dirname(os.path.abspath(__file__)))
#         return os.path.join(plugin_dir, "config.toml")

class AsyncWatchdogHandler(FileSystemEventHandler):
    """异步安全的 Watchdog 处理器"""
    
    def __init__(self, callback, loop):
        self.callback = callback
        self.loop = loop
        self._last_trigger_time = 0
        self._debounce_task = None
        
    def on_modified(self, event):
        """文件修改事件处理"""
        if not event.is_directory and event.src_path.endswith('config.toml'):
            self._handle_config_change()
    
    def on_closed(self, event):
        """文件关闭事件处理"""
        if not event.is_directory and event.src_path.endswith('config.toml'):
            self._handle_config_change()
    
    def _handle_config_change(self):
        """处理配置变化 - 线程安全版本"""
        current_time = time.time()
        
        # 防抖处理：3秒内只触发一次
        if current_time - self._last_trigger_time < 3:
            return
            
        self._last_trigger_time = current_time
        
        # 使用线程安全的方式调用异步函数
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()
        
        # 使用 run_coroutine_threadsafe 在正确的loop中运行
        self._debounce_task = asyncio.run_coroutine_threadsafe(
            self._debounced_reload(), 
            self.loop
        )
    
    async def _debounced_reload(self):
        """防抖重载"""
        logger.info("🔍 检测到配置文件变化，等待防抖延迟...")
        await asyncio.sleep(2.0)  # 2秒防抖延迟
        await self.callback()

class ConfigMonitor:
    """智能配置监控器 - 单例模式确保每个插件只有一个实例"""
    
    _instances = {}  # 类变量，存储每个插件的单例实例
    _lock = asyncio.Lock()  # 异步锁，防止并发问题
    
    def __new__(cls, plugin):
        """单例模式，确保每个插件只有一个监控实例"""
        plugin_name = plugin.plugin_name
        
        # 如果实例不存在，创建新实例
        if plugin_name not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[plugin_name] = instance
            instance._initialized = False
            logger.debug(f"🆕 创建新的 ConfigMonitor 实例: {plugin_name}")
        else:
            logger.debug(f"🔄 重用现有的 ConfigMonitor 实例: {plugin_name}")
            
        return cls._instances[plugin_name]
    
    def __init__(self, plugin):
        # 防止重复初始化
        if getattr(self, '_initialized', False):
            logger.debug(f"⏭️  跳过重复初始化: {plugin.plugin_name}")
            return
            
        self.plugin = plugin
        self.plugin_name = plugin.plugin_name  # 存储插件名称
        self.is_running = False
        self.observer = None
        self._reload_in_progress = False
        self.config_path = self._get_config_path()
        self.loop = asyncio.get_event_loop()
        self._initialized = True
        
        logger.info(f"🔧 ConfigMonitor 初始化完成: {self.plugin_name}")
        logger.info(f"📁 监控路径: {self.config_path}")
    
    async def start(self):
        """启动配置监控"""
        async with self._lock:  # 使用锁防止并发启动
            if self.is_running:
                logger.warning(f"⚠️ {self.plugin_name} 配置监控已经在运行")
                return
            
            self.is_running = True
            logger.info(f"🚀 开始启动 {self.plugin_name} 配置监控...")
            
            try:
                import watchdog
                logger.info(f"🔧 {self.plugin_name} - watchdog 可用，启动 Watchdog 监控")
                await self._start_watchdog_monitor()
            except ImportError:
                logger.warning(f"📋 {self.plugin_name} - watchdog 未安装，使用轮询模式")
                await self._start_polling_monitor()
            except Exception as e:
                logger.error(f"❌ {self.plugin_name} - 配置监控启动失败: {str(e)}，使用轮询模式")
                await self._start_polling_monitor()
    
    async def _start_watchdog_monitor(self):
        """启动 Watchdog 监控"""
        try:
            from watchdog.observers import Observer
            
            self.observer = Observer()
            handler = AsyncWatchdogHandler(self._safe_reload_plugin, self.loop)
            
            monitor_path = os.path.dirname(self.config_path)
            logger.info(f"📂 {self.plugin_name} - Watchdog 监控目录: {monitor_path}")
            
            self.observer.schedule(
                handler,
                path=monitor_path,
                recursive=False
            )
            self.observer.start()
            
            logger.info(f"✅ {self.plugin_name} - Watchdog 配置监控已启动")
            
        except Exception as e:
            logger.error(f"❌ {self.plugin_name} - Watchdog 监控启动失败: {str(e)}，回退到轮询模式")
            await self._start_polling_monitor()
    
    async def _start_polling_monitor(self):
        """启动轮询监控（备用）"""
        self.task = asyncio.create_task(self._polling_loop())
        logger.info(f"🔄 {self.plugin_name} - 轮询配置监控已启动")
    
    async def _polling_loop(self):
        """轮询监控循环"""
        check_interval = 30
        
        while self.is_running:
            try:
                await asyncio.sleep(check_interval)
                await self._safe_check_config()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ {self.plugin_name} - 轮询监控出错: {str(e)}")
                await asyncio.sleep(60)
    
    async def _safe_check_config(self):
        """安全的配置检查（用于轮询模式）"""
        if self._reload_in_progress or not os.path.exists(self.config_path):
            return
        
        try:
            current_mtime = os.path.getmtime(self.config_path)
            
            if not hasattr(self, '_last_mtime'):
                self._last_mtime = current_mtime
                return
            
            if current_mtime > self._last_mtime:
                logger.info(f"🔍 {self.plugin_name} - 检测到配置文件变化")
                self._last_mtime = current_mtime
                await self._safe_reload_plugin()
                
        except Exception as e:
            logger.error(f"❌ {self.plugin_name} - 配置检查失败: {str(e)}")
    
    async def _safe_reload_plugin(self):
        """安全重载插件"""
        if self._reload_in_progress:
            logger.warning(f"⏳ {self.plugin_name} - 重载操作正在进行中")
            return
            
        self._reload_in_progress = True
        
        try:
            logger.info(f"🔄 {self.plugin_name} - 开始安全重载插件...")
            
            # 延迟确保文件写入完成
            await asyncio.sleep(1)
            
            # 检查文件是否存在
            if not os.path.exists(self.config_path):
                logger.error(f"❌ {self.plugin_name} - 配置文件不存在")
                return
            
            # 执行重载（带超时）
            success = await asyncio.wait_for(
                plugin_manage_api.reload_plugin(self.plugin_name),
                timeout=30.0
            )
            
            if success:
                logger.info(f"✅ {self.plugin_name} - 插件热重载成功")
            else:
                logger.error(f"❌ {self.plugin_name} - 插件热重载失败")
                
        except asyncio.TimeoutError:
            logger.error(f"⏰ {self.plugin_name} - 插件重载超时")
        except Exception as e:
            logger.error(f"❌ {self.plugin_name} - 重载插件时出错: {str(e)}")
        finally:
            self._reload_in_progress = False
    
    async def stop(self):
        """停止配置监控"""
        async with self._lock:  # 使用锁防止并发停止
            if not self.is_running:
                logger.info(f"ℹ️ {self.plugin_name} - 配置监控未运行")
                return
            
            self.is_running = False
            logger.info(f"🛑 {self.plugin_name} - 开始停止配置监控...")
            
            # 停止 Watchdog 观察者
            if hasattr(self, 'observer') and self.observer:
                self.observer.stop()
                self.observer.join(timeout=5)
                self.observer = None
                logger.info(f"👁️ {self.plugin_name} - Watchdog 观察者已停止")
            
            # 停止轮询任务
            if hasattr(self, 'task') and self.task and not self.task.done():
                self.task.cancel()
                try:
                    await self.task
                except asyncio.CancelledError:
                    pass
                logger.info(f"🔄 {self.plugin_name} - 轮询任务已停止")
            
            logger.info(f"✅ {self.plugin_name} - 配置监控已完全停止")
    
    def _get_config_path(self):
        """获取配置文件路径"""
        plugin_dir = getattr(self.plugin, 'plugin_directory', os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(plugin_dir, "config.toml")
    
    @classmethod
    async def cleanup(cls, plugin_name):
        """清理指定插件的监控实例"""
        if plugin_name in cls._instances:
            instance = cls._instances[plugin_name]
            if instance.is_running:
                await instance.stop()
            del cls._instances[plugin_name]
            logger.info(f"🧹 已清理 {plugin_name} 的配置监控实例")
    
    # @classmethod
    # def get_instance_count(cls):
    #     """获取当前实例数量（用于调试）"""
    #     return len(cls._instances)
    
    # @classmethod
    # def get_running_instances(cls):
    #     """获取正在运行的实例列表（用于调试）"""
    #     return {name: instance for name, instance in cls._instances.items() if instance.is_running}
        
@register_plugin
class SkyToolsPlugin(BasePlugin):
    """光遇工具插件"""
    
    plugin_name = "sky_tools_plugin"
    enable_plugin = True
    dependencies = []
    python_dependencies = ["aiohttp", "watchdog"]
    config_file_name = "config.toml"
    
    config_section_descriptions = {
        "plugin": "插件基本配置",
        "height_api": "身高查询API配置",
        "task_api": "任务图片API配置",
        "candle_api": "大蜡烛位置API配置",
        "settings": "插件通用设置"
    }

    config_schema = {
        "plugin": {
            "enabled": ConfigField(type=bool, default=True, description="是否启用插件"),
            "config_version": ConfigField(type=str, default="1.1.4", description="配置文件版本"),
        },
        "height_api": {
            "default_platform": ConfigField(
                type=str, 
                default="mango", 
                description="默认身高查询平台",
                choices=["mango", "ovoav", "yingtian"]
            ),
            "platform_aliases": ConfigField(
                type=list,
                default=["mango:芒果,mg", "ovoav:独角兽,djs", "yingtian:应天,yt"],
                description="平台别名配置，格式：主平台名:别名1,别名2,..."
            ),
            "enable_mango": ConfigField(
                type=bool, 
                default=True, 
                description="是否启用芒果平台身高查询"
            ),
            "enable_ovoav": ConfigField(
                type=bool, 
                default=True, 
                description="是否启用独角兽平台身高查询"
            ),
            "enable_yingtian": ConfigField(
                type=bool, 
                default=True, 
                description="是否启用应天平台身高查询"
            ),
            "mango_url": ConfigField(
                type=str, 
                default="https://api.mangotool.cn/sky/out/cn", 
                description="芒果工具身高查询API地址"
            ),
            "mango_key": ConfigField(
                type=str, 
                default="你的芒果工具API密钥", 
                description="芒果工具身高查询API密钥，获取方式：芒果工具：https://mangotool.cn/openAPI",
                required=True
            ),
            "ovoav_url": ConfigField(
                type=str, 
                default="https://ovoav.com/api/sky/sgwz/sgv1", 
                description="独角兽平台身高查询API地址"
            ),
            "ovoav_key": ConfigField(
                type=str, 
                default="你的独角兽平台API密钥", 
                description="独角兽平台身高查询API密钥，获取方式：独角兽API：https://ovoav.com",
                required=True
            ),
            "yingtian_url": ConfigField(
                type=str, 
                default="https://api.t1qq.com/api/sky/sc/sg", 
                description="应天平台身高查询API地址"
            ),
            "yingtian_key": ConfigField(
                type=str, 
                default="你的应天平台API密钥", 
                description="应天平台身高查询API密钥，获取方式：应天API：https://api.t1qq.com",
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
        "skytest_api": {
            "url": ConfigField(
                type=str, 
                default="https://ovoav.com/api/sky/gyzt/zt", 
                description="服务器状态测试API地址"
            ),
            "key": ConfigField(
                type=str, 
                default="你的服务器状态API密钥", 
                description="服务器状态测试API密钥，获取方式：独角兽API：https://ovoav.com",
                required=True
            ),
            "timeout": ConfigField(
                type=int, 
                default=15, 
                description="服务器状态API请求超时时间（秒）"
            )
        },
        "settings": {
            "enable_height_query": ConfigField(
                type=bool, 
                default=True, 
                description="是否启用身高查询功能"
            ),
            "enable_task_query": ConfigField(
                type=bool, 
                default=True, 
                description="是否启用任务查询功能"
            ),
            "enable_candle_query": ConfigField(
                type=bool, 
                default=True, 
                description="是否启用大蜡烛查询功能"
            ),
            "enable_ancestor_query": ConfigField(
                type=bool, 
                default=True, 
                description="是否启用复刻先祖查询功能"
            ),
            "enable_magic_query": ConfigField(
                type=bool, 
                default=True, 
                description="是否启用每日魔法查询功能"
            ),
            "enable_season_candle_query": ConfigField(
                type=bool, 
                default=True, 
                description="是否启用季蜡查询功能"
            ),
            "enable_calendar_query": ConfigField(
                type=bool, 
                default=True, 
                description="是否启用日历查询功能"
            ),
            "enable_redstone_query": ConfigField(
                type=bool, 
                default=True, 
                description="是否启用红石查询功能"
            ),
            "enable_skytest_query": ConfigField(
                type=bool, 
                default=True, 
                description="是否启用服务器状态查询功能"
            )
        }
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._monitor_start_task = None  # 跟踪启动任务
        
        # 如果启用插件，初始化配置监控
        if self.get_config("plugin.enabled", True):
            self.enable_plugin = True
            
            # 使用单例模式获取 ConfigMonitor
            self.config_monitor = ConfigMonitor(self)
            logger.info(f"✅ {self.plugin_name} - 配置监控器初始化完成")
            
            # 延迟启动监控（确保只启动一次）
            if not self._monitor_start_task or self._monitor_start_task.done():
                self._monitor_start_task = asyncio.create_task(self._start_config_monitor_after_delay())
        else:
            logger.warning(f"❌ {self.plugin_name} - 插件未启用，跳过配置监控")
    
    async def _start_config_monitor_after_delay(self):
        """延迟启动配置监控任务"""
        logger.info(f"⏰ {self.plugin_name} - 等待10秒后启动配置监控...")
        await asyncio.sleep(10)
        
        if self.config_monitor:
            if not self.config_monitor.is_running:
                await self.config_monitor.start()
            else:
                logger.info(f"ℹ️ {self.plugin_name} - 配置监控器已在运行")
        else:
            logger.error(f"❌ {self.plugin_name} - 配置监控器未初始化")
    
    async def on_unload(self):
        """插件卸载时调用"""
        logger.info(f"🧹 {self.plugin_name} - 开始卸载插件...")
        
        # 取消启动任务
        if self._monitor_start_task and not self._monitor_start_task.done():
            self._monitor_start_task.cancel()
            try:
                await self._monitor_start_task
            except asyncio.CancelledError:
                pass
        
        # 清理配置监控
        if self.config_monitor:
            await ConfigMonitor.cleanup(self.plugin_name)
        
        await super().on_unload()
        logger.info(f"✅ {self.plugin_name} - 插件卸载完成")
           
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
            (SkyTestCommand.get_command_info(), SkyTestCommand),
        ]
