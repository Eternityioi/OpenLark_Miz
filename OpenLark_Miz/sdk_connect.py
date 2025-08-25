"""
飞书长连接服务器
使用飞书SDK的WebSocket长连接机制处理事件和回调
"""
import os
import json
import signal
import datetime
import sys
import lark_oapi as lark
from dotenv import load_dotenv
from feishu_bot import FeishuBot

# 加载环境变量
load_dotenv()

# 初始化飞书机器人
bot = FeishuBot()

def do_p2_im_message_receive_v1(data: lark.im.v1.P2ImMessageReceiveV1) -> None:
    """
    处理v2.0版本的消息事件
    """
    print(f'[{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}][消息事件]: 用户ID：{data.event.sender.sender_id.user_id} - 发送了消息：{data.event.message.content}')
    
    try:
        # 提取消息内容
        event_data = data.event
        if hasattr(event_data, 'message') and hasattr(event_data.message, 'content'):
            # 解析消息内容
            content_json = json.loads(event_data.message.content)
            text = content_json.get('text', '').strip()
            
            # 创建模拟事件格式给机器人处理
            event = {
                "event": {
                    "message": {
                        "content": event_data.message.content
                    }
                }
            }
            
            # 调用机器人处理消息
            result = bot.handle_message(event)
            # print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][处理结果] {result}")
            
            # 处理添加成员和删除成员指令，传递正确的飞书open_id
            if text.startswith("添加成员") or text.startswith("删除成员"):
                parts = text.split()
                if len(parts) >= 2:
                    miz_id = parts[1]
                    open_id = data.event.sender.sender_id.open_id
                    
                    if text.startswith("添加成员"):
                        result = bot.add_member(miz_id, open_id)
                    else:
                        result = bot.delete_member(miz_id, open_id)
                    
                    # 打印处理结果
                    # print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][处理结果] {result}")
                    
                    # 直接发送回复消息，不再走下面的通用回复逻辑
                    # 根据操作类型和结果发送不同的提示消息，包含用户ID和失败原因
                    if result.get('success'):
                        # 成功情况
                        if text.startswith("添加成员"):
                            message = f"添加用户 {miz_id} 成功"
                        else:
                            message = f"删除用户 {miz_id} 成功"
                    else:
                        # 失败情况
                        if text.startswith("添加成员"):
                            message = f"添加用户 {miz_id} 失败，原因：{result.get('message', '未知错误')}"    
                        else:
                            message = f"删除用户 {miz_id} 失败，原因：{result.get('message', '未知错误')}"
                    
                    try:
                        # 使用飞书SDK发送回复消息
                        from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody
                        from lark_oapi import JSON
                        
                        # 构建回复消息内容
                        reply_content = JSON.marshal({"text": message})
                        
                        # 创建API客户端
                        client = lark.Client.builder() \
                            .app_id(os.getenv('FEISHU_APP_ID')) \
                            .app_secret(os.getenv('FEISHU_APP_SECRET')) \
                            .build()
                        
                        # 发送回复
                        request = CreateMessageRequest.builder() \
                            .receive_id_type("open_id") \
                            .request_body(CreateMessageRequestBody.builder()
                                .receive_id(data.event.sender.sender_id.open_id)
                                .msg_type("text")
                                .content(reply_content)
                                .build()) \
                            .build()
                        
                        response = client.im.v1.message.create(request)
                        
                        if response.success():
                            print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][发送消息事件-成功] 向用户ID：{data.event.sender.sender_id.user_id} 发送消息成功")
                        else:
                            print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][发送消息事件-失败] 向用户ID：{data.event.sender.sender_id.user_id} 发送消息失败，原因：{response.msg}, LogID: {response.get_log_id()}")
                            
                    except Exception as send_error:
                        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][发送消息事件-失败] 向用户ID：{data.event.sender.sender_id.user_id} 发送消息失败，原因：{send_error}")
                    
                    # 直接返回，不再走下面的通用处理逻辑
                    return
            
            # 发送回复消息给用户
            if result.get('success') and result.get('message'):
                try:
                    # 使用飞书SDK发送回复消息
                    from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody
                    from lark_oapi import JSON
                    
                    # 构建回复消息内容
                    reply_content = JSON.marshal({"text": result['message']})
                    
                    # 创建API客户端
                    client = lark.Client.builder() \
                        .app_id(os.getenv('FEISHU_APP_ID')) \
                        .app_secret(os.getenv('FEISHU_APP_SECRET')) \
                        .build()
                    
                    # 发送回复
                    request = CreateMessageRequest.builder() \
                        .receive_id_type("open_id") \
                        .request_body(CreateMessageRequestBody.builder()
                            .receive_id(data.event.sender.sender_id.open_id)
                            .msg_type("text")
                            .content(reply_content)
                            .build()) \
                        .build()
                    
                    response = client.im.v1.message.create(request)
                    
                    if response.success():
                        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][发送消息事件-成功] 向用户ID：{data.event.sender.sender_id.user_id} 发送消息成功")
                    else:
                        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][发送消息事件-失败] 向用户ID：{data.event.sender.sender_id.user_id} 发送消息失败，原因：{response.msg}, LogID: {response.get_log_id()}")
                        
                except Exception as send_error:
                    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][发送消息事件-失败] 向用户ID：{data.event.sender.sender_id.user_id} 发送消息失败，原因：{send_error}")
            
    except Exception as e:
        # 尝试获取飞书SDK的logid
        log_id = getattr(e, 'log_id', 'N/A')
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][处理消息时出错] {e}, LogID: {log_id}")

def do_p2_chat_access_event_bot_p2p_chat_entered_v1(data: lark.CustomizedEvent) -> None:
    """
    处理v2.0版本的单聊进入事件
    """
    try:
        # 提取事件数据 - data.event可能是字典对象
        event_data = data.event if isinstance(data.event, dict) else data.event.__dict__
        # 根据调试信息，事件数据包含: chat_id, last_message_create_time, last_message_id, operator_id
        operator_id_dict = event_data.get('operator_id', {}) if isinstance(event_data, dict) else getattr(data.event, 'operator_id', {})
        operator_id = operator_id_dict.get('user_id', 'unknown') if isinstance(operator_id_dict, dict) else 'unknown'
        chat_id = event_data.get('chat_id', 'unknown') if isinstance(event_data, dict) else getattr(data.event, 'chat_id', 'unknown')
        # 应用ID可以从data对象本身获取
        # 从header对象获取应用ID
        if hasattr(data, 'header') and hasattr(data.header, 'app_id'):
            app_id = data.header.app_id
        else:
            app_id = 'unknown'
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][单聊进入事件] 用户ID: {operator_id} 进入应用ID: {app_id}")
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][单聊进入事件] 应用已加入会话ID: {chat_id}")
        
        # 这里可以添加处理单聊进入事件的业务逻辑
        # 例如：发送欢迎消息、记录会话开始等
        
    except Exception as e:
        # 尝试获取飞书SDK的logid
        log_id = getattr(e, 'log_id', 'N/A')
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][处理单聊进入事件时出错] {e}, LogID: {log_id}")

def do_bitable_field_changed_event(data: lark.CustomizedEvent) -> None:
    """
    处理多维表格字段变更事件
    """
    try:
        event_type = getattr(data.event, 'type', 'unknown')
        table_id = getattr(data.event, 'table_id', 'unknown')
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][多维表格字段变更事件] 类型: {event_type}, 表格ID: {table_id}")
    except Exception as e:
        # 尝试获取飞书SDK的logid
        log_id = getattr(e, 'log_id', 'N/A')
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][处理多维表格字段变更事件时出错] {e}, LogID: {log_id}")

def do_bitable_record_changed_event(data: lark.CustomizedEvent) -> None:
    """
    处理多维表格记录变更事件
    """
    try:
        event_type = getattr(data.event, 'type', 'unknown')
        table_id = getattr(data.event, 'table_id', 'unknown')
        record_id = getattr(data.event, 'record_id', 'unknown')
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][多维表格记录变更事件] 类型: {event_type}, 表格ID: {table_id}, 记录ID: {record_id}")
    except Exception as e:
        # 尝试获取飞书SDK的logid
        log_id = getattr(e, 'log_id', 'N/A')
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][处理多维表格记录变更事件时出错] {e}, LogID: {log_id}")

def do_file_edit_event(data: lark.CustomizedEvent) -> None:
    """
    处理文件编辑事件
    """
    try:
        file_token = getattr(data.event, 'file_token', 'unknown')
        operator_id = getattr(data.event, 'operator_id', 'unknown')
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][文件编辑事件] 文件Token: {file_token}, 操作者ID: {operator_id}")
    except Exception as e:
        # 尝试获取飞书SDK的logid
        log_id = getattr(e, 'log_id', 'N/A')
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][处理文件编辑事件时出错] {e}, LogID: {log_id}")

def do_file_title_updated_event(data: lark.CustomizedEvent) -> None:
    """
    处理文件标题更新事件
    """
    try:
        file_token = getattr(data.event, 'file_token', 'unknown')
        new_title = getattr(data.event, 'title', 'unknown')
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][文件标题更新事件] 文件Token: {file_token}, 新标题: {new_title}")
    except Exception as e:
        # 尝试获取飞书SDK的logid
        log_id = getattr(e, 'log_id', 'N/A')
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][处理文件标题更新事件时出错] {e}, LogID: {log_id}")

def do_p2p_chat_create_event(data: lark.CustomizedEvent) -> None:
    """
    处理p2p聊天创建事件
    """
    try:
        # 提取事件数据
        event_data = data.event if isinstance(data.event, dict) else data.event.__dict__
        
        # 获取聊天相关信息
        chat_id = event_data.get('chat_id', 'unknown') if isinstance(event_data, dict) else getattr(data.event, 'chat_id', 'unknown')
        operator_id_dict = event_data.get('operator_id', {}) if isinstance(event_data, dict) else getattr(data.event, 'operator_id', {})
        operator_id = operator_id_dict.get('user_id', 'unknown') if isinstance(operator_id_dict, dict) else 'unknown'
        
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][p2p聊天创建事件] 聊天ID: {chat_id}, 操作者ID: {operator_id}")
        
    except Exception as e:
        # 尝试获取飞书SDK的logid
        log_id = getattr(e, 'log_id', 'N/A')
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][处理p2p聊天创建事件时出错] {e}, LogID: {log_id}")

# 创建事件处理器
event_handler = lark.EventDispatcherHandler.builder(os.getenv('FEISHU_VERIFICATION_TOKEN'), os.getenv('FEISHU_ENCRYPT_KEY')) \
    .register_p2_im_message_receive_v1(do_p2_im_message_receive_v1) \
    .register_p2_customized_event("im.chat.access_event.bot_p2p_chat_entered_v1", do_p2_chat_access_event_bot_p2p_chat_entered_v1) \
    .register_p1_customized_event("drive.file.bitable_field_changed_v1", do_bitable_field_changed_event) \
    .register_p1_customized_event("drive.file.bitable_record_changed_v1", do_bitable_record_changed_event) \
    .register_p1_customized_event("drive.file.edit_v1", do_file_edit_event) \
    .register_p1_customized_event("drive.file.title_updated_v1", do_file_title_updated_event) \
    .register_p2_customized_event("im.chat.p2p_chat_create", do_p2p_chat_create_event) \
    .build()

def signal_handler(sig, frame):
    """
    处理Ctrl+C信号的优雅退出
    """
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][正在关闭SDK连接客户端...]")
    sys.exit(0)

def main():
    """
    启动长连接客户端
    """
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    
    # 从环境变量获取应用凭证
    app_id = os.getenv('FEISHU_APP_ID')
    app_secret = os.getenv('FEISHU_APP_SECRET')
    verification_token = os.getenv('FEISHU_VERIFICATION_TOKEN')
    encrypt_key = os.getenv('FEISHU_ENCRYPT_KEY')
    
    if not app_id or not app_secret or not verification_token or not encrypt_key:
        print("错误: 未找到飞书应用凭证，请检查.env文件配置")
        return
    
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][启动飞书SDK连接客户端 (AppID: {app_id})]")
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][正在连接飞书开放平台...]")
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][按 Ctrl+C 可关闭连接，程序将退出]")
    
    try:
        # 初始化长连接客户端
        cli = lark.ws.Client(
            app_id=app_id,
            app_secret=app_secret,
            event_handler=event_handler,
            log_level=lark.LogLevel.INFO
        )
        
        # 启动客户端（阻塞式运行）
        cli.start()
        
    except KeyboardInterrupt:
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][收到中断信号，正在关闭连接...]")
    except Exception as e:
        # 尝试获取飞书SDK的logid
        log_id = getattr(e, 'log_id', 'N/A')
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][SDK连接客户端启动时出错] {e}, LogID: {log_id}")
    finally:
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][SDK连接客户端已停止]")

if __name__ == "__main__":
    main()