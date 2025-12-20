# pet-chat 使用指南

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置API Key（Host端必需）

创建 `.env` 文件：

```env
OPENAI_API_KEY=your_api_key_here
```

**注意**：只有Host端需要配置API Key。Guest端无需配置。

### 3. 启动应用

#### Host端（服务提供者）

```bash
python main.py --host --port 8888
```

启动后会显示：
- 本地IP地址（用于告知Guest端）
- 端口号

**示例输出**：
```
Host started on 0.0.0.0:8888
Waiting for guest to connect...
```

#### Guest端（客户端）

```bash
python main.py --guest --host-ip <HOST_IP> --port 8888
```

将 `<HOST_IP>` 替换为Host端显示的IP地址。

**示例**：
```bash
python main.py --guest --host-ip 192.168.1.100 --port 8888
```

## 功能说明

### 基础聊天

- 在输入框输入消息，按回车或点击"发送"按钮发送
- 消息会自动保存到本地数据库
- 支持Emoji表情

### 情绪宠物

- 左侧顶部的宠物会根据对话氛围实时变化表情
- 表情类型：
  - 😐 平和/轻松
  - 😊 愉快/兴奋
  - 😰 紧张/焦躁
  - 😞 消极/冲突
- 宠物每5条消息自动更新一次

### AI建议

- **自动触发**：当对话中涉及计划、安排等关键词时，右侧面板会自动显示AI建议
- **手动触发**：输入 `/ai` 命令可主动请求AI建议
- **采用建议**：点击建议卡片上的"采用建议"按钮，建议内容会自动填入输入框

### 记忆提取

- AI会自动从对话中提取关键信息（事件、约定、话题）
- 记忆保存在本地数据库
- 每10条消息自动提取一次

## 注意事项

1. **网络连接**：
   - 确保Host和Guest在同一网络或Host的端口已开放
   - 防火墙可能需要允许端口访问

2. **AI功能**：
   - 只有Host端具有AI功能
   - Guest端只能看到AI分析的结果（宠物状态、建议）

3. **数据存储**：
   - 所有数据保存在本地 `petchat.db` 文件
   - 删除此文件可清除所有聊天记录和记忆

4. **实验性质**：
   - 本项目为实验性项目
   - 情绪识别可能存在误判
   - 适合熟人（朋友）小规模使用

## 故障排查

### 连接失败

- 检查Host端是否已启动
- 检查IP地址和端口是否正确
- 检查防火墙设置
- 确保Host和Guest在同一网络

### AI功能不可用

- 检查 `.env` 文件是否存在且包含有效的API Key
- 检查网络连接（需要访问OpenAI API）
- 查看控制台错误信息

### 情绪识别不准确

- 这是正常现象，情绪识别是概率性的
- 可以通过增加对话内容提高准确度
- 如果持续不准确，可以考虑调整分析的消息数量

## 高级用法

### 自定义端口

```bash
# Host端
python main.py --host --port 9999

# Guest端
python main.py --guest --host-ip <IP> --port 9999
```

### 使用自定义API

在 `.env` 文件中设置：

```env
OPENAI_API_KEY=your_key
OPENAI_API_BASE=https://your-api-endpoint.com/v1
```

## 命令参考

### Host端

```bash
python main.py --host [--port PORT]
```

### Guest端

```bash
python main.py --guest --host-ip IP [--port PORT]
```

### 参数说明

- `--host`: 以Host模式运行（服务端）
- `--guest`: 以Guest模式运行（客户端）
- `--host-ip IP`: Guest模式时，指定Host的IP地址
- `--port PORT`: 端口号（默认：8888）

