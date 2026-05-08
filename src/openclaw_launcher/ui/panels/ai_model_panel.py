from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QLineEdit, QComboBox, QGroupBox, QMessageBox, QCheckBox,
    QProgressDialog, QTabWidget
)
from PySide6.QtCore import Qt, QThread, Signal
import json
from pathlib import Path
from ...core.config import Config
from ...core.process_manager import ProcessManager
from ..i18n import i18n
from .llamacpp_panel import LlamaCppTab

# 在线模型提供商配置（参考 VoiceTransl）
ONLINE_PROVIDERS = {
    "moonshot": {
        "base_url": "https://api.moonshot.cn/v1",
        "default_model": "kimi-k2.5",
        "requires_key": True,
    },
    "moonshot_intl": {
        "base_url": "https://api.moonshot.ai/v1",
        "default_model": "kimi-k2.5",
        "requires_key": True,
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "requires_key": True,
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-5.3-codex",
        "requires_key": True,
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "default_model": "gemini-3-flash-preview",
        "requires_key": True,
    },
    "grok": {
        "base_url": "https://api.x.ai/v1",
        "default_model": "grok-4-1-fast-non-reasoning",
        "requires_key": True,
    },
    "glm_intl": {
        "base_url": "https://api.z.ai/api/paas",
        "default_model": "glm-4.7",
        "requires_key": True,
    },
    "glm": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "default_model": "glm-4.7",
        "requires_key": True,
    },
    "aliyun": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen3-coder-next",
        "requires_key": True,
    },
    "aliyun_coding": {
        "base_url": "https://coding.dashscope.aliyuncs.com/v1",
        "default_model": "qwen3-coder-next",
        "requires_key": True,
    },
    "doubao": {
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "default_model": "doubao-seed-2.0-code",
        "requires_key": True,
    },
    "doubao_coding": {
        "base_url": "https://ark.cn-beijing.volces.com/api/coding/v3",
        "default_model": "ark-code-latest",
        "requires_key": True,
    },
    "ollama": {
        "base_url": "http://127.0.0.1:11434/v1",
        "default_model": "qwen3.5",
        "requires_key": False,
    },
    "llamacpp": {
        "base_url": "http://127.0.0.1:8989/v1",
        "default_model": "local-model",
        "requires_key": False,
    },
    "custom": {
        "base_url": "",
        "default_model": "",
        "requires_key": True,
    },
}


def get_provider_display_name(provider_key: str) -> str:
    name_key = f"model_switch_provider_{provider_key}"
    translated = i18n.t(name_key)
    return translated if translated != name_key else provider_key


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
            if ProcessManager.get_status(self.instance_name) == "Running":
                self.progress.emit(i18n.t("model_switch_stopping_instance"))
                ProcessManager.stop_instance(self.instance_name)
                # 等待实例完全停止
                import time
                for _ in range(30):  # 最多等待30秒
                    if ProcessManager.get_status(self.instance_name) != "Running":
                        break
                    time.sleep(1)
                else:
                    raise RuntimeError(i18n.t("model_switch_stop_timeout"))

            # 2. 修改 openclaw.json
            self.progress.emit(i18n.t("model_switch_updating_config"))
            self._update_openclaw_config(instance_path)

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
        use_vision_input = bool(self.config.get("use_vision_input", False))
        model_ref = f"{self.provider_key}/{model_id}"

        model_inputs = ["text"]
        if use_vision_input:
            model_inputs.append("image")

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
                        "input": model_inputs,
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
            "primary": model_ref
        }
        defaults_config["models"] = {
            model_ref: {}
        }
        if use_vision_input:
            defaults_config["imageModel"] = {
                "primary": model_ref
            }

        agents_obj["defaults"] = defaults_config
        config_data["agents"] = agents_obj

        # 写入配置
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
            f.write('\n')


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

        # Instance Selection Group
        self.instance_group = QGroupBox(i18n.t("model_switch_instance_group"))
        instance_layout = QVBoxLayout(self.instance_group)

        instance_select_layout = QHBoxLayout()
        self.instance_label = QLabel(i18n.t("model_switch_select_instance"))
        instance_select_layout.addWidget(self.instance_label)

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

        layout.addWidget(self.instance_group)

        # Model Provider Selection Group
        self.provider_group = QGroupBox(i18n.t("model_switch_provider_group"))
        provider_layout = QVBoxLayout(self.provider_group)

        provider_select_layout = QHBoxLayout()
        self.provider_label = QLabel(i18n.t("model_switch_provider"))
        provider_select_layout.addWidget(self.provider_label)

        self.provider_combo = QComboBox()
        self._populate_provider_combo()
        self.provider_combo.currentIndexChanged.connect(self.on_provider_changed)
        self.instance_combo.currentIndexChanged.connect(self.on_instance_changed)
        provider_select_layout.addWidget(self.provider_combo)
        provider_select_layout.addStretch()

        provider_layout.addLayout(provider_select_layout)

        # Provider icon/type indicator
        self.provider_type_label = QLabel("")
        self.provider_type_label.setStyleSheet("font-weight: bold;")
        provider_layout.addWidget(self.provider_type_label)

        layout.addWidget(self.provider_group)

        # Configuration Group
        self.config_group = QGroupBox(i18n.t("model_switch_config_group"))
        config_layout = QVBoxLayout(self.config_group)

        # API Base URL
        base_url_layout = QHBoxLayout()
        self.base_url_label = QLabel(i18n.t("model_switch_base_url"))
        base_url_layout.addWidget(self.base_url_label)

        self.base_url_edit = QLineEdit()
        self.base_url_edit.setPlaceholderText(i18n.t("model_switch_base_url_placeholder"))
        base_url_layout.addWidget(self.base_url_edit)

        config_layout.addLayout(base_url_layout)

        # API Key
        api_key_layout = QHBoxLayout()
        self.api_key_label = QLabel(i18n.t("model_switch_api_key"))
        api_key_layout.addWidget(self.api_key_label)

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
        self.model_id_label = QLabel(i18n.t("model_switch_model_id"))
        model_id_layout.addWidget(self.model_id_label)

        self.model_id_edit = QLineEdit()
        self.model_id_edit.setPlaceholderText(i18n.t("model_switch_model_id_placeholder"))
        model_id_layout.addWidget(self.model_id_edit)

        config_layout.addLayout(model_id_layout)

        # Model Name (display name)
        model_name_layout = QHBoxLayout()
        self.model_name_label = QLabel(i18n.t("model_switch_model_name"))
        model_name_layout.addWidget(self.model_name_label)

        self.model_name_edit = QLineEdit()
        self.model_name_edit.setPlaceholderText(i18n.t("model_switch_model_name_placeholder"))
        model_name_layout.addWidget(self.model_name_edit)

        config_layout.addLayout(model_name_layout)

        # Vision input toggle
        self.vision_input_checkbox = QCheckBox(i18n.t("model_switch_use_vision_input"))
        self.vision_input_checkbox.setChecked(False)
        config_layout.addWidget(self.vision_input_checkbox)

        layout.addWidget(self.config_group)

        # Info/Warning label
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        # Apply Button
        self.apply_btn = QPushButton(i18n.t("model_switch_apply"))
        self.apply_btn.clicked.connect(self.apply_model_switch)

        self.test_api_btn = QPushButton(i18n.t("model_switch_test_api"))
        self.test_api_btn.clicked.connect(self.test_api)

        action_layout = QHBoxLayout()
        action_layout.addWidget(self.test_api_btn)
        action_layout.addWidget(self.apply_btn)
        layout.addLayout(action_layout)

        # Warning note
        self.warning_label = QLabel(i18n.t("model_switch_warning"))
        self.warning_label.setStyleSheet("color: orange;")
        self.warning_label.setWordWrap(True)
        layout.addWidget(self.warning_label)

        layout.addStretch()

    def refresh_instance_list(self):
        """Refresh instance list"""
        current_instance = self.instance_combo.currentData()
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

        if current_instance:
            index = self.instance_combo.findData(current_instance)
            if index >= 0:
                self.instance_combo.setCurrentIndex(index)

    def _populate_provider_combo(self):
        current_provider = self.provider_combo.currentData() if hasattr(self, "provider_combo") else ""
        self.provider_combo.clear()
        self.provider_combo.addItem(i18n.t("model_switch_select_provider"), "")
        for key in ONLINE_PROVIDERS.keys():
            self.provider_combo.addItem(get_provider_display_name(key), key)

        if current_provider:
            index = self.provider_combo.findData(current_provider)
            if index >= 0:
                self.provider_combo.setCurrentIndex(index)

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
            self.base_url_edit.setPlaceholderText(i18n.t("model_switch_base_url_placeholder"))
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
            i18n.t("model_switch_confirm", instance=instance_name, provider=get_provider_display_name(provider_key)),
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
            "use_vision_input": self.vision_input_checkbox.isChecked(),
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
        try:
            self.worker.setParent(self)
            self.worker.finished.connect(self.worker.deleteLater)
        except Exception:
            pass
        self.worker.progress.connect(self.on_progress)
        self.worker.finished_success.connect(self.on_success)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.start()

    def test_api(self):
        """Test the configured provider API endpoint using current form values."""
        import urllib.request

        provider_key = self.provider_combo.currentData()
        if not provider_key:
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("model_switch_select_provider_prompt"))
            return

        provider_info = ONLINE_PROVIDERS.get(provider_key, {})
        base_url = self.base_url_edit.text().strip()
        api_key = self.api_key_edit.text().strip()

        if not base_url:
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("model_switch_base_url_required"))
            return

        url = f"{base_url.rstrip('/')}/models"
        headers = {
            "Accept": "application/json",
        }
        if provider_info.get("requires_key", True) and api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            # Some OpenAI-compatible gateways prefer explicit api-key header.
            headers["api-key"] = api_key

        try:
            request = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(request, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
                models = payload.get("data", [])

                if isinstance(models, list) and models:
                    model_info = []
                    for model in models[:20]:
                        model_info.append(f"  - {model.get('id', 'unknown')}")
                    QMessageBox.information(
                        self,
                        i18n.t("title_success"),
                        i18n.t("model_switch_test_success", models="\n".join(model_info))
                    )
                else:
                    QMessageBox.information(
                        self,
                        i18n.t("title_success"),
                        i18n.t("model_switch_test_no_models")
                    )
        except Exception as e:
            QMessageBox.warning(
                self,
                i18n.t("title_warning"),
                i18n.t("model_switch_test_failed", error=str(e))
            )

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
                self.vision_input_checkbox.setChecked(bool(config.get("use_vision_input", False)))

    def update_ui_texts(self):
        """Update UI texts (when language changes)"""
        self.instance_group.setTitle(i18n.t("model_switch_instance_group"))
        self.instance_label.setText(i18n.t("model_switch_select_instance"))
        self.refresh_instance_btn.setText(i18n.t("btn_refresh"))

        self.provider_group.setTitle(i18n.t("model_switch_provider_group"))
        self.provider_label.setText(i18n.t("model_switch_provider"))

        self.config_group.setTitle(i18n.t("model_switch_config_group"))
        self.base_url_label.setText(i18n.t("model_switch_base_url"))
        self.base_url_edit.setPlaceholderText(i18n.t("model_switch_base_url_placeholder"))
        self.api_key_label.setText(i18n.t("model_switch_api_key"))
        self.api_key_edit.setPlaceholderText(i18n.t("model_switch_api_key_placeholder"))
        self.model_id_label.setText(i18n.t("model_switch_model_id"))
        self.model_id_edit.setPlaceholderText(i18n.t("model_switch_model_id_placeholder"))
        self.model_name_label.setText(i18n.t("model_switch_model_name"))
        self.model_name_edit.setPlaceholderText(i18n.t("model_switch_model_name_placeholder"))
        self.vision_input_checkbox.setText(i18n.t("model_switch_use_vision_input"))

        self.test_api_btn.setText(i18n.t("model_switch_test_api"))
        self.apply_btn.setText(i18n.t("model_switch_apply"))
        self.warning_label.setText(i18n.t("model_switch_warning"))

        if self.show_key_btn.isChecked():
            self.show_key_btn.setText(i18n.t("model_switch_hide_key"))
        else:
            self.show_key_btn.setText(i18n.t("model_switch_show_key"))

        self._populate_provider_combo()
        self.refresh_instance_list()
        self.on_provider_changed()
        self.on_instance_changed()

    def shutdown(self):
        """Shutdown the tab"""
        if self.worker and self.worker.isRunning():
            self.worker.wait(3000)

