# GitHub Actions 自动化部署指南

本文档详细介绍了如何使用 GitHub Actions 实现项目的自动化测试和部署。

## 工作流概述

项目包含两个主要的工作流任务：

### 1. Test 任务
- 运行环境：Ubuntu latest
- Python版本：3.9
- 执行步骤：代码检出 → 环境设置 → 依赖安装 → 语法检查 → 环境变量验证

### 2. Deploy 任务
- 触发条件：main分支推送且test任务成功
- 执行步骤：创建部署包 → 生成说明文档 → 上传artifact
- 发布功能：基于git tag自动创建Release

## 配置文件位置

工作流配置文件位于：`.github/workflows/main.yml`

## 触发条件

### 自动触发
- `push` 到 main 分支
- `pull_request` 到 main 分支

### 手动触发
- 在 GitHub Actions 页面手动运行工作流

## 环境变量配置

### 仓库级别 Secrets
在 GitHub 仓库 Settings → Secrets and variables → Actions 中配置：

| 变量名 | 说明 | 获取方式 | 必填 |
|--------|------|----------|------|
| `FEISHU_APP_ID` | 飞书应用ID | [飞书应用管理](https://open.feishu.cn/app) | 是 |
| `FEISHU_APP_SECRET` | 飞书应用密钥 | [飞书应用管理](https://open.feishu.cn/app) | 是 |
| `FEISHU_VERIFICATION_TOKEN` | 飞书验证令牌 | [飞书应用管理](https://open.feishu.cn/app) | 是 |
| `FEISHU_ENCRYPT_KEY` | 飞书加密密钥 | [飞书应用管理](https://open.feishu.cn/app) | 是 |
| `FEISHU_WEBHOOK_URL` | Cookie检查通知webhook | [飞书机器人配置](https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot) | 是 |
| `BITABLE_APP_TOKEN` | 多维表格应用token | [飞书多维表格集成](https://open.feishu.cn/document/server-docs/docs/bitable-v1/notification) | 是 |
| `BITABLE_TABLE_ID` | 多维表格ID | [飞书多维表格集成](https://open.feishu.cn/document/server-docs/docs/bitable-v1/notification) | 是 |
| `COMPANY_ID` | 公司ID | 从觅智网后台获取 | 是 |

### 测试环境变量
测试使用的环境变量在 `.env.test` 文件中配置：
```env
# 飞书应用配置
FEISHU_APP_ID=test_app_id
FEISHU_APP_SECRET=test_app_secret
FEISHU_VERIFICATION_TOKEN=test_token
FEISHU_ENCRYPT_KEY=test_key

# Cookie检查通知配置
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/test_webhook_key

# 多维表格配置（用于记录操作日志）
BITABLE_APP_TOKEN=test_bitable_app_token
BITABLE_TABLE_ID=test_bitable_table_id

# 企业配置
COMPANY_ID=12345

# HAR文件路径
HAR_FILE=data/cookie.har

# Cookie检查配置
COOKIE_CHECK_INTERVAL=3600  # 检查间隔（秒），默认1小时
```

## 工作流详细步骤

### Test 任务步骤
1. **Checkout**: 检出代码
2. **Setup Python**: 设置Python 3.9环境
3. **Install dependencies**: 安装项目依赖
4. **Lint with flake8**: 代码语法检查
5. **Verify environment setup**: 环境变量验证

### Deploy 任务步骤
1. **Create deployment package**: 创建包含所有必要文件的tar包
2. **Generate deployment guide**: 生成部署说明文档
3. **Upload artifact**: 上传部署包为artifact
4. **Create Release**: 检测到git tag时自动创建Release

## 自定义配置

### 修改Python版本
编辑 `.github/workflows/main.yml` 中的：
```yaml
with:
  python-version: '3.9'  # 修改为需要的版本
```

### 添加新的测试步骤
在工作文件中添加新的job或step：
```yaml
- name: Run custom tests
  run: python -m pytest tests/
```

### 修改触发条件
调整 `on` 部分的配置：
```yaml
on:
  push:
    branches: [ main, develop ]  # 添加更多分支
  pull_request:
    branches: [ main ]
  workflow_dispatch:  # 启用手动触发
```

## 故障排除

### 常见问题

1. **工作流运行失败**
   - 检查 `.github/workflows/main.yml` 语法
   - 确认所有必要的Secrets已配置

2. **环境变量验证失败**
   - 确认 `.env.test` 文件存在且格式正确

3. **依赖安装失败**
   - 检查 `requirements.txt` 文件格式

4. **部署包创建失败**
   - 确认所有需要打包的文件都存在

### 日志查看
在 GitHub Actions 页面点击具体的工作流运行，可以查看详细的执行日志。

## 最佳实践

1. **定期检查工作流**：确保自动化流程正常工作
2. **更新依赖**：定期更新 `requirements.txt` 中的包版本
3. **测试覆盖**：添加更多的自动化测试用例
4. **监控报警**：设置工作流失败的通知机制

## 版本历史

- 2024-01-01: 初始版本创建
- 2024-01-20: 添加环境变量验证步骤
- 2024-02-01: 优化部署包生成逻辑
- 2024-02-15: 添加Release自动创建功能