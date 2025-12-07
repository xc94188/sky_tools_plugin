"""
合并转发消息助手模块
提供统一的合并转发消息发送功能，支持多种消息格式和分条/混合发送
"""
import json
import requests
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
        """发送合并转发消息
        
        Args:
            command_instance: BaseCommand实例，需要包含message属性和get_config方法
            messages_list: 消息列表，支持格式：
                - 纯文本: '文本消息'
                - 纯图片: 图片base64字符串
                - 列表格式: ['文本消息', '图片base64'] (每个元素作为独立节点)
                - 字典格式: {'text': '文本', 'image': '图片base64'} (混合为一条消息)
                - OpenAPI格式: [{'type': 'text', 'data': {'text': '文本'}}, 
                               {'type': 'image', 'data': {'file': '图片base64'}}]
                - 嵌套列表格式: ['文本', ['文本', 图片, '文本']] (子列表内元素混合为一个节点)
            prompt: 转发消息的外显提示，默认为"群聊的聊天记录"
            summary: 转发消息的底部摘要，默认为"查看X条转发消息"
            source: 转发消息的标题，默认为聊天来源
            
        Returns:
            bool: 发送是否成功
        """
        try:
            # 导入必要的模块（延迟导入以避免循环依赖）
            from src.plugin_system.apis import config_api
            
            # 获取napcat配置
            napcat_enabled = command_instance.get_config("napcat.enabled", True)
            if not napcat_enabled:
                logger.info("合并转发功能已禁用，使用直接发送")
                return await MessageForwardHelper._fallback_send_new(command_instance, messages_list)
            
            api_url = command_instance.get_config("napcat.api_url", "http://127.0.0.1:5222")
            api_token = command_instance.get_config("napcat.token", "")
            timeout = command_instance.get_config("napcat.timeout", 30)
            
            logger.info(f"Napcat配置: 地址={api_url}, 启用={napcat_enabled}, 超时={timeout}秒")
            
            # 获取bot QQ号
            bot_qq = None
            bot_nickname = None
            try:
                bot_qq = str(config_api.get_global_config("bot.qq_account", ""))
                bot_nickname = str(config_api.get_global_config("bot.nickname", "麦麦"))
                logger.info(f"获取到bot配置: QQ={bot_qq}, nickname={bot_nickname}")
            except Exception as e:
                logger.error(f"获取bot配置失败: {str(e)}")
            
            # 检查是否是有效的QQ号
            is_valid_qq = bot_qq and bot_qq != "1145141919810" and bot_qq.isdigit()
            
            if not is_valid_qq:
                logger.warning(f"❌ 无法获取有效bot QQ号(当前值: {bot_qq})，回退到直接消息发送")
                return await MessageForwardHelper._fallback_send_new(command_instance, messages_list)
            
            # 如果没有获取到nickname，使用默认值
            if not bot_nickname:
                bot_nickname = "麦麦"
                logger.warning("使用默认昵称: 麦麦")
            
            # 关键：从message属性获取聊天信息
            if not hasattr(command_instance, 'message'):
                logger.error("❌ command_instance没有message属性，无法确定发送目标")
                return await MessageForwardHelper._fallback_send_new(command_instance, messages_list)
            
            message_obj = command_instance.message
            
            # 解析消息列表，构建节点
            messages = MessageForwardHelper._parse_messages_list(messages_list, bot_qq, bot_nickname)
            
            if not messages:
                logger.warning("没有消息需要发送")
                return False
            
            # 计算总消息条数
            total_messages = len(messages)
            
            # 生成summary和source
            if summary is None:
                summary = f"查看{total_messages}条转发消息"
            
            if source is None:
                source = "群聊的聊天记录"
            
            # 构建请求数据
            forward_data = {
                "messages": messages,
                "news": MessageForwardHelper._generate_news(messages, bot_nickname),
                "prompt": prompt,
                "summary": summary,
                "source": source
            }
            
            # 确定发送目标
            target_info = MessageForwardHelper._get_target_info(message_obj)
            if not target_info:
                logger.error("❌ 无法确定发送目标")
                return await MessageForwardHelper._fallback_send_new(command_instance, messages_list)
            
            # 更新forward_data和source
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
            
            # 发送请求
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
        """解析消息列表，构建一级合并转发消息列表
        
        规则：
        1. 如果元素是列表，则列表内的元素合并为一个节点
        2. 如果元素是字符串、字典或OpenAPI格式，则单独作为一个节点
        3. ['文本', 图片] -> 2个节点
        4. ['文本', ['文本', 图片, '文本']] -> 2个节点（第二个节点包含3条混合消息）
        """
        messages = []
        
        # 如果传入的是单个元素，转换为列表
        if not isinstance(messages_list, list):
            messages_list = [messages_list]
        
        for item in messages_list:
            if isinstance(item, list):
                # 子列表：将子列表内的所有元素合并为一个节点
                content = []
                for subitem in item:
                    content_items = MessageForwardHelper._parse_single_item(subitem)
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
                # 单个元素：单独作为一个节点
                content = MessageForwardHelper._parse_single_item(item)
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
    def _parse_single_item(item) -> List[Dict]:
        """解析单个消息项，返回content列表"""
        content = []
        
        if isinstance(item, str):
            # 纯文本或纯图片
            if MessageForwardHelper._is_image_data(item):
                img_content = MessageForwardHelper._create_image_content(item)
                if img_content:
                    content.append(img_content)
            else:
                if item.strip():
                    text_content = MessageForwardHelper._create_text_content(item)
                    if text_content:
                        content.append(text_content)
        
        elif isinstance(item, dict):
            # OpenAPI格式或字典格式
            if 'type' in item and 'data' in item:
                # OpenAPI格式，直接添加
                content.append(item)
            else:
                # 字典格式: {'text': '文本', 'image': '图片base64'}
                if 'text' in item and item['text']:
                    text_content = MessageForwardHelper._create_text_content(item['text'])
                    if text_content:
                        content.append(text_content)
                if 'image' in item and item['image']:
                    img_content = MessageForwardHelper._create_image_content(item['image'])
                    if img_content:
                        content.append(img_content)
        
        return content
    
    @staticmethod
    def _generate_news(messages: List[Dict], bot_nickname: str, max_preview: int = 4) -> List[Dict]:
        """生成news外显列表
        
        格式: [{"text": "麦麦:文本[图片]文本[图片]文本文本"}, {"text": "麦麦:..."}]
        每个节点对应一个news项，展示该节点内的消息组合预览
        """
        news_items = []
        
        for i, message in enumerate(messages[:max_preview]):
            # 从节点中提取所有消息内容生成预览
            content = message["data"]["content"]
            preview_parts = []
            
            for item in content:
                if isinstance(item, dict):
                    item_type = item.get("type")
                    if item_type == "text":
                        text = item.get("data", {}).get("text", "")
                        if text:
                            # 简化文本，去除换行和多余空格
                            simplified_text = text.replace('\n', ' ').replace('\r', '').strip()
                            if simplified_text:
                                preview_parts.append(simplified_text)
                    elif item_type == "image":
                        preview_parts.append(" [图片]")
                    else:
                        preview_parts.append(f"[{item_type}]")
            
            # 组合预览内容
            if preview_parts:
                node_preview = "".join(preview_parts)
                # 限制总长度
                if len(node_preview) > 50:
                    node_preview = node_preview[:47] + "..."
                
                news_items.append({"text": f"{bot_nickname}: {node_preview}"})
            else:
                # 如果没有内容，使用默认预览
                news_items.append({"text": f"{bot_nickname}: 消息{i+1}"})
        
        # 如果没有预览，使用默认
        if not news_items:
            news_items.append({"text": f"{bot_nickname}: [聊天记录]"})
        
        return news_items
    
    @staticmethod
    def _get_target_info(message_obj) -> Optional[Dict]:
        """获取发送目标信息"""
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
            # 回退方案
            return MessageForwardHelper._get_target_info_fallback(message_obj)
    
    @staticmethod
    def _get_target_info_fallback(message_obj) -> Optional[Dict]:
        """回退方式获取发送目标信息"""
        if not hasattr(message_obj, 'message_info'):
            return None
        
        message_info = message_obj.message_info
        target_info = {}
        
        if hasattr(message_info, 'group_info') and message_info.group_info is not None:
            # 群聊
            if hasattr(message_info.group_info, 'group_id'):
                target_info["group_id"] = message_info.group_info.group_id
                group_name = "群聊"
                if hasattr(message_info.group_info, 'group_name') and message_info.group_info.group_name:
                    group_name = message_info.group_info.group_name
                target_info["group_name"] = group_name
                logger.info(f"✅ 从group_info获取群聊ID: {target_info['group_id']}")
        
        else:
            # 私聊
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
        """发送API请求"""
        try:
            # 构建请求头
            headers = {"Content-Type": "application/json"}
            if api_token:
                headers["Authorization"] = f"Bearer {api_token}"
                logger.info("使用API令牌进行认证")
            
            # 构建完整的API地址
            full_api_url = f"{api_url.rstrip('/')}/send_forward_msg"
            logger.info(f"发送请求到: {full_api_url}")
            
            # 调用napcatapi发送合并转发消息
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
        """判断是否为图片数据"""
        if not isinstance(text, str):
            return False
        
        # 检查是否是base64图片数据
        if text.startswith('data:image/'):
            return True
        
        # 检查是否是纯base64字符串（没有data:前缀）
        if text.startswith('base64,') or (len(text) > 100 and 'base64' in text):
            return True
        
        # 检查是否是常见的base64图片前缀
        base64_prefixes = ['/9j/', 'iVBORw', 'R0lGOD', 'UE5HDQ', 'PHN2Zy']
        for prefix in base64_prefixes:
            if text.startswith(prefix):
                return True
        
        return False
    
    @staticmethod
    def _create_text_content(text: str) -> Dict:
        """创建文本消息内容"""
        return {
            "type": "text",
            "data": {
                "text": text
            }
        }
    
    @staticmethod
    def _create_image_content(img_base64: str) -> Dict:
        """创建图片消息内容"""
        # 确保是完整的data URL格式
        if not img_base64.startswith('data:image/'):
            if img_base64.startswith('base64,'):
                img_base64 = f"data:image/png;base64,{img_base64[7:]}"
            elif img_base64.startswith('/9j/'):  # JPEG
                img_base64 = f"data:image/jpeg;base64,{img_base64}"
            elif img_base64.startswith('iVBORw'):  # PNG
                img_base64 = f"data:image/png;base64,{img_base64}"
            else:
                img_base64 = f"data:image/png;base64,{img_base64}"
        
        return {
            "type": "image",
            "data": {
                "file": img_base64,
                "summary": "[图片]"
            }
        }
    
    @staticmethod
    async def _fallback_send_new(command_instance, messages_list: List) -> bool:
        """回退到直接发送消息"""
        logger.warning("⚠️ 使用回退方案：直接发送消息")
        success_count = 0
        
        # 解析消息列表并发送
        if not isinstance(messages_list, list):
            messages_list = [messages_list]
        
        for item in messages_list:
            if isinstance(item, list):
                # 对于子列表，依次发送每个元素
                for subitem in item:
                    if isinstance(subitem, str):
                        success = await MessageForwardHelper._send_single_item(command_instance, subitem)
                        if success:
                            success_count += 1
            elif isinstance(item, str):
                success = await MessageForwardHelper._send_single_item(command_instance, item)
                if success:
                    success_count += 1
            elif isinstance(item, dict):
                # 字典格式
                if 'text' in item and item['text']:
                    try:
                        await command_instance.send_text(item['text'])
                        success_count += 1
                        logger.debug(f"直接发送文本消息: {item['text'][:50]}...")
                    except Exception as e:
                        logger.error(f"直接发送文本消息失败: {str(e)}")
                if 'image' in item and item['image']:
                    try:
                        img_data = item['image']
                        if not img_data.startswith('data:image/'):
                            img_data = MessageForwardHelper._format_image_data(img_data)
                        
                        await command_instance.send_image(img_data)
                        success_count += 1
                        logger.debug("直接发送图片消息")
                    except Exception as e:
                        logger.error(f"直接发送图片消息失败: {str(e)}")
        
        logger.info(f"回退方案完成，成功发送 {success_count} 条消息")
        return success_count > 0
    
    @staticmethod
    async def _send_single_item(command_instance, item: str) -> bool:
        """发送单个消息项"""
        if MessageForwardHelper._is_image_data(item):
            # 图片
            try:
                if not item.startswith('data:image/'):
                    item = MessageForwardHelper._format_image_data(item)
                
                await command_instance.send_image(item)
                logger.debug("直接发送图片消息")
                return True
            except Exception as e:
                logger.error(f"直接发送图片消息失败: {str(e)}")
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
    def _format_image_data(img_data: str) -> str:
        """格式化图片数据为完整的data URL"""
        if img_data.startswith('base64,'):
            return f"data:image/png;base64,{img_data[7:]}"
        elif img_data.startswith('/9j/'):
            return f"data:image/jpeg;base64,{img_data}"
        elif img_data.startswith('iVBORw'):
            return f"data:image/png;base64,{img_data}"
        else:
            return f"data:image/png;base64,{img_data}"