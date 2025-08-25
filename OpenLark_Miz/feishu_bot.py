"""
飞书机器人主文件
处理飞书事件，执行成员管理操作，并同步到多维表格
"""
import os
import json
from sys import maxsize
import requests
import datetime
import time
import threading
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from user_manager import user_manager

# 加载环境变量
load_dotenv()

class FeishuBot:
    def __init__(self):
        """初始化飞书机器人"""
        self.app_id = os.getenv('FEISHU_APP_ID')
        self.app_secret = os.getenv('FEISHU_APP_SECRET')
        self.verification_token = os.getenv('FEISHU_VERIFICATION_TOKEN')
        self.encrypt_key = os.getenv('FEISHU_ENCRYPT_KEY')
        self.company_id = os.getenv('COMPANY_ID', '15854')
        
        # 获取访问令牌
        self.access_token = self._get_access_token()
        
        # 启动过期用户检查定时任务
        self._start_expired_user_check()
    
    def _get_access_token(self) -> str:
        """获取飞书访问令牌"""
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        response = requests.post(url, json=payload)
        result = response.json()
        
        if result.get('code') == 0:
            return result['tenant_access_token']
        else:
            raise Exception(f"获取访问令牌失败: {result}")
    
    def _extract_cookie_from_har(self, har_file: str, target_url: str) -> Optional[str]:
        """从HAR文件中提取Cookie"""
        try:
            with open(har_file, "r", encoding="utf-8-sig") as f:  # ✅ 兼容 BOM
                har_data = json.load(f)
        except FileNotFoundError:
            print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][错误] 找不到HAR文件 {har_file}")
            return None
        except json.JSONDecodeError:
            print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][错误] HAR文件 {har_file} 格式不正确")
            return None

        candidate_cookie = None

        for entry in har_data["log"]["entries"]:
            request = entry["request"]
            url = request["url"]
            headers = {h["name"].lower(): h["value"] for h in request["headers"]}

            # 优先找目标接口
            if target_url in url and "cookie" in headers:
                return headers["cookie"]

            # 如果目标没找到，记录第一个带 cookie 的请求作为候选
            if not candidate_cookie and "cookie" in headers:
                candidate_cookie = headers["cookie"]

        return candidate_cookie
    
    def add_member(self, miz_id: str, open_id: str = None, retry_count: int = 0) -> Dict[str, Any]:
        """添加成员到觅智网，支持Cookie过期自动重试"""
        # 验证用户ID
        if not self._validate_userid(miz_id):
            return {"success": False, "message": "无效的用户ID，必须为5-20位纯数字"}
        
        # 检查用户是否在24小时内已添加过
        if not user_manager.can_add_user(miz_id):
            return {"success": False, "message": "该用户24小时内已添加过，请等待有效期结束后再添加"}
        
        har_file = os.getenv('HAR_FILE', 'data/cookie.har')
        cookies = self._extract_cookie_from_har(har_file, "/v1/company/addMember")
        
        if not cookies:
            return {"success": False, "message": "无法获取Cookie"}
        
        url = "https://api-go.51miz.com/v1/company/addMember"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0",
            "Origin": "https://www.51miz.com",
            "Referer": "https://www.51miz.com/",
            "Cookie": cookies
        }

        files = {
            "userid": (None, miz_id),
            "companyid": (None, self.company_id),
        }

        try:
            response = requests.post(url, headers=headers, files=files)
            result = response.json()
            
            # 打印响应内容用于调试
            print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][添加成员响应状态码] {response.status_code}")
            print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][添加成员响应内容] {result}")
            
            # 检查Cookie是否过期（401错误）
            if response.status_code == 401 or result.get('code') == 401:
                if retry_count < 1:  # 最多重试1次
                    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][错误] Cookie已过期，尝试重新获取Cookie并重试...")
                    # 清除可能的缓存并重试
                    return self.add_member(miz_id, open_id, retry_count + 1)
                else:
                    self._sync_to_bitable(open_id, "add", "failed", "Cookie已过期，请更新HAR文件", miz_id)
                    return {"success": False, "message": "Cookie已过期，请更新HAR文件后重试"}
            
            # 同步到多维表格
            if response.status_code == 200 and result.get('code') == 200:
                # 记录用户添加时间
                user_manager.add_user(miz_id, open_id)
                self._sync_to_bitable(open_id, "add", "success", result.get('msg', ''), miz_id)
                return {"success": True, "message": "添加成员成功"}
            else:
                error_msg = result.get('msg', '添加成员失败')
                self._sync_to_bitable(open_id, "add", "failed", error_msg, miz_id)
                return {"success": False, "message": error_msg}
                
        except Exception as e:
            self._sync_to_bitable(open_id, "add", "error", str(e), miz_id)
            return {"success": False, "message": f"请求异常: {e}"}
    
    def delete_member(self, miz_id: str, open_id: str = None, retry_count: int = 0) -> Dict[str, Any]:
        """从觅智网删除成员，支持Cookie过期自动重试"""
        # 验证用户ID
        if not self._validate_userid(miz_id):
            return {"success": False, "message": "无效的用户ID，必须为5-20位纯数字"}
        
        har_file = os.getenv('HAR_FILE', 'data/cookie.har')
        cookies = self._extract_cookie_from_har(har_file, "OutCompany&a=DelCompanyMember")
        
        if not cookies:
            return {"success": False, "message": "无法获取Cookie"}
        
        url = "https://www.51miz.com/?m=OutCompany&a=DelCompanyMember&ajax=1"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0",
            "Origin": "https://www.51miz.com",
            "Referer": "https://www.51miz.com/?m=home&a=company_vip",
            "Cookie": cookies,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
        }

        data = {
            "userid": miz_id,
            "company_id": self.company_id,
        }

        try:
            response = requests.post(url, headers=headers, data=data)
            result = response.json()
            
            # 打印响应内容用于调试
            print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][删除成员响应状态码] {response.status_code}")
            print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][删除成员响应内容] {result}")
            
            # 检查Cookie是否过期（401错误）
            if response.status_code == 401 or result.get('code') == 401:
                if retry_count < 1:  # 最多重试1次
                    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][错误] Cookie已过期，尝试重新获取Cookie并重试...")
                    # 清除可能的缓存并重试
                    return self.delete_member(miz_id, open_id, retry_count + 1)
                else:
                    self._sync_to_bitable(open_id, "delete", "failed", "Cookie已过期，请更新HAR文件", miz_id)
                    return {"success": False, "message": "Cookie已过期，请更新HAR文件后重试"}
            
            # 同步到多维表格
            if response.status_code == 200 and result.get('status') == 200:
                self._sync_to_bitable(open_id, "delete", "success", result.get('msg', ''), miz_id)
                # 从用户管理器中移除已删除的用户
                user_manager.remove_user(miz_id)
                return {"success": True, "message": "删除成员成功"}
            else:
                error_msg = result.get('msg', '删除成员失败')
                self._sync_to_bitable(open_id, "delete", "failed", error_msg, miz_id)
                return {"success": False, "message": error_msg}
                
        except Exception as e:
            self._sync_to_bitable(open_id, "delete", "error", str(e), miz_id)
            print(f"删除成员失败: {e}")
            return {"success": False, "message": f"请求异常: {e}"}
    
    def _validate_userid(self, miz_id: str) -> bool:
        """验证用户ID是否为纯数字且长度合理（5-20位）
        
        Args:
            miz_id: 用户ID字符串
            
        Returns:
            bool: True表示有效，False表示无效
        """
        if not miz_id:  
            return False
        
        # 检查是否为纯数字
        if not miz_id.isdigit():
            return False
        
        # 检查长度是否在合理范围内（5-20位）
        if len(miz_id) < 5 or len(miz_id) > 20:
            return False
        
        return True
    
    def _get_valid_user_id(self, open_id: str) -> Optional[str]:
        """获取有效的用户ID格式（根据多维表格字段配置）
        
        检查传入的ID格式，如果是user_id格式（纯数字），则返回None（不处理转换）
        如果是open_id格式（以ou_开头），则直接返回
        """
        if not open_id:
            return None
        
        # 如果是open_id格式（以ou_开头），直接返回
        if open_id.startswith('ou_'):
            return open_id
        
        # 如果是纯数字（user_id格式），返回None，因为无法转换为open_id
        if open_id.isdigit():
            print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][警告] 传入的是user_id格式 '{open_id}'，无法转换为open_id格式，跳过人员字段")
            return None
        
        # 其他格式直接返回
        return open_id
    
    def _sync_to_bitable(self, open_id: str, action: str, status: str, message: str, miz_id: str = '') -> None:
        """同步操作记录到飞书多维表格"""
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][同步到多维表格-成功] 该操作执行用户OpenID：{open_id}")
        
        # 检查是否配置了多维表格参数
        app_token = os.getenv('BITABLE_APP_TOKEN')
        table_id = os.getenv('BITABLE_TABLE_ID')
        
        if not app_token or not table_id:
            print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][同步到多维表格-错误] 未配置多维表格参数 BITABLE_APP_TOKEN 或 BITABLE_TABLE_ID，跳过同步")
            return
        
        try:
            # 获取有效的用户ID格式
            valid_user_id = self._get_valid_user_id(open_id)
            
            # 构建多维表格API请求（明确指定user_id_type为open_id）
            bitable_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records?user_id_type=open_id"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            # 获取当前时间（Unix时间戳格式，毫秒级）
            current_time = int(datetime.datetime.now().timestamp() * 1000)
            
            # 根据用户提供的多维表格字段结构调整字段映射
            # 字段：唯一请求ID（表格自动生成）、操作人、操作人部门（多维表格补全）、操作人工号（多维表格补全）、操作时间、事件操作、事件状态、事件记录
            data = {
                "fields": {
                    "操作人": [{"id": valid_user_id}] if valid_user_id and valid_user_id != "test_open_id" else [],  # 使用有效的用户ID
                    "操作时间": current_time,
                    "事件操作": "添加用户" if action == "add" else "删除用户",  # 单选选项
                    "事件状态": "成功" if status == "success" else "失败",  # 单选选项
                    "事件记录": f"{miz_id} - {action}操作: {status} - {message}"
                }
            }
            
            # 发送请求到多维表格
            response = requests.post(bitable_url, headers=headers, json=data, timeout=10)
            result = response.json()
            
            if response.status_code == 200 and result.get('code') == 0:
                print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][同步到多维表格-成功] 多维表格同步成功: {{'事件记录': '{result.get('data', {}).get('record', {}).get('fields', {}).get('事件记录', '')}', 'record_id': '{result.get('data', {}).get('record', {}).get('record_id', '')}'}}")
            else:
                print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][同步到多维表格-失败] 多维表格同步失败: 状态码 {response.status_code}, 响应: {result}")
                
        except requests.exceptions.RequestException as e:
            print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][同步到多维表格-网络错误] 多维表格同步网络错误: {e}")
        except Exception as e:
            print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][同步到多维表格-异常] 多维表格同步异常: {e}")
    
    def _start_expired_user_check(self):
        """启动过期用户检查定时任务"""
        def check_expired_users():
            while True:
                try:
                    # 获取所有过期用户
                    expired_users = user_manager.get_expired_users()
                    
                    for userid in expired_users:
                        try:
                            # 自动删除过期用户
                            result = self.delete_member(userid)
                            if result.get("success"):
                                print(f"自动删除过期用户 {userid} 成功")
                                # 从用户管理器中移除
                                user_manager.remove_user(userid)
                            else:
                                print(f"自动删除过期用户 {userid} 失败: {result.get('message')}")
                        except Exception as e:
                            print(f"删除过期用户 {userid} 时发生错误: {str(e)}")
                    
                    # 每小时检查一次
                    time.sleep(3600)
                    
                except Exception as e:
                    print(f"过期用户检查任务发生错误: {str(e)}")
                    time.sleep(300)  # 5分钟后重试
        
        # 启动后台线程
        thread = threading.Thread(target=check_expired_users, daemon=True)
        thread.start()
        print("过期用户检查定时任务已启动")
    
    def check_cookie_status(self) -> Dict[str, Any]:
        """检查Cookie有效性状态
        
        Returns:
            Dict[str, Any]: Cookie状态信息，包含有效性、上次检查时间和下次检查时间
        """
        # 这里实现简单的Cookie状态检查逻辑
        # 实际可以根据需要添加更复杂的检查逻辑
        current_time = time.time()
        
        # 检查Cookie文件是否存在
        har_file = os.getenv('HAR_FILE', 'data/cookie.har')
        cookie_exists = os.path.exists(har_file)
        
        # 简单的有效性检查：如果文件存在且最近修改过，则认为有效
        if cookie_exists:
            # 获取文件修改时间
            mod_time = os.path.getmtime(har_file)
            # 如果文件在24小时内修改过，认为Cookie有效
            is_valid = (current_time - mod_time) < 86400
        else:
            is_valid = False
        
        return {
            "is_valid": is_valid,
            "last_check_time": current_time,
            "next_check_time": current_time + 3600  # 1小时后再次检查
        }
    
    def handle_message(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """处理飞书消息事件"""
        message_content = event.get('event', {}).get('message', {}).get('content', '')
        
        try:
            # 解析消息内容
            content_json = json.loads(message_content)
            text = content_json.get('text', '').strip()
        except:
            text = message_content.strip()
        
        # 解析指令
        # 注意：添加成员和删除成员指令现在在sdk_connect.py中直接处理
        # 这里只处理其他指令，避免重复处理
        if text.startswith("添加成员") or text.startswith("删除成员"):
            # 这些指令已经在sdk_connect.py中处理，这里返回提示信息
            return {"success": False, "message": "指令正在处理中，请稍候..."}
        
        elif text in ["使用帮助", "帮助", "help"]:
            help_text = """可用指令:\n• 添加成员 [userid] - 添加成员到企业（一次授权仅允许使用24小时，期间不允许重复添加）\n• 删除成员 [userid] - 从企业删除成员\n• Cookie状态 - 检查Cookie有效性状态\n• 用户状态 [userid] - 查看用户有效期状态\n• 使用帮助 - 显示帮助信息"""
            return {"success": True, "message": help_text}
        
        elif text in ["Cookie状态", "cookie状态", "cookie"]:
            status = self.check_cookie_status()
            status_text = f"🍪 Cookie状态检查\n有效性: {'✅ 有效' if status['is_valid'] else '❌ 无效'}\n上次检查: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(status['last_check_time']))}\n下次检查: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(status['next_check_time']))}"
            return {"success": True, "message": status_text}
        
        elif text.startswith("用户状态"):
            # 处理用户状态查询指令
            parts = text.split()
            if len(parts) < 2:
                return {"success": False, "message": "请输入用户ID，格式：用户状态 [userid]"}
            
            miz_id = parts[1]
            user_info = user_manager.get_user_info(miz_id)
            
            if not user_info:
                return {"success": True, "message": f"用户 {miz_id} 未找到或已过期"}
            
            add_time = user_info.get('add_time', 0)
            expire_time = user_info.get('expire_time', 0)
            current_time = time.time()
            
            # 计算剩余时间
            remaining_time = expire_time - current_time
            if remaining_time <= 0:
                return {"success": True, "message": f"用户 {miz_id} 已过期"}
            
            # 格式化时间显示
            add_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(add_time))
            expire_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expire_time))
            remaining_hours = int(remaining_time // 3600)
            remaining_minutes = int((remaining_time % 3600) // 60)
            
            status_text = f"👤 用户状态查询\n用户ID: {miz_id}\n添加时间: {add_time_str}\n过期时间: {expire_time_str}\n剩余有效期: {remaining_hours}小时{remaining_minutes}分钟"
            return {"success": True, "message": status_text}
        
        else:
            return {"success": False, "message": "未知指令，请输入'帮助'查看可用指令"}