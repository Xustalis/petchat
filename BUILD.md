# 打包指南

## 使用 PyInstaller（推荐，简单）

### 1. 安装 PyInstaller

```bash
pip install pyinstaller
```

### 2. 打包

```bash
# 方法1：使用spec文件（推荐）
pyinstaller build.spec

# 方法2：使用命令行
pyinstaller --name=pet-chat --onefile --windowed --add-data="config;config" main.py

# 方法3：使用构建脚本
python build_exe.py pyinstaller
```

### 3. 输出

打包完成后，可执行文件位于 `dist/pet-chat.exe`

## 使用 Nuitka（PRD指定）

### 1. 安装 Nuitka

```bash
pip install nuitka
```

### 2. 打包

```bash
# 使用构建脚本
python build_exe.py nuitka

# 或直接使用命令
python -m nuitka --standalone --onefile --windows-disable-console --enable-plugin=pyqt6 main.py
```

### 3. 输出

打包完成后，可执行文件位于 `dist/pet-chat.exe`

## 注意事项

1. **依赖问题**：
   - 确保所有依赖都已安装
   - PyQt6 可能需要额外配置

2. **文件大小**：
   - PyInstaller: 约 50-100MB
   - Nuitka: 约 30-80MB

3. **首次运行**：
   - 打包后的exe首次运行可能较慢
   - 需要配置API Key才能使用AI功能

4. **配置文件**：
   - `config.json` 会在exe同目录创建
   - `petchat.db` 会在exe同目录创建

## 测试打包结果

1. 在另一台没有Python环境的Windows机器上测试
2. 确保所有功能正常：
   - Host/Guest连接
   - 消息收发
   - AI功能（需要配置API Key）
   - 记忆查看

## 常见问题

### PyInstaller打包后无法运行

- 检查是否有缺失的DLL
- 尝试添加 `--collect-all=PyQt6`
- 检查控制台错误信息（临时添加 `console=True`）

### Nuitka打包失败

- 确保安装了C++编译器（Visual Studio Build Tools）
- 尝试使用 `--standalone` 模式

