from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QLineEdit, QComboBox, QTextEdit, QGroupBox, QMessageBox,
    QFileDialog, QScrollArea, QFrame, QSpinBox, QProgressDialog,
    QTabWidget, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from ...core.config import Config
from ...core.process_manager import ProcessManager
from ..i18n import i18n

# 在线模型提供商配置（参考 VoiceTransl）
ONLINE_PROVIDERS = {
    "moonshot": {
        "name": "Moonshot AI",
        "base_url": "https://api.moonshot.cn/v1",
        "default_model": "kimi-k2.5",
        "requires_key": True,
    },
    "moonshot_intl": {
        "name": "Moonshot AI (International)",
        "base_url": "https://api.moonshot.ai/v1",
        "default_model": "kimi-k2.5",
        "requires_key": True,
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "requires_key": True,
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o",
        "requires_key": True,
    },
    "glm": {
        "name": "智谱 GLM",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "default_model": "glm-4-flash",
        "requires_key": True,
    },
    "aliyun": {
        "name": "阿里云百炼",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-max",
        "requires_key": True,
    },
    "doubao": {
        "name": "火山引擎 Doubao",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "default_model": "doubao-pro-128k",
        "requires_key": True,
    },
    "ollama": {
        "name": "Ollama (本地)",
        "base_url": "http://localhost:11434/v1",
        "default_model": "llama3.1",
        "requires_key": False,
    },
    "llamacpp": {
        "name": "Llama.cpp (本地 - 本页面启动)",
        "base_url": "http://localhost:8989/v1",
        "default_model": "local-model",
        "requires_key": False,
    },
    "custom": {
        "name": "自定义 OpenAI 兼容",
        "base_url": "",
        "default_model": "",
        "requires_key": True,
    },
}


class LlamaCppProcessWorker(QThread):
    """Worker thread for running llama.cpp server process"""
    output_ready = Signal(str)
    process_started = Signal()
    process_stopped = Signal()
    error_occurred = Signal(str)

    def __init__(self, model_path: str, port: int = 8989, n_gpu_layers: int = 100, extra_params: str = ""):
        super().__init__()
        self.model_path = model_path
        self.port = port
        self.n_gpu_layers = n_gpu_layers
        self.extra_params = extra_params
        self.process = None
        self._running = False

    def run(self):
        try:
            # Find llama-server executable
            llama_exe = self._find_llama_server()
            if not llama_exe:
                self.error_occurred.emit("llama-server executable not found. Please ensure llama.cpp is installed.")
                return

            # Build command
            cmd = [
                str(llama_exe),
                "-m", self.model_path,
                "--port", str(self.port),
                "-ngl", str(self.n_gpu_layers),
            ]

            # Add extra parameters
            if self.extra_params.strip():
                cmd.extend(self.extra_params.strip().split())

            self._running = True
            self.process_started.emit()

            # Start process
            if sys.platform == "win32":
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )

            # Read output
            for line in iter(self.process.stdout.readline, ''):
                if not self._running:
                    break
                if line:
                    self.output_ready.emit(line.strip())

            self.process.stdout.close()
            self.process.wait()

        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self._running = False
            self.process_stopped.emit()

    def stop(self):
        self._running = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                try:
                    self.process.kill()
                    self.process.wait(timeout=2)
                except:
                    pass
            self.process = None

    def _find_llama_server(self) -> Path:
        """Find llama-server executable in common locations"""
        possible_names = ["llama-server", "llama-server.exe"]

        # Check in llama directory (same as VoiceTransl)
        llama_dir = Path.cwd() / "llama"
        for name in possible_names:
            exe_path = llama_dir / name
            if exe_path.exists():
                return exe_path

        # Check in PATH
        import shutil
        for name in possible_names:
            exe_path = shutil.which(name)
            if exe_path:
                return Path(exe_path)

        return None


class ModelSwitchWorker(QThread):
    """Worker thread for switching model configuration"""
    progress = Signal(str)
    finished_success = Signal()
    error_occurred = Signal(str)

    def __init__(self, instance_name: str, provider_key: str, config: dict):
        super().__init__()
        self.instance_name = instance_name
        self.provider_key = provider_key
        self.config = config

    def run(self):
        try:
            instance_path = Config.get_instance_path(self.instance_name)

            # 1. 检查实例是否运行中
            self.progress.emit(i18n.t("model_switch_checking_status"))
            if ProcessManager.is_instance_running(self.instance_name):
                self.progress.emit(i18n.t("model_switch_stopping_instance"))
                ProcessManager.stop_instance(self.instance_name)
                # 等待实例完全停止
                import time
                for _ in range(30):  # 最多等待30秒
                    if not ProcessManager.is_instance_running(self.instance_name):
                        break
                    time.sleep(1)
                else:
                    raise RuntimeError(i18n.t("model_switch_stop_timeout"))

            # 2. 修改 openclaw.json
            self.progress.emit(i18n.t("model_switch_updating_config"))
            self._update_openclaw_config(instance_path)

            # 3. 启动实例
            self.progress.emit(i18n.t("model_switch_starting_instance"))
            ProcessManager.start_instance(self.instance_name)

            self.finished_success.emit()

        except Exception as e:
            self.error_occurred.emit(str(e))

    def _update_openclaw_config(self, instance_path: Path):
        """更新实例的 openclaw.json 配置文件"""
        config_path = instance_path / ".openclaw" / "openclaw.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # 读取现有配置
        config_data = {}
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        config_data = loaded
            except Exception:
                pass

        provider_info = ONLINE_PROVIDERS.get(self.provider_key, {})

        # 构建模型配置
        base_url = self.config.get("base_url", provider_info.get("base_url", ""))
        api_key = self.config.get("api_key", "")
        model_id = self.config.get("model_id", provider_info.get("default_model", ""))
        model_name = self.config.get("model_name", model_id)

        # 构建 providers 配置
        providers_config = {
            self.provider_key: {
                "baseUrl": base_url,
                "apiKey": api_key if provider_info.get("requires_key", True) else "not-required",
                "auth": "api-key",
                "api": "openai-completions",
                "models": [
                    {
                        "id": model_id,
                        "name": model_name,
                        "api": "openai-completions",
                        "reasoning": False,
                        "input": ["text"],
                        "cost": {
                            "input": 0,
                            "output": 0,
                            "cacheRead": 0,
                            "cacheWrite": 0
                        },
                        "contextWindow": 200000,
                        "maxTokens": 8192
                    }
                ]
            }
        }

        # 保留其他 provider 配置
        existing_providers = config_data.get("models", {}).get("providers", {})
        if isinstance(existing_providers, dict):
            for key, value in existing_providers.items():
                if key != self.provider_key:
                    providers_config[key] = value

        config_data["models"] = {
            "providers": providers_config
        }

        # 更新 agents defaults
        agents_obj = config_data.get("agents", {})
        if not isinstance(agents_obj, dict):
            agents_obj = {}

        defaults_config = agents_obj.get("defaults", {})
        if not isinstance(defaults_config, dict):
            defaults_config = {}

        defaults_config["model"] = {
            "primary": f"{self.provider_key}/{model_id}"
        }
        defaults_config["models"] = {
            f"{self.provider_key}/{model_id}": {}
        }

        agents_obj["defaults"] = defaults_config
        config_data["agents"] = agents_obj

        # 写入配置
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
            f.write('\n')


class LlamaCppTab(QWidget):
    """Llama.cpp local server tab"""

    def __init__(self, parent_panel):
        super().__init__()
        self.parent_panel = parent_panel
        self.worker = None
        self._is_running = False
        self.init_ui()
        self.load_config()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Title
        title_label = QLabel(i18n.t("llamacpp_title"))
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        title_label.setFont(font)
        layout.addWidget(title_label)

        desc_label = QLabel(i18n.t("llamacpp_desc"))
        desc_label.setStyleSheet("color: gray;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        layout.addSpacing(10)

        # Model Configuration Group
        model_group = QGroupBox(i18n.t("llamacpp_model_group"))
        model_layout = QVBoxLayout(model_group)

        # Model file selection
        model_file_layout = QHBoxLayout()
        model_file_label = QLabel(i18n.t("llamacpp_model_file"))
        model_file_layout.addWidget(model_file_label)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.refresh_model_list()
        model_file_layout.addWidget(self.model_combo)

        self.refresh_models_btn = QPushButton(i18n.t("btn_refresh"))
        self.refresh_models_btn.clicked.connect(self.refresh_model_list)
        model_file_layout.addWidget(self.refresh_models_btn)

        self.browse_model_btn = QPushButton(i18n.t("btn_browse"))
        self.browse_model_btn.clicked.connect(self.browse_model_file)
        model_file_layout.addWidget(self.browse_model_btn)

        model_layout.addLayout(model_file_layout)

        # Open model directory button
        self.open_model_dir_btn = QPushButton(i18n.t("llamacpp_open_model_dir"))
        self.open_model_dir_btn.clicked.connect(self.open_model_directory)
        model_layout.addWidget(self.open_model_dir_btn)

        layout.addWidget(model_group)

        # Server Configuration Group
        server_group = QGroupBox(i18n.t("llamacpp_server_group"))
        server_layout = QVBoxLayout(server_group)

        # Port setting
        port_layout = QHBoxLayout()
        port_label = QLabel(i18n.t("llamacpp_port"))
        port_layout.addWidget(port_label)

        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(8989)
        port_layout.addWidget(self.port_spin)
        port_layout.addStretch()

        server_layout.addLayout(port_layout)

        # GPU layers
        gpu_layout = QHBoxLayout()
        gpu_label = QLabel(i18n.t("llamacpp_gpu_layers"))
        gpu_layout.addWidget(gpu_label)

        self.gpu_layers_spin = QSpinBox()
        self.gpu_layers_spin.setRange(0, 1000)
        self.gpu_layers_spin.setValue(100)
        self.gpu_layers_spin.setSpecialValueText(i18n.t("llamacpp_cpu_only"))
        gpu_layout.addWidget(self.gpu_layers_spin)
        gpu_layout.addStretch()

        server_layout.addLayout(gpu_layout)

        # API Address display (for reference)
        api_layout = QHBoxLayout()
        api_label = QLabel(i18n.t("llamacpp_api_address"))
        api_layout.addWidget(api_label)

        self.api_address_display = QLineEdit()
        self.api_address_display.setReadOnly(True)
        self.api_address_display.setText("http://localhost:8989")
        self.port_spin.valueChanged.connect(self.update_api_address)
        api_layout.addWidget(self.api_address_display)

        server_layout.addLayout(api_layout)

        layout.addWidget(server_group)

        # Parameters Group
        params_group = QGroupBox(i18n.t("llamacpp_params_group"))
        params_layout = QVBoxLayout(params_group)

        params_label = QLabel(i18n.t("llamacpp_extra_params_desc"))
        params_label.setStyleSheet("color: gray;")
        params_layout.addWidget(params_label)

        self.extra_params = QTextEdit()
        self.extra_params.setPlaceholderText(i18n.t("llamacpp_extra_params_placeholder"))
        self.extra_params.setMaximumHeight(80)
        params_layout.addWidget(self.extra_params)

        layout.addWidget(params_group)

        # Control buttons
        control_layout = QHBoxLayout()

        self.start_btn = QPushButton(i18n.t("llamacpp_start_server"))
        self.start_btn.clicked.connect(self.start_server)
        control_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton(i18n.t("llamacpp_stop_server"))
        self.stop_btn.clicked.connect(self.stop_server)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)

        self.test_api_btn = QPushButton(i18n.t("llamacpp_test_api"))
        self.test_api_btn.clicked.connect(self.test_api)
        control_layout.addWidget(self.test_api_btn)

        control_layout.addStretch()

        layout.addLayout(control_layout)

        # Status and output
        status_layout = QHBoxLayout()
        status_label = QLabel(i18n.t("llamacpp_status"))
        status_layout.addWidget(status_label)

        self.status_display = QLabel(i18n.t("llamacpp_status_stopped"))
        self.status_display.setStyleSheet("color: red; font-weight: bold;")
        status_layout.addWidget(self.status_display)
        status_layout.addStretch()

        layout.addLayout(status_layout)

        # Output log
        output_label = QLabel(i18n.t("llamacpp_output_log"))
        layout.addWidget(output_label)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setPlaceholderText(i18n.t("llamacpp_output_placeholder"))
        self.output_text.setMaximumHeight(150)
        layout.addWidget(self.output_text)

        layout.addStretch()

    def refresh_model_list(self):
        """Refresh the list of available .gguf models"""
        self.model_combo.clear()

        # Scan llama directory for .gguf files (same as VoiceTransl)
        llama_dir = Path.cwd() / "llama"
        models = []

        if llama_dir.exists():
            for file in llama_dir.iterdir():
                if file.is_file() and file.suffix == ".gguf":
                    models.append(file.name)

        if models:
            self.model_combo.addItems(models)
        else:
            self.model_combo.addItem(i18n.t("llamacpp_no_models_found"))

    def browse_model_file(self):
        """Open file dialog to select a .gguf model file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            i18n.t("llamacpp_select_model"),
            str(Path.cwd() / "llama"),
            "GGUF Models (*.gguf)"
        )
        if file_path:
            self.model_combo.setCurrentText(file_path)

    def open_model_directory(self):
        """Open the llama models directory"""
        llama_dir = Path.cwd() / "llama"
        llama_dir.mkdir(parents=True, exist_ok=True)

        import platform
        if platform.system() == "Windows":
            os.startfile(str(llama_dir))
        elif platform.system() == "Darwin":
            os.system(f'open "{llama_dir}"')
        else:
            os.system(f'xdg-open "{llama_dir}"')

    def update_api_address(self):
        """Update the displayed API address when port changes"""
        port = self.port_spin.value()
        self.api_address_display.setText(f"http://localhost:{port}")

    def start_server(self):
        """Start the llama.cpp server"""
        if self._is_running:
            return

        model_path = self.model_combo.currentText()
        if not model_path or model_path == i18n.t("llamacpp_no_models_found"):
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("llamacpp_no_model_selected"))
            return

        # Resolve full path
        llama_dir = Path.cwd() / "llama"
        if not Path(model_path).is_absolute():
            model_full_path = llama_dir / model_path
        else:
            model_full_path = Path(model_path)

        if not model_full_path.exists():
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("llamacpp_model_not_found"))
            return

        port = self.port_spin.value()
        gpu_layers = self.gpu_layers_spin.value()
        extra_params = self.extra_params.toPlainText()

        self.output_text.clear()
        self.output_text.append(i18n.t("llamacpp_starting_server", model=model_path))

        self.worker = LlamaCppProcessWorker(
            model_path=str(model_full_path),
            port=port,
            n_gpu_layers=gpu_layers,
            extra_params=extra_params
        )
        self.worker.output_ready.connect(self.on_output)
        self.worker.process_started.connect(self.on_process_started)
        self.worker.process_stopped.connect(self.on_process_stopped)
        self.worker.error_occurred.connect(self.on_process_error)
        self.worker.start()

    def stop_server(self):
        """Stop the llama.cpp server"""
        if self.worker and self._is_running:
            self.output_text.append(i18n.t("llamacpp_stopping_server"))
            self.worker.stop()

    def test_api(self):
        """Test if the llama.cpp API is accessible"""
        import urllib.request
        import json

        port = self.port_spin.value()
        url = f"http://localhost:{port}/v1/models"

        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read().decode())
                models = data.get("data", [])
                if models:
                    model_info = []
                    for m in models:
                        model_info.append(f"  - {m.get('id', 'unknown')}")
                    QMessageBox.information(
                        self,
                        i18n.t("title_success"),
                        i18n.t("llamacpp_api_test_success", models="\n".join(model_info))
                    )
                else:
                    QMessageBox.information(
                        self,
                        i18n.t("title_success"),
                        i18n.t("llamacpp_api_test_no_models")
                    )
        except Exception as e:
            QMessageBox.warning(
                self,
                i18n.t("title_warning"),
                i18n.t("llamacpp_api_test_failed", error=str(e))
            )

    def on_output(self, text):
        """Handle output from the server process"""
        self.output_text.append(text)
        # Auto-scroll to bottom
        scrollbar = self.output_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def on_process_started(self):
        """Handle server process started"""
        self._is_running = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_display.setText(i18n.t("llamacpp_status_running"))
        self.status_display.setStyleSheet("color: green; font-weight: bold;")
        self.save_config()

    def on_process_stopped(self):
        """Handle server process stopped"""
        self._is_running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_display.setText(i18n.t("llamacpp_status_stopped"))
        self.status_display.setStyleSheet("color: red; font-weight: bold;")
        self.worker = None

    def on_process_error(self, error):
        """Handle server process error"""
        self.output_text.append(f"[ERROR] {error}")
        QMessageBox.critical(self, i18n.t("title_error"), i18n.t("llamacpp_server_error", error=error))

    def save_config(self):
        """Save current configuration"""
        config = {
            "model": self.model_combo.currentText(),
            "port": self.port_spin.value(),
            "gpu_layers": self.gpu_layers_spin.value(),
            "extra_params": self.extra_params.toPlainText()
        }
        Config.set_setting("llamacpp_config", config)

    def load_config(self):
        """Load saved configuration"""
        config = Config.get_setting("llamacpp_config", {})
        if isinstance(config, dict):
            model = config.get("model", "")
            if model:
                index = self.model_combo.findText(model)
                if index >= 0:
                    self.model_combo.setCurrentIndex(index)
                else:
                    self.model_combo.setCurrentText(model)

            port = config.get("port", 8989)
            self.port_spin.setValue(port)

            gpu_layers = config.get("gpu_layers", 100)
            self.gpu_layers_spin.setValue(gpu_layers)

            extra_params = config.get("extra_params", "")
            self.extra_params.setPlainText(extra_params)

    def shutdown(self):
        """Shutdown the tab and stop any running processes"""
        self.stop_server()
        if self.worker:
            self.worker.wait(3000)


class ModelSwitchTab(QWidget):
    """Model switch configuration tab"""

    def __init__(self, parent_panel):
        super().__init__()
        self.parent_panel = parent_panel
        self.worker = None
        self.init_ui()
        self.load_saved_config()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Title
        title_label = QLabel(i18n.t("model_switch_title"))
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        title_label.setFont(font)
        layout.addWidget(title_label)

        desc_label = QLabel(i18n.t("model_switch_desc"))
        desc_label.setStyleSheet("color: gray;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        layout.addSpacing(10)

        # Instance Selection Group
        instance_group = QGroupBox(i18n.t("model_switch_instance_group"))
        instance_layout = QVBoxLayout(instance_group)

        instance_select_layout = QHBoxLayout()
        instance_label = QLabel(i18n.t("model_switch_select_instance"))
        instance_select_layout.addWidget(instance_label)

        self.instance_combo = QComboBox()
        self.refresh_instance_list()
        instance_select_layout.addWidget(self.instance_combo)

        self.refresh_instance_btn = QPushButton(i18n.t("btn_refresh"))
        self.refresh_instance_btn.clicked.connect(self.refresh_instance_list)
        instance_select_layout.addWidget(self.refresh_instance_btn)

        instance_layout.addLayout(instance_select_layout)

        # Current model info
        self.current_model_label = QLabel(i18n.t("model_switch_current_model", model=i18n.t("model_switch_unknown")))
        self.current_model_label.setStyleSheet("color: blue;")
        instance_layout.addWidget(self.current_model_label)

        layout.addWidget(instance_group)

        # Model Provider Selection Group
        provider_group = QGroupBox(i18n.t("model_switch_provider_group"))
        provider_layout = QVBoxLayout(provider_group)

        provider_select_layout = QHBoxLayout()
        provider_label = QLabel(i18n.t("model_switch_provider"))
        provider_select_layout.addWidget(provider_label)

        self.provider_combo = QComboBox()
        self.provider_combo.addItem(i18n.t("model_switch_select_provider"), "")
        for key, info in ONLINE_PROVIDERS.items():
            self.provider_combo.addItem(info["name"], key)
        self.provider_combo.currentIndexChanged.connect(self.on_provider_changed)
        provider_select_layout.addWidget(self.provider_combo)
        provider_select_layout.addStretch()

        provider_layout.addLayout(provider_select_layout)

        # Provider icon/type indicator
        self.provider_type_label = QLabel("")
        self.provider_type_label.setStyleSheet("font-weight: bold;")
        provider_layout.addWidget(self.provider_type_label)

        layout.addWidget(provider_group)

        # Configuration Group
        config_group = QGroupBox(i18n.t("model_switch_config_group"))
        config_layout = QVBoxLayout(config_group)

        # API Base URL
        base_url_layout = QHBoxLayout()
        base_url_label = QLabel(i18n.t("model_switch_base_url"))
        base_url_layout.addWidget(base_url_label)

        self.base_url_edit = QLineEdit()
        self.base_url_edit.setPlaceholderText("https://api.example.com/v1")
        base_url_layout.addWidget(self.base_url_edit)

        config_layout.addLayout(base_url_layout)

        # API Key
        api_key_layout = QHBoxLayout()
        api_key_label = QLabel(i18n.t("model_switch_api_key"))
        api_key_layout.addWidget(api_key_label)

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText(i18n.t("model_switch_api_key_placeholder"))
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        api_key_layout.addWidget(self.api_key_edit)

        self.show_key_btn = QPushButton(i18n.t("model_switch_show_key"))
        self.show_key_btn.setCheckable(True)
        self.show_key_btn.toggled.connect(self.toggle_key_visibility)
        api_key_layout.addWidget(self.show_key_btn)

        config_layout.addLayout(api_key_layout)

        # Model ID
        model_id_layout = QHBoxLayout()
        model_id_label = QLabel(i18n.t("model_switch_model_id"))
        model_id_layout.addWidget(model_id_label)

        self.model_id_edit = QLineEdit()
        self.model_id_edit.setPlaceholderText("model-name")
        model_id_layout.addWidget(self.model_id_edit)

        config_layout.addLayout(model_id_layout)

        # Model Name (display name)
        model_name_layout = QHBoxLayout()
        model_name_label = QLabel(i18n.t("model_switch_model_name"))
        model_name_layout.addWidget(model_name_label)

        self.model_name_edit = QLineEdit()
        self.model_name_edit.setPlaceholderText(i18n.t("model_switch_model_name_placeholder"))
        model_name_layout.addWidget(self.model_name_edit)

        config_layout.addLayout(model_name_layout)

        layout.addWidget(config_group)

        # Info/Warning label
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        # Apply Button
        self.apply_btn = QPushButton(i18n.t("model_switch_apply"))
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.apply_btn.clicked.connect(self.apply_model_switch)
        layout.addWidget(self.apply_btn)

        # Warning note
        warning_label = QLabel(i18n.t("model_switch_warning"))
        warning_label.setStyleSheet("color: orange;")
        warning_label.setWordWrap(True)
        layout.addWidget(warning_label)

        layout.addStretch()

    def refresh_instance_list(self):
        """Refresh instance list"""
        self.instance_combo.clear()
        instances = ProcessManager.get_all_instances()

        if not instances:
            self.instance_combo.addItem(i18n.t("model_switch_no_instances"), "")
            return

        self.instance_combo.addItem(i18n.t("model_switch_select_instance"), "")
        for instance in instances:
            name = instance.get("name", "")
            status = instance.get("status", "")
            display = f"{name} ({status})"
            self.instance_combo.addItem(display, name)

        self.instance_combo.currentIndexChanged.connect(self.on_instance_changed)

    def on_instance_changed(self):
        """Update current model info when instance selection changes"""
        instance_name = self.instance_combo.currentData()
        if not instance_name:
            self.current_model_label.setText(i18n.t("model_switch_current_model", model=i18n.t("model_switch_unknown")))
            return

        # Read current configuration
        try:
            instance_path = Config.get_instance_path(instance_name)
            config_path = instance_path / ".openclaw" / "openclaw.json"

            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                agents = config.get("agents", {})
                defaults = agents.get("defaults", {})
                model = defaults.get("model", {})
                primary = model.get("primary", i18n.t("model_switch_unknown"))

                self.current_model_label.setText(i18n.t("model_switch_current_model", model=primary))
            else:
                self.current_model_label.setText(i18n.t("model_switch_current_model", model=i18n.t("model_switch_not_configured")))
        except Exception:
            self.current_model_label.setText(i18n.t("model_switch_current_model", model=i18n.t("model_switch_unknown")))

    def on_provider_changed(self):
        """Update defaults when provider selection changes"""
        provider_key = self.provider_combo.currentData()

        if not provider_key or provider_key not in ONLINE_PROVIDERS:
            self.provider_type_label.setText("")
            self.info_label.setText("")
            return

        provider_info = ONLINE_PROVIDERS.get(provider_key, {})

        # Set default values
        self.base_url_edit.setText(provider_info.get("base_url", ""))
        self.model_id_edit.setText(provider_info.get("default_model", ""))
        self.model_name_edit.setText(provider_info.get("default_model", ""))

        # Check if local model
        is_local = provider_key in ["ollama", "llamacpp"]

        if is_local:
            self.provider_type_label.setText(f"🖥️ {i18n.t('model_switch_local_model')}")
            self.provider_type_label.setStyleSheet("color: green; font-weight: bold;")
            self.api_key_edit.setPlaceholderText(i18n.t("model_switch_no_key_needed"))
            self.api_key_edit.setEnabled(False)

            if provider_key == "llamacpp":
                self.info_label.setText(i18n.t("model_switch_llamacpp_info"))
            else:
                self.info_label.setText(i18n.t("model_switch_local_info"))
            self.info_label.setStyleSheet("color: green;")
        else:
            self.provider_type_label.setText(f"☁️ {i18n.t('model_switch_online_model')}")
            self.provider_type_label.setStyleSheet("color: blue; font-weight: bold;")
            self.api_key_edit.setPlaceholderText(i18n.t("model_switch_api_key_placeholder"))
            self.api_key_edit.setEnabled(True)
            self.info_label.setText(i18n.t("model_switch_online_info"))
            self.info_label.setStyleSheet("color: blue;")

        # Custom provider allows editing base URL
        if provider_key == "custom":
            self.base_url_edit.setReadOnly(False)
            self.base_url_edit.setPlaceholderText("https://api.example.com/v1")
        else:
            self.base_url_edit.setReadOnly(True)

    def toggle_key_visibility(self, checked):
        """Toggle API Key visibility"""
        if checked:
            self.api_key_edit.setEchoMode(QLineEdit.Normal)
            self.show_key_btn.setText(i18n.t("model_switch_hide_key"))
        else:
            self.api_key_edit.setEchoMode(QLineEdit.Password)
            self.show_key_btn.setText(i18n.t("model_switch_show_key"))

    def apply_model_switch(self):
        """Apply model switch"""
        instance_name = self.instance_combo.currentData()
        provider_key = self.provider_combo.currentData()

        if not instance_name:
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("model_switch_select_instance_prompt"))
            return

        if not provider_key:
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("model_switch_select_provider_prompt"))
            return

        provider_info = ONLINE_PROVIDERS.get(provider_key, {})

        # Validate inputs
        base_url = self.base_url_edit.text().strip()
        api_key = self.api_key_edit.text().strip()
        model_id = self.model_id_edit.text().strip()
        model_name = self.model_name_edit.text().strip() or model_id

        if not base_url:
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("model_switch_base_url_required"))
            return

        if not model_id:
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("model_switch_model_id_required"))
            return

        if provider_info.get("requires_key", True) and not api_key:
            reply = QMessageBox.question(
                self,
                i18n.t("title_confirm"),
                i18n.t("model_switch_no_key_confirm"),
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        # Confirm switch
        reply = QMessageBox.question(
            self,
            i18n.t("title_confirm"),
            i18n.t("model_switch_confirm", instance=instance_name, provider=provider_info.get("name", provider_key)),
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Save configuration
        config = {
            "base_url": base_url,
            "api_key": api_key,
            "model_id": model_id,
            "model_name": model_name,
        }
        self.save_config(provider_key, config)

        # Execute switch
        self.progress_dialog = QProgressDialog(
            i18n.t("model_switch_in_progress"),
            "",
            0,
            0,
            self,
        )
        self.progress_dialog.setWindowTitle(i18n.t("model_switch_title"))
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setCancelButton(None)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.show()

        self.apply_btn.setEnabled(False)

        self.worker = ModelSwitchWorker(instance_name, provider_key, config)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished_success.connect(self.on_success)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.start()

    def on_progress(self, message):
        """Update progress"""
        if self.progress_dialog:
            self.progress_dialog.setLabelText(message)

    def on_success(self):
        """Switch successful"""
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None

        self.apply_btn.setEnabled(True)
        self.worker = None

        QMessageBox.information(
            self,
            i18n.t("title_success"),
            i18n.t("model_switch_success")
        )

        # Refresh current model display
        self.on_instance_changed()

    def on_error(self, error):
        """Switch error"""
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None

        self.apply_btn.setEnabled(True)
        self.worker = None

        QMessageBox.critical(
            self,
            i18n.t("title_error"),
            i18n.t("model_switch_error", error=error)
        )

    def save_config(self, provider_key: str, config: dict):
        """Save configuration to settings"""
        saved = Config.get_setting("model_switch_configs", {})
        if not isinstance(saved, dict):
            saved = {}

        saved[provider_key] = config
        Config.set_setting("model_switch_configs", saved)
        Config.set_setting("model_switch_last_provider", provider_key)

    def load_saved_config(self):
        """Load saved configuration"""
        last_provider = Config.get_setting("model_switch_last_provider", "")
        configs = Config.get_setting("model_switch_configs", {})

        if last_provider and last_provider in ONLINE_PROVIDERS:
            index = self.provider_combo.findData(last_provider)
            if index >= 0:
                self.provider_combo.setCurrentIndex(index)

            config = configs.get(last_provider, {})
            if config:
                self.base_url_edit.setText(config.get("base_url", ""))
                self.api_key_edit.setText(config.get("api_key", ""))
                self.model_id_edit.setText(config.get("model_id", ""))
                self.model_name_edit.setText(config.get("model_name", ""))

    def update_ui_texts(self):
        """Update UI texts (when language changes)"""
        self.refresh_instance_list()

    def shutdown(self):
        """Shutdown the tab"""
        if self.worker and self.worker.isRunning():
            self.worker.wait(3000)


class AIModelPanel(QWidget):
    """Combined AI Model Panel with Llama.cpp and Model Switch tabs"""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create tab widget
        self.tabs = QTabWidget()

        # Create subtabs
        self.llamacpp_tab = LlamaCppTab(self)
        self.model_switch_tab = ModelSwitchTab(self)

        # Add subtabs
        self.tabs.addTab(self.llamacpp_tab, i18n.t("tab_llamacpp"))
        self.tabs.addTab(self.model_switch_tab, i18n.t("tab_model_switch"))

        layout.addWidget(self.tabs)

    def update_ui_texts(self):
        """Update UI texts when language changes"""
        self.tabs.setTabText(0, i18n.t("tab_llamacpp"))
        self.tabs.setTabText(1, i18n.t("tab_model_switch"))

        if hasattr(self.llamacpp_tab, 'update_ui_texts'):
            self.llamacpp_tab.update_ui_texts()
        if hasattr(self.model_switch_tab, 'update_ui_texts'):
            self.model_switch_tab.update_ui_texts()

    def shutdown(self):
        """Shutdown the panel"""
        if hasattr(self.llamacpp_tab, 'shutdown'):
            self.llamacpp_tab.shutdown()
        if hasattr(self.model_switch_tab, 'shutdown'):
            self.model_switch_tab.shutdown()


