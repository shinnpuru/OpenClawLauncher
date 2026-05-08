
<p align="center">
	<img src="teaser.png" alt="OpenClaw Launcher Logo"/>
</p>

<h1 align="center">OpenClaw Launcher</h1>

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/UI-PySide6-41CD52?logo=qt&logoColor=white)
![Platforms](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux%20%7C%20Windows-555)
![License](https://img.shields.io/badge/License-MIT-blue)
[![Build and Release PyInstaller](https://github.com/shinnpuru/OpenClawLauncher/actions/workflows/release-pyinstaller.yml/badge.svg)](https://github.com/shinnpuru/OpenClawLauncher/actions/workflows/release-pyinstaller.yml)

<p align="center">中文 | <a href="README.md">English</a></p>

## 项目目的

`OpenClaw Launcher` 是一个基于 PySide6 的桌面启动器，用于以图形化方式管理 [OpenClaw](https://github.com/openclaw/openclaw) 的安装与运行流程。

它的核心目标是：

- 将原本依赖命令行的安装/启动流程可视化。
- 降低多实例管理、依赖检查与故障排查的门槛。
- 提供更清晰的运行状态、日志和备份入口。

## 核心功能

- **一键上手**：首次使用可通过“快速上手”面板一键配置。
- **实例管理**：创建、启动、停止、删除实例，支持版本更新前自动备份、打开实例目录、启动实例 CLI。
- **运行时管理**：在“依赖检查”面板中管理 OpenClaw / Node.js（必需）与 Python / uv（可选）版本，支持下载与切换默认版本。
- **频道配置**：在“频道配置”面板按实例维护 Discord / Telegram / Feishu / DingTalk / QQ 等频道参数，保存时可自动处理实例停止检查。
- **本地模型服务**：在“LlamaCPP”面板配置并启动本地 GGUF 推理服务，支持端口、GPU 层数、额外参数与 API 连通性测试。
- **模型切换**：在“模型切换”面板一键切换在线/本地模型提供商（如 OpenAI、DeepSeek、Moonshot、Ollama、Llama.cpp），自动更新实例配置。
- **插件管理**：在“插件管理”面板按实例安装/卸载插件，支持推荐插件一键安装。
- **备份与恢复**：将实例打包为 zip 备份并恢复，恢复后自动尝试重装依赖。
- **日志查看**：按实例实时查看日志、清空日志、用系统默认程序打开日志文件。
- **高级设置**：支持托盘行为、开机启动、更新检查、源地址配置及故障排除清理工具。

## 快速开始

### 1) 下载

前往仓库的 [Releases](https://github.com/shinnpuru/OpenClawLauncher/releases) 页面，下载与你系统匹配的安装包（macOS / Windows）。

### 2) 安装

按系统提示完成安装：

- macOS：将 `.app` 包放入应用程序文件夹，然后双击打开。
- Windows：双击运行 `.exe` 包。

### 3) 使用

建议先进入“快速上手”面板完成首次初始化。教程详见[Wiki](https://github.com/shinnpuru/OpenClawLauncher/wiki)。

### 4) 配置与管理

- 在“依赖检查”面板确认 Node.js / OpenClaw（必需）以及 Python / uv（可选）。
- 在“本地模型”和“模型切换”面板配置本地或在线模型。
- 在“频道配置”面板配置机器人频道参数。
- 在“实例管理”面板创建并启动实例，按需更新版本或打开目录/CLI。
- 在“插件管理”面板安装所需插件。
- 在“日志查看”和“备份管理”面板进行运行排查与数据保护。
- 在“高级设置”面板调整托盘、开机启动、源地址和清理策略。

<details>
<summary>开发者说明</summary>

### 开发环境

- Python 3.10+
- Node.js v22+

### 本地运行

本项目使用 [uv](https://github.com/astral-sh/uv) 管理依赖：

```bash
uv sync
uv run python src/openclaw_launcher/main.py
```

### 本地打包

```bash
uv add --dev pyinstaller
uv run pyinstaller app.spec
# uv run pyinstaller app-macos.spec
```

输出目录：`dist/`

</details>

## License

MIT
