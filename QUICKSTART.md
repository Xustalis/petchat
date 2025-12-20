# 快速开始指南

## 1. 环境准备

### Windows

```bash
# 方法1：使用自动脚本（推荐）
setup_venv.bat

# 方法2：手动创建
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Linux/Mac

```bash
# 方法1：使用自动脚本
chmod +x setup_venv.sh
./setup_venv.sh

# 方法2：手动创建
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 2. 运行应用

### Host端（服务提供者）

```bash
# 激活虚拟环境（如果未激活）
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# 启动Host
python main.py --host --port 8888
```

**首次运行**：
- 会自动弹出API配置对话框
- 输入你的OpenAI API Key
- 可选：配置API Base URL（如使用兼容API）

### Guest端（客户端）

```bash
# 激活虚拟环境
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# 连接Host（替换<HOST_IP>为实际IP）
python main.py --guest --host-ip <HOST_IP> --port 8888
```

## 3. 使用功能

### 基础聊天
- 在输入框输入消息，按回车或点击"发送"
- 消息会自动保存到本地数据库

### 情绪宠物
- 左上角的宠物会根据对话氛围自动变化
- 每5条消息自动更新一次情绪

### AI建议
- **自动触发**：当对话涉及计划、安排时，右侧会自动显示建议
- **手动触发**：输入 `/ai` 命令主动请求建议
- **采用建议**：点击"采用建议"按钮，内容会填入输入框

### 查看记忆
- 点击右侧"记忆"标签页
- 查看AI提取的关键信息
- 可以清空所有记忆

### 配置API（Host端）
- 菜单栏：`文件 -> API 配置` 或按 `Ctrl+K`
- 配置会保存在 `config.json` 文件中

## 4. 打包为exe

### 使用PyInstaller（推荐）

```bash
# 安装PyInstaller
pip install pyinstaller

# 打包
pyinstaller build.spec

# 输出文件在 dist/pet-chat.exe
```

### 使用Nuitka

```bash
# 安装Nuitka
pip install nuitka

# 打包
python build_exe.py nuitka

# 输出文件在 dist/pet-chat.exe
```

详细说明请参考 [BUILD.md](BUILD.md)

## 5. 项目结构

```
petchat/
├── main.py                    # 程序入口
├── core/                      # 核心模块
│   ├── network.py            # P2P网络通信
│   ├── database.py           # 数据库管理
│   ├── ai_service.py         # AI服务集成
│   └── config_manager.py     # 配置管理
├── ui/                        # UI模块
│   ├── main_window.py        # 主窗口
│   ├── pet_widget.py         # 宠物组件
│   ├── suggestion_panel.py   # 建议面板
│   ├── memory_viewer.py      # 记忆查看器
│   └── api_config_dialog.py  # API配置对话框
├── config/                    # 配置
│   └── settings.py           # 设置
├── venv/                      # 虚拟环境（已创建）
├── requirements.txt           # 依赖列表
├── build.spec                # PyInstaller配置
├── build_exe.py              # 打包脚本
└── config.json               # 运行时配置（自动生成）
```

## 6. 常见问题

### Q: API Key在哪里配置？
A: Host端首次启动会自动弹出配置对话框，或通过菜单栏 `文件 -> API 配置` 配置。

### Q: 配置保存在哪里？
A: API配置保存在 `config.json`，聊天记录保存在 `petchat.db`。

### Q: Guest端需要配置API Key吗？
A: 不需要，只有Host端需要配置。

### Q: 如何打包？
A: 参考 [BUILD.md](BUILD.md)，推荐使用PyInstaller。

### Q: 打包后文件很大？
A: 正常，PyQt6依赖较大，单文件exe约50-100MB。

## 7. 快捷键

- `Ctrl+K`: 打开API配置（Host端）
- `Ctrl+M`: 查看记忆
- `Ctrl+Q`: 退出应用
- `Enter`: 发送消息

## 8. 下一步

- 阅读 [README.md](README.md) 了解详细功能
- 阅读 [USAGE.md](USAGE.md) 了解使用说明
- 阅读 [BUILD.md](BUILD.md) 了解打包详情
- 阅读 [CHANGELOG.md](CHANGELOG.md) 了解更新内容

