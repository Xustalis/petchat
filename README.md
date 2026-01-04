# pet-chat



## 核心特性

### 1. 情绪宠物系统 

* **实时氛围感知**：AI 每 5 条消息分析一次对话的整体情绪趋势（平和、愉快、紧张、消极），而非单一立场。
* **拟物化交互**：采用 iOS 控制中心风格的轻拟物动画，宠物通过表情变化、呼吸浮动及眨眼动作实时反馈聊天氛围。

### 2. 智能记忆与提炼 (Memory Extraction)

* **结构化提炼**：自动从海量对话中提取“共同事件”、“明确约定”及“长期话题”。
* **本地化存储**：所有记忆摘要均加密存储于本地 SQLite 数据库，用户可随时查看或一键清空。

### 3. 决策与计划辅助 (AI Suggestion) 

* **意图识别触发**：当识别到时间（如“下周”）或行为（如“计划”）相关关键词时，自动在侧边栏生成行程建议或执行清单。
* **交互式采用**：支持将 AI 建议一键填入输入框，减少手动输入成本。

### 4. 现代化 UI/UX 设计 

* **iOS 风格暗黑主题**：基于 `UI_DESIGN_SPEC.md` 规范，采用 10-18px 中等圆角、暗色 iOS 配色方案。
* **响应式布局**：左侧为核心聊天与宠物区，右侧为建议与记忆 Tab 面板，支持伸缩调节。

---

## 🛠 技术栈

* **核心语言**：Python 3.10+
* **GUI 框架**：PyQt6
* **网络通信**：TCP Socket P2P 协议 (Host-Guest 模式)
* **AI 服务**：OpenAI API 兼容协议 
* **数据管理**：SQLAlchemy + SQLite

---

## 项目结构

```text
petchat/
├── main.py              # 应用入口，负责生命周期与 AI 触发逻辑控制
├── core/                # 核心功能模块
│   ├── network.py       # 线程安全的 P2P 通信实现
│   ├── ai_service.py    # LLM 情绪分析、记忆提取与建议生成逻辑
│   ├── database.py      # SQLite 数据库持久化管理
│   └── config_manager.py # 基于 JSON 的运行时配置管理器
├── ui/                  # UI 组件模块
│   ├── pet_widget.py    # 包含绘制逻辑与动画的情绪宠物组件
│   ├── memory_viewer.py # 记忆查看与管理卡片
│   ├── theme.py         # 统一的主题颜色与 QSS 样式定义
│   └── api_config_dialog.py # API 运行时配置交互对话框
└── config/              # 静态配置目录
    └── settings.py      # 系统默认参数与分析频率配置

```

---

## 快速开始

### 1. 环境准备

项目提供了自动化的环境配置脚本：

* **Windows**: 运行 `setup_venv.bat`
* **Linux/Mac**: 运行 `source setup_venv.sh`

或手动安装：

```bash
pip install -r requirements.txt

```

### 2. 配置 AI API (仅 Host 端需做此配置)

启动应用后，通过菜单栏 `文件 -> API 配置` (或 `Ctrl+K`) 配置 API Key。配置将安全地存储在本地 `config.json` 中。

### 3. 运行应用

* **房主模式 (Host)**: 负责创建房间并提供 AI 分析服务。
```bash
python main.py --host --port 8888

```


* **访客模式 (Guest)**: 连接到房主 IP 即可开始聊天。
```bash
python main.py --guest --host-ip <HOST_IP> --port 8888

```



---

## 打包分发

本项目支持打包为独立的单文件可执行程序：

* **PyInstaller (推荐)**：
```bash
pyinstaller build.spec

```


* **Nuitka**：
```bash
python build_exe.py nuitka

```

生成的程序将位于 `dist/` 目录下。

---

## 隐私与安全

* **数据本地化**：对话内容与记忆摘要仅存储于本地 `petchat.db` 数据库。
* **透明 AI 请求**：AI 仅在预设的分析间隔发送必要的匿名上下文片段。

---

## 开源协议

本项目采用 [MIT License](https://www.google.com/search?q=%23) 协议。