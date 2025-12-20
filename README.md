# pet-chat

一个探索 AI 作为"第三方观察者"介入聊天场景的实验性项目。

## 功能特性

- 🔄 P2P 点对点聊天（Host-Guest 模式）
- 🐾 情绪宠物系统（实时反映聊天氛围）
- 🧠 对话记忆与关键信息提取
- 💡 决策与计划辅助系统

## 技术栈

- Python 3.10+
- PyQt6 (UI框架)
- OpenAI API (AI服务)
- SQLite (本地存储)

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境变量

创建 `.env` 文件：

```
OPENAI_API_KEY=your_api_key_here
OPENAI_API_BASE=https://api.openai.com/v1  # 可选，默认为OpenAI官方API
```

### 运行

#### Host 端（需要配置API Key）

```bash
python main.py --host --port 8888
```

#### Guest 端（连接Host）

```bash
python main.py --guest --host-ip <HOST_IP> --port 8888
```

## 项目结构

```
petchat/
├── main.py              # 程序入口
├── core/                # 核心模块
│   ├── network.py       # P2P网络通信
│   ├── database.py      # 数据库管理
│   └── ai_service.py    # AI服务集成
├── ui/                  # UI模块
│   ├── main_window.py   # 主窗口
│   ├── pet_widget.py    # 宠物组件
│   └── suggestion_panel.py  # 建议面板
└── config/              # 配置文件
    └── settings.py      # 配置管理
```

## 使用说明

### Host 端

1. 配置 OpenAI API Key
2. 启动服务：`python main.py --host --port 8888`
3. 将显示的IP地址和端口告知Guest
4. 开始聊天

### Guest 端

1. 使用Host提供的IP和端口连接：`python main.py --guest --host-ip <IP> --port <PORT>`
2. 开始聊天


## 打包为可执行文件

### 使用 PyInstaller

```bash
pip install pyinstaller
pyinstaller build.spec
```

### 使用 Nuitka

```bash
pip install nuitka
python build_exe.py nuitka
```

详细说明请参考 [BUILD.md](BUILD.md)

## 注意事项

- 本项目为实验性项目，不追求商业化与大规模稳定性
- 聊天记录仅保存在本地
- 适合熟人（朋友）小规模使用
- API Key通过运行时配置，不会硬编码

