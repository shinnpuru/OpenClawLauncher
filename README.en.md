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

- **Instance Management**: Create, start, stop, and delete multiple OpenClaw instances.
- **Source-based Install**: Download and initialize from OpenClaw source archives.
- **Dependency Checks**: Validate required runtimes (Node.js v22+, OpenClaw) and optional runtimes (Python, uv).
- **Log Viewer**: Inspect runtime logs directly in the UI.
- **Backup & Restore**: Archive and restore instance data when needed.
- **Runtime Configuration**: Configure basic environment and repository settings.

## Quick Start

### 1) Download

Download the installer from the repository **Releases** page for your OS (macOS / Linux / Windows).

### 2) Install

Install with your platform package:

- macOS: open the `.app` package.
- Windows: run the `.exe` package.
- Linux: use the distro package.

### 3) Use

After launching `OpenClaw Launcher`:

- Check Node.js / OpenClaw (required) and Python / uv (optional) in the Dependencies panel.
- If Python / uv is installed, it is automatically added to the instance runtime environment variables (including PATH).
- Create and start an instance in the Instances panel.
- Review runtime output in the Logs panel.
- Manage backup and restore in the Backups panel.

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
