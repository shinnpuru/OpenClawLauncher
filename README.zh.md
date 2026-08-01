<p align="center">
	<img src="teaser.png" alt="OpenClaw Launcher Logo" width="200"/>
</p>

<h1 align="center">OpenClaw Launcher</h1>

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/UI-PySide6-41CD52?logo=qt&logoColor=white)
![Platforms](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-555)
![License](https://img.shields.io/badge/License-MIT-blue)
[![Build and Release PyInstaller](https://github.com/shinnpuru/OpenClawLauncher/actions/workflows/release-pyinstaller.yml/badge.svg)](https://github.com/shinnpuru/OpenClawLauncher/actions/workflows/release-pyinstaller.yml)

<p align="center">中文 | <a href="README.md">English</a></p>

`OpenClaw Launcher` 是一个基于 PySide6 的桌面应用，用图形化流程帮助你安装、配置和运行 [OpenClaw](https://github.com/openclaw/openclaw)。

## 核心功能

- **快速上手**：一键安装必需运行时、创建默认的 `openclaw` 实例并启动。快速上手页还提供启动/停止、打开 WebUI、打开 CLI、查看文档和原地更新 OpenClaw 等快捷操作。
- **运行时版本管理**：下载、选择和删除 OpenClaw 与 Node.js 版本，也可管理可选的 Python 和 uv；支持刷新可用的 OpenClaw 版本，删除当前默认版本后会自动选择新的默认版本。
- **频道配置**：按实例配置 Discord、Telegram、飞书、钉钉、QQ 和微信。依赖插件的频道若缺少插件，可直接在频道页安装；微信登录可直接打开实例 CLI。
- **模型切换**：配置兼容 OpenAI API 的在线或本地提供商，包括 OpenAI、Moonshot、DeepSeek、Gemini、Grok、GLM、通义千问/DashScope、豆包、Ollama、llama.cpp 和自定义端点；应用前可测试 API 连通性。
- **本地模型服务**：使用内置的 llama.cpp 服务运行 GGUF 模型，可设置模型、多模态投影文件、端口、GPU 层数和额外参数，并查看输出及测试 API。
- **插件管理**：按实例检测已安装插件，通过 npm 包名安装或卸载插件；若卸载后仍有残留文件，可快捷打开对应目录进行手动清理。
- **实例环境变量**：按实例添加、编辑和删除环境变量。
- **备份、恢复与日志**：创建 zip 备份，恢复实例并重新安装依赖；实时查看启动器和实例日志、清空选中的日志，或用系统默认程序打开日志文件。
- **桌面与高级设置**：支持中英文切换以及浅色、深色、跟随系统主题；可配置托盘行为、启动器开机启动、最小化启动、自动启动实例或 llama.cpp、更新检查、下载镜像和故障排除清理操作。

## 快速开始

### 1. 下载

前往 [Releases](https://github.com/shinnpuru/OpenClawLauncher/releases) 下载最新安装包：

- Windows x64：提供 Vulkan 和 CUDA 12.4 构建。
- macOS：提供 Apple Silicon（`arm64`）构建。

### 2. 安装

- Windows：解压下载的压缩包，然后运行启动器程序。
- macOS：解压后将 `.app` 移入“应用程序”文件夹并打开。

### 3. 初始化并运行 OpenClaw

进入“快速上手”，点击主操作按钮。启动器会下载必需的 Node.js 和 OpenClaw 运行时、创建默认的 `openclaw` 实例并启动它。初始化完成后，同一个按钮用于启动或停止 OpenClaw。

下方快捷按钮可打开 WebUI 或 CLI、更新 OpenClaw，以及访问官方文档。更多使用说明请参阅项目 [Wiki](https://github.com/shinnpuru/OpenClawLauncher/wiki)。

### 4. 配置

- 在“依赖检查”中选择运行时版本，或删除不再使用的版本。
- 在“频道配置”中填写凭据；缺少频道插件时，可按提示直接安装。
- 在“模型切换”中选择在线提供商，或在“LlamaCPP”中配置本地 GGUF 模型。
- 在“实例环境变量”和“插件管理”中维护实例变量与扩展。
- 使用“备份管理”和“日志查看”保护数据、排查问题。
- 在“高级设置”中调整启动行为、镜像、更新检查和清理选项。

<details>
<summary>开发者说明</summary>

### 环境要求

- Python 3.10+
- Node.js 22+
- [uv](https://github.com/astral-sh/uv)

### 本地运行

```bash
uv sync
uv run python src/openclaw_launcher/main.py
```

### 本地构建

```bash
uv sync --dev
# Windows
uv run pyinstaller app.spec
# macOS
uv run pyinstaller app-macos.spec
```

构建产物位于 `dist/`。

</details>

## License

MIT
