<p align="center">
	<img src="teaser.png" alt="OpenClaw Launcher Logo" width="200"/>
</p>

<h1 align="center">OpenClaw Launcher</h1>

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/UI-PySide6-41CD52?logo=qt&logoColor=white)
![Platforms](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-555)
![License](https://img.shields.io/badge/License-MIT-blue)
[![Build and Release PyInstaller](https://github.com/shinnpuru/OpenClawLauncher/actions/workflows/release-pyinstaller.yml/badge.svg)](https://github.com/shinnpuru/OpenClawLauncher/actions/workflows/release-pyinstaller.yml)

<p align="center">English | <a href="README.zh.md">中文</a></p>

`OpenClaw Launcher` is a PySide6 desktop application that provides a graphical workflow for installing, configuring, and running [OpenClaw](https://github.com/openclaw/openclaw).

## Key Features

- **Guided onboarding**: Install the required runtimes, create the default `openclaw` instance, and start it in one click. The Onboard panel also provides start/stop, WebUI, CLI, documentation, and in-place OpenClaw update actions.
- **Runtime version management**: Download, select, and remove OpenClaw and Node.js versions, plus optional Python and uv versions. The launcher can refresh the available OpenClaw releases and automatically select another default after the current default is removed.
- **Channel configuration**: Configure Discord, Telegram, Feishu, DingTalk, QQ, and Weixin for each instance. Plugin-backed channels offer an install action when their plugin is missing, and Weixin login opens directly in the instance CLI.
- **Model switching**: Configure OpenAI-compatible online and local providers—including OpenAI, Moonshot, DeepSeek, Gemini, Grok, GLM, Qwen/DashScope, Doubao, Ollama, llama.cpp, and custom endpoints—and test the API before applying it to an instance.
- **Local model serving**: Run GGUF models with the bundled llama.cpp server; configure the model, optional multimodal projector, port, GPU layers, and extra arguments, then inspect output and test API connectivity.
- **Plugin management**: Detect installed plugins and install or uninstall npm plugin packages per instance. If an uninstall leaves files behind, the launcher provides a direct folder shortcut for manual cleanup.
- **Instance environment variables**: Add, edit, and remove environment variables stored for each instance.
- **Backup, restore, and logs**: Create zip backups, restore an instance with dependency reinstallation, follow launcher and instance logs, clear a selected log, or open it with the system default application.
- **Desktop and advanced settings**: Switch between Chinese and English and light/dark/system themes; configure tray behavior, launcher auto-start, minimized startup, automatic instance or llama.cpp startup, update checks, download mirrors, and troubleshooting cleanup actions.

## Quick Start

### 1. Download

Download the latest package from [Releases](https://github.com/shinnpuru/OpenClawLauncher/releases):

- Windows x64: Vulkan and CUDA 12.4 builds are available.
- macOS: Apple Silicon (`arm64`) build.

### 2. Install

- Windows: extract the downloaded archive and run the launcher executable.
- macOS: extract the archive, move the `.app` to Applications, and open it.

### 3. Initialize and run OpenClaw

Open **Onboard** and click the main one-click button. The launcher downloads the required Node.js and OpenClaw runtimes, creates the default `openclaw` instance, and starts it. The same button starts or stops OpenClaw after initialization.

Use the shortcuts below it to open WebUI or CLI, update OpenClaw, or visit the official documentation. See the project [Wiki](https://github.com/shinnpuru/OpenClawLauncher/wiki) for more usage guides.

### 4. Configure

- Choose runtime versions or remove unused ones in **Dependencies**.
- Set credentials in **Channels**; install a required channel plugin there when prompted.
- Choose an online provider in **Model Switch**, or configure a local GGUF model in **LlamaCPP**.
- Maintain per-instance variables in **Environment Variables** and extensions in **Plugins**.
- Use **Backups** and **Logs** for data protection and troubleshooting.
- Adjust startup behavior, mirrors, update checks, and cleanup options in **Advanced**.

<details>
<summary>Developer Notes</summary>

### Requirements

- Python 3.10+
- Node.js 22+
- [uv](https://github.com/astral-sh/uv)

### Run locally

```bash
uv sync
uv run python src/openclaw_launcher/main.py
```

### Build locally

```bash
uv sync --dev
# Windows
uv run pyinstaller app.spec
# macOS
uv run pyinstaller app-macos.spec
```

Build output is written to `dist/`.

</details>

## License

MIT
