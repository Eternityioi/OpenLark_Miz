# 本地部署指南

本文档详细介绍了如何在本地环境中部署和运行飞书机器人项目。

## 环境要求

- Python 3.9+
- pip 最新版本
- Git（可选，用于版本控制）

## 安装步骤

### 1. 克隆项目
```bash
git clone <项目地址>
cd OpenLark_Miz
```

### 2. 创建虚拟环境（推荐）
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 配置环境变量
复制 `.env.example` 文件为 `.env`：
```bash
cp .env.example .env
```

编辑 `.env` 文件，配置以下必要环境变量：

```env
# 飞书应用配置
# 获取方式 https://open.feishu.cn/app
FEISHU_APP_ID=your_app_id
FEISHU_APP_SECRET=your_app_secret
FEISHU_VERIFICATION_TOKEN=your_verification_token
FEISHU_ENCRYPT_KEY=your_encrypt_key

# Cookie检查通知配置
# 获取方式 https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your_botwebhook_key

# 多维表格配置（用于记录操作日志）
# 获取方式 https://open.feishu.cn/document/server-docs/docs/bitable-v1/notification
BITABLE_APP_TOKEN=your_bitable_app_token
BITABLE_TABLE_ID=your_bitable_table_id

# 企业配置
COMPANY_ID=12345

# HAR文件路径
HAR_FILE=data/cookie.har

# Cookie检查配置
COOKIE_CHECK_INTERVAL=3600  # 检查间隔（秒），默认1小时
```

### 5. 运行项目
```bash
python sdk_connect.py
```

## 功能测试

### 测试环境变量配置
```bash
python -c "import os; print('环境变量检查:', dict((k, v) for k, v in os.environ.items() if k.startswith('FEISHU_') or k == 'COMPANY_ID'))"
```

## 常见问题

### 1. 依赖安装失败
- 确保使用Python 3.9+版本
- 尝试使用清华镜像源：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`

### 2. 环境变量未生效
- 确认 `.env` 文件在项目根目录
- 重启终端或IDE使环境变量生效

### 3. 飞书API连接失败
- 检查网络连接
- 确认应用ID和密钥正确
- 确认应用权限配置正确

## 开发建议

1. **使用虚拟环境**：避免污染系统Python环境
2. **定期更新依赖**：`pip install -U -r requirements.txt`
3. **备份配置**：重要的环境变量配置建议备份
4. **日志监控**：关注程序运行日志，及时发现问题
