# 更新日志

## v2.1 - 统一 AI 入口架构 (2026-01-21)

### 重大变更

1. **统一 AI Provider 接口**
   - 新增 `core/providers/factory.py` 工厂模块
   - `AIService` 现在通过 Provider 抽象层调用 AI，不再直接使用 HTTP 请求
   - 支持自动检测 Provider 类型：`gemini-*` 模型使用 GeminiProvider，其他使用 OpenAI 兼容 Provider

2. **Provider 自动切换**
   - 根据模型名前缀自动选择 Provider
   - 支持显式指定 `provider_type` 参数覆盖自动检测
   - 业务逻辑代码无需关心底层 Provider 差异

### 新增测试

1. **Provider Factory 测试**
   - 自动检测逻辑单元测试
   - Provider 实例化测试
   - Gemini Provider Mock 测试

### 技术改进

1. 移除 `ai_service.py` 中的直接 HTTP 请求代码，改用 Provider 模式
2. 所有 AI 请求现在包含重试机制（指数退避）
3. 统一的日志记录格式

---

## v2.0 - Client-Server 架构版本 (2026-01-18)

### 重大变更

1. **架构重构：P2P → Client-Server**
   - 移除 Host/Guest P2P 模式
   - 新增独立服务器 `server.py`
   - 客户端连接服务器进行通信
   - 支持多客户端同时在线

2. **网络层完全重写**
   - 简化协议实现，内置到 `server.py` 和 `core/network.py`
   - 移除 `core/protocol.py`（协议代码已内联）
   - 消息广播自动排除发送者
   - 更可靠的连接管理

3. **信号系统修复**
   - 修复 `PetChatApp` 缺失 `super().__init__()` 的关键 Bug
   - 重构信号连接，确保跨线程通信正常

### 新增功能

1. **用户在线状态**
   - 实时显示在线用户列表
   - 用户加入/离开通知
   - 支持点击用户发起私聊

2. **改进的连接体验**
   - 启动时提示输入服务器 IP
   - 支持命令行参数 `--server-ip`
   - 连接状态实时显示

### 改进

1. **代码清理**
   - 移除所有 P2P/Host/Guest 相关代码
   - 移除未使用的 AI 网络信号
   - 简化网络管理器 API

2. **文档更新**
   - 更新 README.md 反映新架构
   - 更新 BUILD.md 打包指南
   - 更新 CHANGELOG.md

---

## v1.0 - MVP 版本

### 功能

1. **运行时 API 配置**
   - API 配置对话框
   - 支持运行时配置 API Key 和 API Base URL
   - 配置保存在 `config.json`

2. **记忆查看和管理**
   - 记忆查看器组件
   - 支持查看和清空记忆
   - 记忆按类别显示

3. **情绪宠物系统**
   - 情绪变化动画
   - 空闲时循环动画
   - 现代化 UI 设计

4. **现代化 UI**
   - iOS 风格暗黑主题
   - 圆润的边框和阴影
   - 标签页式布局

5. **打包支持**
   - PyInstaller 打包配置
   - Nuitka 打包支持
