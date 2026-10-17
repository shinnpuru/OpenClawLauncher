<p align="center">
	<img src="teaser.png" alt="OpenClaw Launcher Logo" width="200"/>
</p>

<h1 align="center">OpenClaw Launcher</h1>

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/UI-PySide6-41CD52?logo=qt&logoColor=white)
![Platforms](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-555)
![License](https://img.shields.io/badge/License-MIT-blue)
[![Build and Release PyInstaller](https://github.com/shinnpuru/OpenClawLauncher/actions/workflows/release-pyinstaller.yml/badge.svg)](https://github.com/shinnpuru/OpenClawLauncher/actions/workflows/release-pyinstaller.yml)

<p align="center">中文 | <a href="README.en.md">English</a></p>

`OpenClaw Launcher` 是一个基于 PySide6 的桌面应用，用图形化流程帮助你安装、配置和运行 [OpenClaw](https://github.com/openclaw/openclaw)。

## 核心功能

- **快速上手**：一键安装必需运行时、创建默认的 `openclaw` 实例并启动。快速上手页还提供启动/停止、打开 WebUI、打开命令行、打开实例配置文件夹和原地更新 OpenClaw 等快捷操作。
- **运行时版本管理**：下载、选择和删除 OpenClaw 与 Node.js 版本，也可管理可选的 Python 和 uv；支持刷新可用的 OpenClaw 版本，删除当前默认版本后会自动选择新的默认版本。
- **频道配置**：按实例配置 Discord、Telegram、飞书、钉钉、QQ 和微信。依赖插件的频道若缺少插件，可直接在频道页安装；微信登录可直接打开实例 CLI。
- **模型切换**：配置兼容 OpenAI API 的在线或本地提供商，包括 OpenAI、Moonshot、DeepSeek、Gemini、Grok、GLM、通义千问/DashScope、豆包、Ollama、llama.cpp 和自定义端点；应用前可测试 API 连通性。
- **本地模型服务**：使用内置的 llama.cpp 服务运行 GGUF 模型，可设置模型、多模态投影文件、端口、GPU 层数和额外参数，并查看输出及测试 API。
- **插件管理**：按实例检测已安装插件，通过 npm 包名安装或卸载插件；若卸载后仍有残留文件，可快捷打开对应目录进行手动清理。
- **实例环境变量**：按实例添加、编辑和删除环境变量。
- **备份、恢复与日志**：创建 zip 备份，恢复实例并重新安装依赖；实时查看启动器和实例日志、清空选中的日志，或用系统默认程序打开日志文件。
- **桌面与高级设置**：支持中英文切换以及浅色、深色、跟随系统主题；可配置托盘行为、启动器开机启动、最小化启动、自动启动实例或 llama.cpp、更新检查、下载镜像和故障排除清理操作。

## 快速开始

### 1. 下载并打开启动器

前往 [最新 Release](https://github.com/shinnpuru/OpenClawLauncher/releases/latest)，在 **Assets** 中按系统和显卡选择压缩包（`<版本号>` 以发布页为准）：

| 系统 | 文件名 | 说明 |
| --- | --- | --- |
| Windows x64 | `openclaw-launcher-<版本号>-windows.zip` | 内置 Vulkan 版 llama.cpp |
| Windows x64（NVIDIA 显卡） | `openclaw-launcher-<版本号>-windows-cuda.zip` | 内置 CUDA 12.4 版 llama.cpp |
| macOS Apple Silicon | `openclaw-launcher-<版本号>-macos.app.zip` | 适用于 Apple 芯片 Mac（`arm64`） |

- **Windows**：完整解压压缩包，进入 `openclaw-launcher` 文件夹，运行 `openclaw-launcher.exe`。请保留同目录下的依赖文件。
- **macOS**：解压后将 `openclaw-launcher.app` 移入“应用程序”文件夹并打开。

使用发布包无需预先安装 Python、Node.js 或 uv。首次初始化需要联网下载 Node.js、OpenClaw 及相关依赖；使用本地模型时，还需自行准备 GGUF 模型文件。

### 2. 一键初始化

进入“快速上手”，点击 **一键安装并启动 OpenClaw**。启动器会依次：

1. 检查并安装最新兼容的 Node.js 运行时。
2. 下载 OpenClaw 运行时（尚未设置默认版本时）。
3. 创建默认的 `openclaw` 实例，安装依赖并完成初始化。
4. 启动 OpenClaw，默认网关端口为 `18789`。

首次安装可能较慢，请等待进度完成。安装期间，WebUI、命令行、文件夹和更新按钮暂不可用；安装完成后自动启用。

### 3. 配置模型

实例启动后，还需配置可用的模型才能进行对话。新实例默认指向本地 llama.cpp 服务 `http://127.0.0.1:8989/v1`，请选择以下一种方式：

- **在线模型**：进入“模型切换”，选择 `openclaw` 实例和模型提供商，填写 API Key、模型 ID，按需调整 API 地址；点击“测试 API”，确认连接后点击“应用模型切换”。
- **本地模型**：进入“本地模型”，选择 GGUF 模型文件，按需选择图像模型文件（mmproj），配置端口与 GPU 加载层数，点击“启动服务器”，再点击“测试 API”。使用默认端口 `8989` 时可沿用实例的默认模型配置；若更改端口或改用其他本地服务，请到“模型切换”中应用对应地址。

应用模型切换会停止正在运行的实例；配置完成后，请回到“快速上手”点击“启动 OpenClaw”。

### 4. 打开 WebUI，按需接入频道

确认 OpenClaw 和所选模型服务正在运行，然后回到“快速上手”，点击 **打开 WebUI** 开始对话。此按钮会打开带有当前实例网关 Token 的地址，无需手动拼接。

需要接入 Discord、Telegram、飞书、钉钉、QQ 或微信时，进入“频道配置”，选择实例并按页面提示填写凭据或登录；缺少频道插件时，可直接在该页安装。

### 5. 日常使用与更新

- **启动 / 停止**：在“快速上手”使用主按钮控制默认实例，也可在“实例管理”中操作其他实例。
- **打开命令行 / 文件夹**：使用快捷按钮打开实例命令行或 `.openclaw` 配置目录。
- **更新 OpenClaw**：先在“依赖检查”中刷新 OpenClaw 版本列表、下载目标版本并设为默认版本，再回到“快速上手”点击“更新版本”并确认。该操作会将默认运行时应用到实例；若实例正在运行，启动器会先提示停止。更新完成后再启动实例。
- **管理运行时与扩展**：在“依赖检查”中下载、选择或删除运行时版本，在“插件管理”和“环境变量”中维护实例扩展及变量。
- **备份与排错**：在“备份管理”中备份或恢复实例，在“日志查看”中查看安装及运行日志；下载缓慢或失败时，可在“高级设置”中检查下载镜像设置后重试。

更多使用说明请参阅项目 [Wiki](https://github.com/shinnpuru/OpenClawLauncher/wiki)。

<details>
<summary>开发者说明</summary>

### 环境要求

- Python 3.10+
- Node.js：由启动器管理，当前支持 `>=24.16.0 <25` 或 `>=26.1.0`
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
