<p align="center">
	<img src="teaser.png" alt="OpenClaw Launcher Logo" width="200"/>
</p>

<h1 align="center">OpenClaw Launcher</h1>

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/UI-PySide6-41CD52?logo=qt&logoColor=white)
![Platforms](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-555)
![License](https://img.shields.io/badge/License-MIT-blue)
[![Build and Release PyInstaller](https://github.com/shinnpuru/OpenClawLauncher/actions/workflows/release-pyinstaller.yml/badge.svg)](https://github.com/shinnpuru/OpenClawLauncher/actions/workflows/release-pyinstaller.yml)

<p align="center"><a href="README.md">中文</a> | English</p>

`OpenClaw Launcher` is a PySide6 desktop application that provides a graphical workflow for installing, configuring, and running [OpenClaw](https://github.com/openclaw/openclaw).

## Key Features

- **Guided onboarding**: Install the required runtimes, create the default `openclaw` instance, and start it in one click. The Onboarding panel also provides start/stop, WebUI, CLI, the instance configuration folder, and in-place OpenClaw update actions.
- **Runtime version management**: Download, select, and remove OpenClaw and Node.js versions, plus optional Python and uv versions. The launcher can refresh the available OpenClaw releases and automatically select another default after the current default is removed.
- **Channel configuration**: Configure Discord, Telegram, Feishu, DingTalk, QQ, and Weixin for each instance. Plugin-backed channels offer an install action when their plugin is missing, and Weixin login opens directly in the instance CLI.
- **Model switching**: Configure OpenAI-compatible online and local providers—including OpenAI, Moonshot, DeepSeek, Gemini, Grok, GLM, Qwen/DashScope, Doubao, Ollama, llama.cpp, and custom endpoints—and test the API before applying it to an instance.
- **Local model serving**: Run GGUF models with the bundled llama.cpp server; configure the model, optional multimodal projector, port, GPU layers, and extra arguments, then inspect output and test API connectivity.
- **Plugin management**: Detect installed plugins and install or uninstall npm plugin packages per instance. If an uninstall leaves files behind, the launcher provides a direct folder shortcut for manual cleanup.
- **Instance environment variables**: Add, edit, and remove environment variables stored for each instance.
- **Backup, restore, and logs**: Create zip backups, restore an instance with dependency reinstallation, follow launcher and instance logs, clear a selected log, or open it with the system default application.
- **Desktop and advanced settings**: Switch between Chinese and English and light/dark/system themes; configure tray behavior, launcher auto-start, minimized startup, automatic instance or llama.cpp startup, update checks, download mirrors, and troubleshooting cleanup actions.

## Quick Start

### 1. Download and open the launcher

Open the [latest release](https://github.com/shinnpuru/OpenClawLauncher/releases/latest) and select an archive under **Assets** for your system and GPU (`<version>` is the release version):

| System | File name | Details |
| --- | --- | --- |
| Windows x64 | `openclaw-launcher-<version>-windows.zip` | Bundles the Vulkan build of llama.cpp |
| Windows x64 (NVIDIA GPU) | `openclaw-launcher-<version>-windows-cuda.zip` | Bundles the CUDA 12.4 build of llama.cpp |
| macOS Apple Silicon | `openclaw-launcher-<version>-macos.app.zip` | For Apple Silicon Macs (`arm64`) |

- **Windows**: Extract the entire archive, open the `openclaw-launcher` folder, and run `openclaw-launcher.exe`. Keep its dependency files in the same directory.
- **macOS**: Extract the archive, move `openclaw-launcher.app` to Applications, and open it.

Release packages do not require Python, Node.js, or uv to be installed beforehand. Initial setup needs an internet connection to download Node.js, OpenClaw, and their dependencies. To use a local model, prepare a GGUF model file separately.

### 2. Initialize with one click

Open **Onboarding** and click the main install-and-start button. The launcher will:

1. Check for and install the latest compatible Node.js runtime.
2. Download the OpenClaw runtime if no default version is configured.
3. Create the default `openclaw` instance, install its dependencies, and initialize it.
4. Start OpenClaw on the default gateway port, `18789`.

The first installation can take some time. WebUI, CLI, folder, and update shortcuts remain disabled during installation and become available when it finishes.

### 3. Configure a model

A running instance still needs a working model before you can chat. New instances default to the local llama.cpp service at `http://127.0.0.1:8989/v1`. Choose one of these options:

- **Online model**: Open **Model Switch**, select the `openclaw` instance and a provider, enter your API key and model ID, and adjust the API URL if needed. Click **Test API**, then **Apply Model Switch** once the connection succeeds.
- **Local model**: Open **Local LLM**, select a GGUF model and an optional multimodal projector (mmproj), configure the port and GPU layers, and click **Start Server**, then **Test API**. The default port, `8989`, matches the instance's default model configuration. If you change the port or use another local service, apply its address in **Model Switch**.

Applying a model switch stops the instance if it is running. After configuring it, return to **Onboarding** and click **Start OpenClaw**.

### 4. Open WebUI and optionally connect channels

With OpenClaw and your chosen model service running, return to **Onboarding** and click **Open WebUI** to start chatting. The shortcut includes the current instance's gateway token in the URL automatically.

To connect Discord, Telegram, Feishu, DingTalk, QQ, or Weixin, open **Channels**, select the instance, and follow the prompts to enter credentials or log in. Missing channel plugins can be installed on that page.

### 5. Everyday use and updates

- **Start / stop**: Use the main button in **Onboarding** for the default instance, or manage other instances in **Instances**.
- **Open CLI / folder**: Use the shortcuts to open the instance CLI or its `.openclaw` configuration directory.
- **Update OpenClaw**: First refresh the OpenClaw version list in **Dependencies**, download the target version, and set it as the default. Then return to **Onboarding**, click **Update Version**, and confirm. This applies the default runtime to the instance. If it is running, the launcher prompts you to stop it first. Start it again after the update completes.
- **Manage runtimes and extensions**: Download, select, or remove runtimes in **Dependencies**, and maintain instance extensions and variables in **Plugins** and **Env Vars**.
- **Back up and troubleshoot**: Use **Backups** to back up or restore an instance and **Logs** to inspect installation and runtime output. If downloads are slow or fail, check the download mirror settings in **Advanced** and retry.

See the project [Wiki](https://github.com/shinnpuru/OpenClawLauncher/wiki) for more usage guides.

<details>
<summary>Developer Notes</summary>

### Requirements

- Python 3.10+
- Node.js: managed by the launcher; currently supports `>=24.16.0 <25` or `>=26.1.0`
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
