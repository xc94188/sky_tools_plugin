"""
合并转发消息助手模块
提供统一的合并转发消息发送功能，支持多种消息格式和分条/混合发送
"""
import json
import requests
import re
from typing import List, Dict, Union, Optional
import logging

# 设置日志
logger = logging.getLogger('sky_tools_plugin.MessageForwardHelper')


class MessageForwardHelper:
    """合并转发消息助手类"""
    
    @staticmethod
    async def send_forward_message(
        command_instance, 
        messages_list: List, 
        prompt: str = "群聊的聊天记录",
        summary: str = None,
        source: str = None
    ) -> bool:
        """发送合并转发消息（同原代码，无改动）"""
        try:
            from src.plugin_system.apis import config_api
            
            napcat_enabled = command_instance.get_config("napcat.enabled", True)
            if not napcat_enabled:
                logger.info("合并转发功能已禁用，使用直接发送")
                return await MessageForwardHelper._fallback_send_new(command_instance, messages_list)
            
            api_url = command_instance.get_config("napcat.api_url", "http://127.0.0.1:5222")
            api_token = command_instance.get_config("napcat.token", "")
            timeout = command_instance.get_config("napcat.timeout", 30)
            
            logger.info(f"Napcat配置: 地址={api_url}, 启用={napcat_enabled}, 超时={timeout}秒")
            
            bot_qq = None
            bot_nickname = None
            try:
                bot_qq = str(config_api.get_global_config("bot.qq_account", ""))
                bot_nickname = str(config_api.get_global_config("bot.nickname", "麦麦"))
                logger.info(f"获取到bot配置: QQ={bot_qq}, nickname={bot_nickname}")
            except Exception as e:
                logger.error(f"获取bot配置失败: {str(e)}")
            
            is_valid_qq = bot_qq and bot_qq != "1145141919810" and bot_qq.isdigit()
            
            if not is_valid_qq:
                logger.warning(f"❌ 无法获取有效bot QQ号(当前值: {bot_qq})，回退到直接消息发送")
                return await MessageForwardHelper._fallback_send_new(command_instance, messages_list)
            
            if not bot_nickname:
                bot_nickname = "麦麦"
                logger.warning("使用默认昵称: 麦麦")
            
            if not hasattr(command_instance, 'message'):
                logger.error("❌ command_instance没有message属性，无法确定发送目标")
                return await MessageForwardHelper._fallback_send_new(command_instance, messages_list)
            
            message_obj = command_instance.message
            
            messages = MessageForwardHelper._parse_messages_list(messages_list, bot_qq, bot_nickname)
            
            if not messages:
                logger.warning("没有消息需要发送")
                return False
            
            total_messages = len(messages)
            
            if summary is None:
                summary = f"查看{total_messages}条转发消息"
            
            if source is None:
                source = "群聊的聊天记录"
            
            forward_data = {
                "messages": messages,
                "news": MessageForwardHelper._generate_news(messages, bot_nickname),
                "prompt": prompt,
                "summary": summary,
                "source": source
            }
            
            target_info = MessageForwardHelper._get_target_info(message_obj)
            if not target_info:
                logger.error("❌ 无法确定发送目标")
                return await MessageForwardHelper._fallback_send_new(command_instance, messages_list)
            
            forward_data.update(target_info)
            if source == "群聊的聊天记录" and "group_name" in target_info:
                forward_data["source"] = f"{target_info['group_name']}的聊天记录"
            elif source == "群聊的聊天记录" and "user_name" in target_info:
                forward_data["source"] = f"{target_info['user_name']}的聊天记录"
            
            target = forward_data.get('group_id', forward_data.get('user_id'))
            chat_type = "群聊" if "group_id" in forward_data else "私聊"
            
            logger.info(f"🎯 发送合并转发消息:")
            logger.info(f"  目标: {target} ({chat_type})")
            logger.info(f"  source: {forward_data['source']}")
            logger.info(f"  prompt: {forward_data['prompt']}")
            logger.info(f"  summary: {forward_data['summary']}")
            logger.info(f"  news: {forward_data['news']}")
            logger.info(f"  消息节点数: {total_messages}")
            logger.debug(f"  messages结构: {json.dumps(messages[:1], indent=2, ensure_ascii=False)}")
            
            result = MessageForwardHelper._send_api_request(
                api_url, api_token, timeout, forward_data
            )
            
            if result:
                logger.info(f"✅ 合并转发消息发送成功")
                return True
            else:
                logger.warning("合并转发失败，回退到直接消息发送")
                return await MessageForwardHelper._fallback_send_new(command_instance, messages_list)
            
        except Exception as e:
            logger.error(f"❌ 发送合并转发消息失败: {str(e)}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return await MessageForwardHelper._fallback_send_new(command_instance, messages_list)
    
    @staticmethod
    def _parse_messages_list(messages_list, bot_qq: str, bot_nickname: str) -> List[Dict]:
        """解析消息列表，构建一级合并转发消息列表（同原代码）"""
        messages = []
        if not isinstance(messages_list, list):
            messages_list = [messages_list]
        
        for item in messages_list:
            if isinstance(item, list):
                content = []
                for subitem in item:
                    content_items = MessageForwardHelper._parse_single_item(subitem, for_merge=True)
                    content.extend(content_items)
                if content:
                    message = {
                        "type": "node",
                        "data": {
                            "user_id": int(bot_qq),
                            "nickname": bot_nickname,
                            "content": content
                        }
                    }
                    messages.append(message)
            else:
                content = MessageForwardHelper._parse_single_item(item, for_merge=True)
                if content:
                    message = {
                        "type": "node",
                        "data": {
                            "user_id": int(bot_qq),
                            "nickname": bot_nickname,
                            "content": content
                        }
                    }
                    messages.append(message)
        return messages
    
    @staticmethod
    def _parse_single_item(item, for_merge: bool = False) -> List[Dict]:
        """
        解析单个消息项，返回content列表
        for_merge: True 表示用于合并转发（图片需带data前缀），False 表示用于直接发送
        """
        content = []
        if isinstance(item, str):
            if MessageForwardHelper._is_image_data(item):
                if for_merge:
                    img_content = MessageForwardHelper._create_image_content(item)
                else:
                    # 直接发送时不构造content，由调用者处理
                    return []
                if img_content:
                    content.append(img_content)
            else:
                if item.strip():
                    if for_merge:
                        text_content = MessageForwardHelper._create_text_content(item)
                        if text_content:
                            content.append(text_content)
        elif isinstance(item, dict):
            if 'type' in item and 'data' in item:
                content.append(item)
            else:
                if 'text' in item and item['text']:
                    if for_merge:
                        text_content = MessageForwardHelper._create_text_content(item['text'])
                        if text_content:
                            content.append(text_content)
                if 'image' in item and item['image']:
                    if for_merge:
                        img_content = MessageForwardHelper._create_image_content(item['image'])
                        if img_content:
                            content.append(img_content)
        return content
    
    @staticmethod
    def _generate_news(messages: List[Dict], bot_nickname: str, max_preview: int = 4) -> List[Dict]:
        """生成news外显列表（同原代码）"""
        news_items = []
        for i, message in enumerate(messages[:max_preview]):
            content = message["data"]["content"]
            preview_parts = []
            for item in content:
                if isinstance(item, dict):
                    item_type = item.get("type")
                    if item_type == "text":
                        text = item.get("data", {}).get("text", "")
                        if text:
                            simplified_text = text.replace('\n', ' ').replace('\r', '').strip()
                            if simplified_text:
                                preview_parts.append(simplified_text)
                    elif item_type == "image":
                        preview_parts.append(" [图片]")
                    else:
                        preview_parts.append(f"[{item_type}]")
            if preview_parts:
                node_preview = "".join(preview_parts)
                if len(node_preview) > 50:
                    node_preview = node_preview[:47] + "..."
                news_items.append({"text": f"{bot_nickname}: {node_preview}"})
            else:
                news_items.append({"text": f"{bot_nickname}: 消息{i+1}"})
        if not news_items:
            news_items.append({"text": f"{bot_nickname}: [聊天记录]"})
        return news_items
    
    @staticmethod
    def _get_target_info(message_obj) -> Optional[Dict]:
        """获取发送目标信息（同原代码）"""
        try:
            from src.plugin_system.apis import chat_api
            chat_stream = message_obj.chat_stream
            stream_info = chat_api.get_stream_info(chat_stream)
            target_info = {}
            if stream_info.get("type") == "group":
                target_info["group_id"] = stream_info.get("group_id")
                target_info["group_name"] = stream_info.get("group_name", "群聊")
                logger.info(f"✅ 确定是群聊，group_id: {target_info['group_id']}")
            elif stream_info.get("type") == "private":
                user_id = stream_info.get("user_id")
                if user_id:
                    target_info["user_id"] = user_id
                    target_info["user_name"] = stream_info.get("user_name", "用户")
                    logger.info(f"✅ 确定是私聊，user_id: {user_id}")
            return target_info if target_info else None
        except Exception as e:
            logger.error(f"使用chat_api失败: {str(e)}")
            return MessageForwardHelper._get_target_info_fallback(message_obj)
    
    @staticmethod
    def _get_target_info_fallback(message_obj) -> Optional[Dict]:
        """回退方式获取发送目标信息（同原代码）"""
        if not hasattr(message_obj, 'message_info'):
            return None
        message_info = message_obj.message_info
        target_info = {}
        if hasattr(message_info, 'group_info') and message_info.group_info is not None:
            if hasattr(message_info.group_info, 'group_id'):
                target_info["group_id"] = message_info.group_info.group_id
                group_name = "群聊"
                if hasattr(message_info.group_info, 'group_name') and message_info.group_info.group_name:
                    group_name = message_info.group_info.group_name
                target_info["group_name"] = group_name
                logger.info(f"✅ 从group_info获取群聊ID: {target_info['group_id']}")
        else:
            if hasattr(message_info, 'user_info') and hasattr(message_info.user_info, 'user_id'):
                target_info["user_id"] = message_info.user_info.user_id
                user_name = "用户"
                if hasattr(message_info.user_info, 'user_nickname') and message_info.user_info.user_nickname:
                    user_name = message_info.user_info.user_nickname
                elif hasattr(message_info.user_info, 'user_cardname') and message_info.user_info.user_cardname:
                    user_name = message_info.user_info.user_cardname
                target_info["user_name"] = user_name
                logger.info(f"✅ 从user_info获取私聊用户ID: {target_info['user_id']}")
        return target_info if target_info else None
    
    @staticmethod
    def _send_api_request(api_url: str, api_token: str, timeout: int, forward_data: Dict) -> bool:
        """发送API请求（同原代码）"""
        try:
            headers = {"Content-Type": "application/json"}
            if api_token:
                headers["Authorization"] = f"Bearer {api_token}"
                logger.info("使用API令牌进行认证")
            full_api_url = f"{api_url.rstrip('/')}/send_forward_msg"
            logger.info(f"发送请求到: {full_api_url}")
            response = requests.post(
                full_api_url,
                json=forward_data,
                headers=headers,
                timeout=timeout
            )
            if response.status_code == 200:
                result = response.json()
                logger.debug(f"API响应: {json.dumps(result, ensure_ascii=False)}")
                return result.get("status") == "ok"
            else:
                logger.error(f"❌ HTTP请求失败: {response.status_code}")
                logger.error(f"响应内容: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 网络请求异常: {str(e)}")
            return False
    
    @staticmethod
    def _is_image_data(text: str) -> bool:
        """判断是否为图片数据（同原代码）"""
        if not isinstance(text, str):
            return False
        if text.startswith('data:image/'):
            return True
        if text.startswith('base64,') or (len(text) > 100 and 'base64' in text):
            return True
        base64_prefixes = ['/9j/', 'iVBORw', 'R0lGOD', 'UE5HDQ', 'PHN2Zy']
        for prefix in base64_prefixes:
            if text.startswith(prefix):
                return True
        return False
    
    @staticmethod
    def _extract_base64_data(img_data: str) -> str:
        """
        从各种图片数据格式中提取纯base64字符串（无头）
        用于直接发送 send_image
        """
        if not img_data:
            return ""
        # 如果已经是data:image格式，提取逗号后面的部分
        if img_data.startswith('data:image/'):
            match = re.search(r'base64,(.*)', img_data)
            if match:
                return match.group(1)
        # 如果以base64,开头，去掉前缀
        if img_data.startswith('base64,'):
            return img_data[7:]
        # 否则认为是纯base64，直接返回
        return img_data
    
    @staticmethod
    def _to_full_data_url(img_data: str) -> str:
        """
        将图片数据转换为完整的 data URL 格式
        用于合并转发消息
        """
        if img_data.startswith('data:image/'):
            return img_data
        if img_data.startswith('base64,'):
            return f"data:image/png;base64,{img_data[7:]}"
        # 尝试根据前缀推断格式
        if img_data.startswith('/9j/'):
            return f"data:image/jpeg;base64,{img_data}"
        elif img_data.startswith('iVBORw'):
            return f"data:image/png;base64,{img_data}"
        elif img_data.startswith('R0lGOD'):
            return f"data:image/gif;base64,{img_data}"
        elif img_data.startswith('PHN2Zy'):
            return f"data:image/svg+xml;base64,{img_data}"
        else:
            # 默认为png
            return f"data:image/png;base64,{img_data}"
    
    @staticmethod
    def _create_text_content(text: str) -> Dict:
        """创建文本消息内容（同原代码）"""
        return {
            "type": "text",
            "data": {
                "text": text
            }
        }
    
    @staticmethod
    def _create_image_content(img_base64: str) -> Dict:
        """创建图片消息内容（用于合并转发，返回完整data URL）"""
        full_url = MessageForwardHelper._to_full_data_url(img_base64)
        return {
            "type": "image",
            "data": {
                "file": full_url,
                "summary": "[图片]"
            }
        }
    
    @staticmethod
    async def _fallback_send_new(command_instance, messages_list: List) -> bool:
        """回退到直接发送消息"""
        logger.warning("⚠️ 使用回退方案：直接发送消息")
        await command_instance.send_text("⚠️ 当前napcat服务无法连接，已切换至基础发送模式，请联系管理员修复")
        success_count = 0
        
        if not isinstance(messages_list, list):
            messages_list = [messages_list]
        
        for item in messages_list:
            if isinstance(item, list):
                # 子列表：依次发送每个元素
                for subitem in item:
                    if isinstance(subitem, str):
                        success = await MessageForwardHelper._send_single_item_direct(command_instance, subitem)
                        if success:
                            success_count += 1
                    elif isinstance(subitem, dict):
                        success = await MessageForwardHelper._send_dict_item_direct(command_instance, subitem)
                        if success:
                            success_count += 1
            elif isinstance(item, str):
                success = await MessageForwardHelper._send_single_item_direct(command_instance, item)
                if success:
                    success_count += 1
            elif isinstance(item, dict):
                success = await MessageForwardHelper._send_dict_item_direct(command_instance, item)
                if success:
                    success_count += 1
        
        logger.info(f"回退方案完成，成功发送 {success_count} 条消息")
        return success_count > 0
    
    @staticmethod
    async def _send_single_item_direct(command_instance, item: str) -> bool:
        """直接发送单个字符串项（文本或图片）"""
        if MessageForwardHelper._is_image_data(item):
            # 图片：提取纯base64后调用 send_image
            try:
                base64_data = MessageForwardHelper._extract_base64_data(item)
                await command_instance.send_image(base64_data)
                logger.debug("直接发送图片消息（无头base64）")
                return True
            except Exception as e:
                logger.error(f"直接发送图片消息失败: {str(e)}")
                # 尝试发送纯文本提示
                try:
                    await command_instance.send_text("[图片发送失败]")
                except:
                    pass
                return False
        else:
            # 文本
            if item.strip():
                try:
                    await command_instance.send_text(item)
                    logger.debug(f"直接发送文本消息: {item[:50]}...")
                    return True
                except Exception as e:
                    logger.error(f"直接发送文本消息失败: {str(e)}")
                    return False
        return False
    
    @staticmethod
    async def _send_dict_item_direct(command_instance, item: dict) -> bool:
        """直接发送字典格式消息项"""
        success = False
        if 'text' in item and item['text']:
            try:
                await command_instance.send_text(item['text'])
                logger.debug(f"直接发送文本消息: {item['text'][:50]}...")
                success = True
            except Exception as e:
                logger.error(f"直接发送文本消息失败: {str(e)}")
        if 'image' in item and item['image']:
            try:
                base64_data = MessageForwardHelper._extract_base64_data(item['image'])
                await command_instance.send_image(base64_data)
                logger.debug("直接发送图片消息（无头base64）")
                success = True
            except Exception as e:
                logger.error(f"直接发送图片消息失败: {str(e)}")
        return success