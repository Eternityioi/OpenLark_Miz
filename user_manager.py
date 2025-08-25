"""
用户有效期管理模块
存储用户添加时间，管理24小时有效期，防止重复添加和自动删除过期用户
"""
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class UserManager:
    def __init__(self, data_file: str = "data/user_data.json"):
        """初始化用户管理器
        
        Args:
            data_file: 用户数据存储文件路径
        """
        self.data_file = data_file
        self.users = self._load_users()
    
    def _load_users(self) -> Dict[str, Dict]:
        """从文件加载用户数据"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}
        return {}
    
    def _save_users(self) -> None:
        """保存用户数据到文件"""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.users, f, ensure_ascii=False, indent=2)
    
    def add_user(self, miz_id: str, open_id: Optional[str] = None) -> bool:
        """添加用户并记录添加时间
        
        Args:
            miz_id: 觅智网用户ID
            open_id: 飞书用户ID（可选）
            
        Returns:
            bool: 是否成功添加（如果24小时内已存在则返回False）
        """
        current_time = time.time()
        
        # 检查用户是否在24小时内已存在且未过期
        if miz_id in self.users:
            user_data = self.users[miz_id]
            expire_time = user_data.get('expire_time', 0)
            
            # 如果用户未过期，不允许重复添加
            if current_time < expire_time:
                return False
        
        # 添加或更新用户信息
        self.users[miz_id] = {
            'add_time': current_time,
            'open_id': open_id,
            'expire_time': current_time + 24 * 3600  # 24小时后过期
        }
        
        self._save_users()
        return True
    
    def can_add_user(self, miz_id: str) -> bool:
        """检查用户是否可以被添加（用户已过期）
        
        Args:
            miz_id: 觅智网用户ID
            
        Returns:
            bool: 是否可以添加
        """
        if miz_id not in self.users:
            return True
            
        user_data = self.users[miz_id]
        expire_time = user_data.get('expire_time', 0)
        
        # 如果用户已过期，则可以再次添加
        return time.time() >= expire_time
    
    def get_expired_users(self) -> List[str]:
        """获取已过期的用户列表
        
        Returns:
            List[str]: 过期用户的miz_id列表
        """
        current_time = time.time()
        expired_users = []
        
        for miz_id, user_data in self.users.items():
            expire_time = user_data.get('expire_time', 0)
            if current_time >= expire_time:
                expired_users.append(miz_id)
        
        return expired_users
    
    def remove_user(self, miz_id: str) -> bool:
        """移除用户
        
        Args:
            miz_id: 觅智网用户ID
            
        Returns:
            bool: 是否成功移除
        """
        if miz_id in self.users:
            del self.users[miz_id]
            self._save_users()
            return True
        return False
    
    def get_user_info(self, miz_id: str) -> Optional[Dict]:
        """获取用户信息
        
        Args:
            miz_id: 觅智网用户ID
            
        Returns:
            Optional[Dict]: 用户信息字典，包含add_time和open_id
        """
        return self.users.get(miz_id)
    
    def cleanup_expired_users(self) -> List[str]:
        """清理过期用户并返回被清理的用户列表
        
        Returns:
            List[str]: 被清理的用户miz_id列表
        """
        expired_users = self.get_expired_users()
        for miz_id in expired_users:
            self.remove_user(miz_id)
        return expired_users
    
    def get_all_users(self) -> Dict[str, Dict]:
        """获取所有用户信息
        
        Returns:
            Dict[str, Dict]: 所有用户数据的字典
        """
        return self.users.copy()

# 全局用户管理器实例
user_manager = UserManager()

if __name__ == "__main__":
    # 测试代码
    manager = UserManager("test_user_data.json")
    
    # 测试添加用户
    print("添加用户12345:", manager.add_user("12345", "test_open_id"))
    print("再次添加用户12345:", manager.add_user("12345", "test_open_id"))
    
    # 测试获取过期用户
    print("过期用户:", manager.get_expired_users())
    
    # 清理测试文件
    if os.path.exists("test_user_data.json"):
        os.remove("test_user_data.json")