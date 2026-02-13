"""
光遇身高查询命令
支持芒果、独角兽、应天等多个平台
"""
import re
import asyncio
from typing import Tuple, Optional, Dict, Any

from .base import SkyBaseCommand
from ..message_forward_helper import MessageForwardHelper
from ..platforms.registry import registry as platform_registry
from ..utils.validators import validate_game_id, validate_friend_code

# 尝试导入 logger（若失败则使用 print 回退）
try:
    from src.plugin_system.apis import get_logger
    logger = get_logger("sky_tools_plugin.HeightQueryCommand")
except ImportError:
    import logging
    logger = logging.getLogger("sky_tools_plugin.HeightQueryCommand")


class HeightQueryCommand(SkyBaseCommand):
    """光遇身高查询命令"""

    command_name = "height"
    command_description = "查询光遇国服玩家身高数据"
    command_pattern = (
        r"^{escaped_prefix}(?:height|身高)(?:\s+(?P<platform>\w+))?"
        r"(?:\s+(?P<game_id>[^\s]+)(?:\s+(?P<friend_code>[^\s]+))?)?$"
    )

    async def execute(self) -> Tuple[bool, Optional[str], bool]:
        """执行身高查询命令"""
        try:
            platform_input = self.matched_groups.get("platform")
            game_id = self.matched_groups.get("game_id")
            friend_code = self.matched_groups.get("friend_code")

            # 显示帮助
            if not game_id or game_id.lower() == "help":
                help_text = await self._get_help_text()
                await self._safe_send_text(help_text)
                return True, "显示帮助信息", True

            # 1. 获取所有启用的平台
            enabled_platforms = self._get_enabled_platforms()
            if not enabled_platforms:
                await self._safe_send_text("❌ 所有身高查询平台都未启用，请联系管理员启用")
                return False, "所有平台未启用", True

            # 2. 解析用户指定的平台（或使用默认）
            target_platform = self._resolve_platform(platform_input, enabled_platforms)
            if not target_platform:
                await self._safe_send_text("❌ 平台名称错误或该平台未启用")
                return False, "平台错误或禁用", True

            # 3. 验证参数（根据平台规则）
            validation = self._validate_parameters(target_platform, game_id, friend_code)
            if not validation["success"]:
                await self._safe_send_text(validation["message"])
                return False, validation["error"], True

            # 4. 获取平台配置
            config = self._get_platform_config(target_platform)
            if not config:
                await self._safe_send_text(f"❌ 插件未配置 {target_platform} 平台 API 密钥")
                return False, f"{target_platform} API 密钥未配置", True

            # 5. 获取处理器并查询
            handler_class = platform_registry.get_handler(target_platform)
            if not handler_class:
                await self._safe_send_text(f"❌ 平台 {target_platform} 处理器未注册")
                return False, "平台处理器缺失", True

            handler = handler_class()
            result = await handler.query(
                config["url"],
                config["key"],
                validation.get("game_id", game_id),
                validation.get("friend_code", friend_code),
                config["timeout"],
            )

            if result["success"]:
                # ---------- 核心修复：无条件确保消息发送 ----------
                message = result["message"]
                await self._force_send_message(message, target_platform)
                return True, "身高查询成功", True
            else:
                # ---------- 智能错误提示 ----------
                error_msg = result.get("message", "")
                error_detail = result.get("error", "").lower()

                if any(kw in error_detail for kw in ["record not found", "未找到", "no record", "不存在"]):
                    suggestion = self._build_record_not_found_suggestion(target_platform)
                    await self._force_send_message(suggestion, target_platform)
                    return False, "平台无记录，需提供好友码", True

                # 其他错误原样发送
                await self._force_send_message(error_msg, target_platform)
                return False, result.get("error", "身高查询失败"), True

        except asyncio.TimeoutError:
            await self._safe_send_text("❌ 查询超时")
            return False, "API请求超时", True
        except Exception as e:
            error_text = f"❌ 查询错误: {str(e)}"
            await self._safe_send_text(error_text)
            logger.exception("身高查询未捕获异常")
            return False, f"查询错误: {str(e)}", True

    # ---------- 消息发送核心方法（兜底保障） ----------
    async def _force_send_message(self, content: str, platform_hint: str = ""):
        """强制发送消息，优先合并转发，失败则直接发送文本，并记录错误"""
        # 方法1：尝试合并转发
        try:
            sent = await MessageForwardHelper.send_forward_message(self, [content])
            if sent:
                logger.info(f"✅ [{platform_hint}] 合并转发发送成功")
                return
            else:
                logger.warning(f"⚠️ [{platform_hint}] 合并转发返回 False，将使用直接发送")
        except Exception as e:
            logger.error(f"❌ [{platform_hint}] 合并转发异常: {e}，将使用直接发送")

        # 方法2：直接发送文本
        try:
            await self.send_text(content)
            logger.info(f"✅ [{platform_hint}] 直接发送文本成功")
        except Exception as e:
            logger.error(f"❌ [{platform_hint}] 直接发送文本也失败: {e}")
            # 终极兜底：尝试使用基类的 send_custom
            try:
                await self.send_custom("text", content)
                logger.info(f"✅ [{platform_hint}] send_custom 发送成功")
            except Exception as e2:
                logger.critical(f"💥 [{platform_hint}] 所有发送方式均失败: {e2}")

    async def _safe_send_text(self, content: str):
        """安全的纯文本发送（仅直接发送，不尝试合并转发）"""
        try:
            await self.send_text(content)
        except Exception as e:
            logger.error(f"发送文本失败: {e}")
            try:
                await self.send_custom("text", content)
            except:
                pass

    # ---------- 以下为辅助方法（与之前相同，略作优化）----------
    def _get_enabled_platforms(self) -> list:
        all_platforms = platform_registry.get_all_platforms()
        enabled = []
        for plat in all_platforms:
            if self.get_config(f"height_api.enable_{plat}", True):
                enabled.append(plat)
        return enabled

    def _resolve_platform(self, user_input: Optional[str], enabled_platforms: list) -> Optional[str]:
        if not user_input:
            default = self.get_config("height_api.default_platform", "mango")
            return default if default in enabled_platforms else (enabled_platforms[0] if enabled_platforms else None)
        handler_class = platform_registry.get_handler(user_input.lower())
        if handler_class:
            for main_name in platform_registry.get_all_platforms():
                if platform_registry.get_handler(main_name) == handler_class:
                    return main_name if main_name in enabled_platforms else None
        return None

    def _validate_parameters(self, platform: str, game_id: str, friend_code: Optional[str]) -> Dict[str, Any]:
        result = {"success": True, "game_id": game_id, "friend_code": friend_code}
        if platform == "mango":
            if not game_id or not validate_game_id(game_id):
                return {
                    "success": False,
                    "message": "❌ 游戏长ID格式错误。正确格式应为：xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                    "error": "游戏ID格式错误"
                }
            if friend_code and not validate_friend_code(friend_code):
                return {
                    "success": False,
                    "message": "❌ 好友码格式错误。正确格式应为：XXXX-XXXX-XXXX",
                    "error": "好友码格式错误"
                }
            return result
        elif platform in ["ovoav", "yingtian"]:
            if game_id and validate_game_id(game_id):
                result["game_id"] = game_id.lower()
            elif game_id and validate_friend_code(game_id):
                result["friend_code"] = game_id.upper()
                result["game_id"] = None
            else:
                return {
                    "success": False,
                    "message": "❌ 需要提供有效的游戏长ID或好友码（格式 XXXX-XXXX-XXXX）",
                    "error": "缺少有效参数"
                }
            if friend_code and not validate_friend_code(friend_code):
                return {
                    "success": False,
                    "message": "❌ 好友码格式错误。正确格式应为：XXXX-XXXX-XXXX",
                    "error": "好友码格式错误"
                }
            if friend_code:
                result["friend_code"] = friend_code.upper()
            return result
        return result

    def _get_platform_config(self, platform: str) -> Optional[Dict[str, Any]]:
        url = self.get_config(f"height_api.{platform}_url")
        key = self.get_config(f"height_api.{platform}_key")
        if not key or key.startswith("你的"):
            return None
        return {
            "url": url,
            "key": key,
            "timeout": self.get_config("height_api.timeout", 15),
        }

    def _build_record_not_found_suggestion(self, platform: str) -> str:
        prefix = self.get_config("plugin.command_prefix", "#")
        lines = [
            f"❌ 在 **{platform}** 平台未找到该玩家的身高记录。",
            "",
            "📌 **首次查询请务必提供好友码**",
            f"   格式：`{prefix}height <游戏ID> <好友码>`",
            "",
            "🔗 **好友码获取方法**",
            "   游戏设置 → 好友 → 使用编号 → 设置昵称后获取",
            "   格式示例：`1234-5678-9012`",
            "",
            "💡 **为什么需要好友码？**",
            "   好友码用于将游戏ID与你的查询绑定，",
            "   首次提供后，后续可直接使用游戏ID查询。",
            "",
            "⚠️ **注意**：请勿拉黑测身高好友，否则后续无法查询。"
        ]
        return "\n".join(lines)

    async def _get_help_text(self) -> str:
        enabled_platforms = self._get_enabled_platforms()
        platforms_info = platform_registry.get_platform_info()
        lines = [
            "📏 身高查询使用说明",
            "",
            "使用方法（两种格式）:",
            f"  1. 使用默认平台(当前默认:{self.get_config('height_api.default_platform', 'mango')}):",
            "     #height <游戏长ID> [好友码]",
            "  2. 指定平台:",
            "     #height <平台名> <游戏长ID> [好友码]",
            "",
            "参数说明:",
            "• 平台名: 支持以下平台和别名",
        ]
        for main_name in enabled_platforms:
            aliases = platforms_info.get(main_name, [])
            alias_str = ", ".join(aliases) if aliases else "无"
            lines.append(f"  • {main_name} (别名: {alias_str}) - ✅ 启用")
        lines.extend([
            "• 游戏长ID: UUID格式的游戏ID",
            "• 好友码: 可选的好友码参数",
            "",
            "平台要求:",
        ])
        if "mango" in enabled_platforms:
            lines.append("• 芒果平台: 必须提供游戏长ID，好友码可选")
        if "ovoav" in enabled_platforms:
            lines.append("• 独角兽平台: 提供游戏长ID或好友码任选其一")
        if "yingtian" in enabled_platforms:
            lines.append("• 应天平台: 必须提供游戏长ID，好友码可选")
        lines.extend([
            "",
            "获取方式:",
            "• 长ID: 游戏右上角设置→精灵→询问'长id'",
            "• 好友码: 游戏右上角设置→好友→使用编号→设置昵称后获取",
            "",
            "示例:",
        ])
        if "mango" in enabled_platforms:
            lines.extend([
                "芒果平台:",
                "#height mango xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "#height mg xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx XXXX-XXXX-XXXX",
                "",
            ])
        if "ovoav" in enabled_platforms:
            lines.extend([
                "独角兽平台:",
                "#height ovoav xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "#height djs XXXX-XXXX-XXXX",
                "",
            ])
        if "yingtian" in enabled_platforms:
            lines.extend([
                "应天平台:",
                "#height yingtian xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "#height yt xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx XXXX-XXXX-XXXX",
                "",
            ])
        lines.extend([
            "注意:",
            "• 首次查询请提供好友码",
            "• 请勿拉黑测身高好友，否则后续无法查询",
        ])
        return "\n".join(lines)