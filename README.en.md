<p align="center">
	<img src="logo.png" alt="OpenClaw Launcher Logo" width="160" />
</p>

<h1 align="center">OpenClaw Launcher</h1>

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/UI-PySide6-41CD52?logo=qt&logoColor=white)
![Platforms](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux%20%7C%20Windows-555)
![License](https://img.shields.io/badge/License-MIT-blue)
[![Build and Release PyInstaller](https://github.com/shinnpuru/OpenClawLauncher/actions/workflows/release-pyinstaller.yml/badge.svg)](https://github.com/shinnpuru/OpenClawLauncher/actions/workflows/release-pyinstaller.yml)

<p align="center">English | <a href="README.md">中文</a></p>

## Purpose

`OpenClaw Launcher` is a PySide6-based desktop launcher that provides a GUI workflow for installing and running [OpenClaw](https://github.com/openclaw/openclaw).

Its primary goals are:

- Replace command-heavy setup/start operations with a visual workflow.
- Simplify multi-instance management, dependency checks, and troubleshooting.
- Offer clear access to runtime status, logs, and backups.

## Key Features

- **Guided Onboarding**: The Onboard panel helps first-time setup with one-click dependency install, sample instance creation, and WebUI launch.
- **Instance Management**: Create/start/stop/delete instances, with optional pre-update backup, open-folder action, and instance CLI launcher.
- **Runtime Management**: Manage OpenClaw / Node.js (required) and Python / uv (optional) in Dependencies, including download and default-version switching.
- **Plugin Management**: Install/uninstall plugins per instance in the Plugins panel, with one-click recommended plugins.
- **Backup & Restore**: Create zip backups and restore instances; dependency reinstall is attempted after restore.
- **Log Viewer**: Follow instance logs in-app, clear logs, or open log files with the system default app.
- **Advanced Settings**: Configure tray behavior, auto-start, update checks, source mirrors, and troubleshooting cleanup actions.

## Panel Overview

- **Onboard**: 4-step guided flow (install dependencies -> create sample instance -> start instance -> open WebUI).
- **Instances**: Lifecycle operations, version update, and shortcuts for folder/CLI.
- **Dependencies**: Runtime version list, download progress, and default-version switching.
- **Backups**: Backup creation, backup list, restore flow, and overwrite confirmation.
- **Logs**: Per-instance log tailing with open/clear operations.
- **Plugins**: Extension directory inspection plus plugin install/uninstall.
- **Advanced**: App behavior settings, mirrors/sources, and troubleshooting cleanup utilities.

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
