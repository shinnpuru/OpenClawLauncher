<p align="center">
	<img src="logo.png" alt="OpenClaw Launcher Logo" width="160" />
</p>

<h1 align="center">OpenClaw Launcher</h1>

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/UI-PySide6-41CD52?logo=qt&logoColor=white)
![Platforms](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux%20%7C%20Windows-555)
![License](https://img.shields.io/badge/License-MIT-blue)
[![Build and Release PyInstaller](https://github.com/shinnpuru/OpenClawLauncher/actions/workflows/release-pyinstaller.yml/badge.svg)](https://github.com/shinnpuru/OpenClawLauncher/actions/workflows/release-pyinstaller.yml)

<p align="center">English | <a href="README.zh.md">中文</a></p>

## Key Features

- **Guided Onboarding**: The Onboard panel now covers a 6-step flow (install dependencies, create instance, configure LlamaCPP/model, configure channels, start instance, open WebUI).
- **Instance Management**: Create/start/stop/delete instances, with optional pre-update backup, open-folder action, and instance CLI launcher.
- **Runtime Management**: Manage OpenClaw / Node.js (required) and Python / uv (optional) in Dependencies, including download and default-version switching.
- **Channel Configuration**: Configure Discord / Telegram / Feishu / DingTalk / QQ credentials per instance in Channels, with stop-before-save safeguards.
- **Local Model Serving**: Configure and run local GGUF inference in LlamaCPP (port, GPU layers, extra args, API health test).
- **Model Switching**: Switch instance model providers in Model Switch (OpenAI/DeepSeek/Moonshot/Ollama/Llama.cpp and more) with config automation.
- **Plugin Management**: Install/uninstall plugins per instance in the Plugins panel, with one-click recommended plugins.
- **Backup & Restore**: Create zip backups and restore instances; dependency reinstall is attempted after restore.
- **Log Viewer**: Follow instance logs in-app, clear logs, or open log files with the system default app.
- **Advanced Settings**: Configure tray behavior, auto-start, update checks, source mirrors, and troubleshooting cleanup actions.

## Quick Start

### 1) Download

Download the installer from the repository [Releases](https://github.com/shinnpuru/OpenClawLauncher/releases) page for your OS (macOS / Linux / Windows).

### 2) Install

Install with your platform package:

- macOS: put the `.app` package in Application folder and open.
- Windows: run the `.exe` package.

### 3) Use

After launching `OpenClaw Launcher`:

- Start with the **Onboard** panel for first-run initialization. Tutorial: [Wiki](https://github.com/shinnpuru/OpenClawLauncher/wiki)
- Confirm Node.js / OpenClaw (required) and Python / uv (optional) in **Dependencies**.
- Configure local or online model settings in **LlamaCPP** and **Model Switch**.
- Configure bot channels in **Channels**.
- Create and run instances in **Instances**, then update version or open folder/CLI when needed.
- Install required extensions in **Plugins**.
- Use **Logs** and **Backups** for troubleshooting and data safety.
- Tune tray behavior, auto-start, mirrors, and cleanup options in **Advanced**.

<details>
<summary>Developer Notes</summary>

### Development Environment

- Python 3.10+
- Node.js v22+

### Run Locally

This project uses [uv](https://github.com/astral-sh/uv):

```bash
uv sync
uv run python src/openclaw_launcher/main.py
```

### Local Packaging (Optional)

```bash
uv add --dev pyinstaller
uv run pyinstaller --name "OpenClaw Launcher" --windowed --onefile src/openclaw_launcher/main.py
```

Output directory: `dist/`

</details>

## License

MIT
