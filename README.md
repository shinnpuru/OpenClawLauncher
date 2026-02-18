
<p align="center">
	<img src="logo.png" alt="OpenClaw Launcher Logo" width="160" />
</p>

<h1 align="center">OpenClaw Launcher</h1>

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/UI-PySide6-41CD52?logo=qt&logoColor=white)
![Platforms](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux%20%7C%20Windows-555)
![License](https://img.shields.io/badge/License-MIT-blue)

<p align="center">中文 | <a href="README.en.md">English</a></p>

## 项目目的

`OpenClaw Launcher` 是一个基于 PySide6 的桌面启动器，用于以图形化方式管理 [OpenClaw](https://github.com/openclaw/openclaw) 的安装与运行流程。

它的核心目标是：

- 将原本依赖命令行的安装/启动流程可视化。
- 降低多实例管理、依赖检查与故障排查的门槛。
- 提供更清晰的运行状态、日志和备份入口。

## 核心功能

- **实例管理**：创建、启动、停止、删除多个 OpenClaw 实例。
- **源码安装**：下载 OpenClaw 对应版本源码压缩包并执行初始化流程。
- **依赖检测**：检查必需运行时（Node.js v22+、OpenClaw），并支持可选运行时（Python、uv）。
- **日志查看**：在界面内查看运行日志，便于排错。
- **备份与恢复**：将实例打包备份并在需要时恢复。
- **运行配置**：支持基础环境变量与仓库来源配置。

## 快速开始

### 1) 下载

前往仓库的 **Releases** 页面，下载与你系统匹配的安装包（macOS / Linux / Windows）。

### 2) 安装

按系统提示完成安装：

- macOS：打开 `.app` 包。
- Windows：运行 `.exe` 包。
- Linux：使用对应发行版包。

### 3) 使用

启动 `OpenClaw Launcher` 后：

- 在“依赖”面板检查 Node.js / OpenClaw（必需）以及 Python / uv（可选）。
- Python / uv 若已安装，会自动加入实例运行环境变量（含 PATH）。
- 在“实例”面板创建并启动 OpenClaw 实例。
- 在“日志”面板查看运行输出。
- 在“备份”面板进行备份与恢复。

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
