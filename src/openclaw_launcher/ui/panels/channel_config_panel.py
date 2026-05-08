import json
from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.config import Config
from ...core.install_manager import InstallManager
from ...core.process_manager import ProcessManager
from ..i18n import i18n


class ChannelConfigPanel(QWidget):
    DINGTALK_PLUGIN = "dingtalk-connector"
    WEIXIN_PLUGIN = "openclaw-weixin"
    telegram_KEYS = ("telegram", "telegram")

    def __init__(self):
        super().__init__()
        self._active_telegram_key = "telegram"
        self._dingtalk_available = False
        self._weixin_available = False

        self.layout = QVBoxLayout(self)

        instance_row = QHBoxLayout()
        self.instance_label = QLabel(i18n.t("lbl_select_instance"))
        instance_row.addWidget(self.instance_label)

        self.instance_selector = QComboBox()
        self.instance_selector.currentIndexChanged.connect(self._on_instance_changed)
        instance_row.addWidget(self.instance_selector)

        self.btn_refresh = QPushButton(i18n.t("btn_refresh"))
        self.btn_refresh.clicked.connect(self.refresh)
        instance_row.addWidget(self.btn_refresh)
        self.layout.addLayout(instance_row)

        self.status_label = QLabel(i18n.t("status_ready"))
        self.layout.addWidget(self.status_label)

        self.config_container = QWidget()
        self.layout.addWidget(self.config_container)

        group_layout = QVBoxLayout(self.config_container)
        group_layout.setContentsMargins(0, 0, 0, 0)

        self.channel_form = QFormLayout()
        group_layout.addLayout(self.channel_form)

        self.discord_token = QLineEdit()
        self.discord_token.setPlaceholderText(i18n.t("ph_bot_token"))
        self.discord_token_label = QLabel()
        self.channel_form.addRow(self.discord_token_label, self.discord_token)

        self.telegram_token = QLineEdit()
        self.telegram_token.setPlaceholderText(i18n.t("ph_bot_token"))
        self.telegram_token_label = QLabel()
        self.channel_form.addRow(self.telegram_token_label, self.telegram_token)

        self.feishu_app_id = QLineEdit()
        self.feishu_app_secret = QLineEdit()
        self.feishu_app_secret.setEchoMode(QLineEdit.Password)
        self.feishu_app_id.setPlaceholderText(i18n.t("ph_app_id"))
        self.feishu_app_secret.setPlaceholderText(i18n.t("ph_app_secret"))
        self.feishu_app_id_label = QLabel()
        self.feishu_app_secret_label = QLabel()
        self.channel_form.addRow(self.feishu_app_id_label, self.feishu_app_id)
        self.channel_form.addRow(self.feishu_app_secret_label, self.feishu_app_secret)

        self.qq_app_id = QLineEdit()
        self.qq_app_secret = QLineEdit()
        self.qq_app_secret.setEchoMode(QLineEdit.Password)
        self.qq_app_id.setPlaceholderText(i18n.t("ph_app_id"))
        self.qq_app_secret.setPlaceholderText(i18n.t("ph_app_secret"))
        self.qq_app_id_label = QLabel()
        self.qq_app_secret_label = QLabel()
        self.channel_form.addRow(self.qq_app_id_label, self.qq_app_id)
        self.channel_form.addRow(self.qq_app_secret_label, self.qq_app_secret)

        self.dingtalk_app_id = QLineEdit()
        self.dingtalk_app_secret = QLineEdit()
        self.dingtalk_app_secret.setEchoMode(QLineEdit.Password)
        self.dingtalk_app_id.setPlaceholderText(i18n.t("ph_app_id"))
        self.dingtalk_app_secret.setPlaceholderText(i18n.t("ph_app_secret"))
        self.dingtalk_app_id_label = QLabel()
        self.dingtalk_app_secret_label = QLabel()
        self.channel_form.addRow(self.dingtalk_app_id_label, self.dingtalk_app_id)
        self.channel_form.addRow(self.dingtalk_app_secret_label, self.dingtalk_app_secret)

        self.dingtalk_hint = QLabel("")
        self.dingtalk_hint.setStyleSheet("color: orange;")
        self.dingtalk_hint.setWordWrap(True)
        group_layout.addWidget(self.dingtalk_hint)

        self.weixin_login_row = QHBoxLayout()
        self.weixin_login_label = QLabel()
        self.weixin_login_row.addWidget(self.weixin_login_label)
        self.weixin_login_row.addStretch()

        self.btn_weixin_login = QPushButton(i18n.t("btn_channel_login"))
        self.btn_weixin_login.clicked.connect(self.login_weixin_channel)
        self.weixin_login_row.addWidget(self.btn_weixin_login)
        group_layout.addLayout(self.weixin_login_row)

        self.weixin_hint = QLabel("")
        self.weixin_hint.setStyleSheet("color: orange;")
        self.weixin_hint.setWordWrap(True)
        group_layout.addWidget(self.weixin_hint)

        self.btn_save = QPushButton(i18n.t("btn_save"))
        self.btn_save.clicked.connect(self.save_channel_config)
        self.layout.addWidget(self.btn_save)

        self.layout.addStretch()

        self._update_channel_field_labels()
        self._load_instances()
        self.refresh()

    def _update_channel_field_labels(self):
        self.discord_token_label.setText(f"{i18n.t('channel_discord')} {i18n.t('lbl_bot_token')}")
        self.telegram_token_label.setText(f"{i18n.t('channel_telegram')} {i18n.t('lbl_bot_token')}")
        self.feishu_app_id_label.setText(f"{i18n.t('channel_feishu')} {i18n.t('lbl_app_id')}")
        self.feishu_app_secret_label.setText(f"{i18n.t('channel_feishu')} {i18n.t('lbl_app_secret')}")
        self.dingtalk_app_id_label.setText(f"{i18n.t('channel_dingtalk')} {i18n.t('lbl_app_id')}")
        self.dingtalk_app_secret_label.setText(f"{i18n.t('channel_dingtalk')} {i18n.t('lbl_app_secret')}")
        self.qq_app_id_label.setText(f"{i18n.t('channel_qq')} {i18n.t('lbl_app_id')}")
        self.qq_app_secret_label.setText(f"{i18n.t('channel_qq')} {i18n.t('lbl_app_secret')}")
        self.weixin_login_label.setText(i18n.t("channel_weixin"))

    def _load_instances(self, selected_name: str | None = None):
        self.instance_selector.blockSignals(True)
        self.instance_selector.clear()
        self.instance_selector.addItem(i18n.t("opt_select_instance"), "")

        if Config.INSTANCES_DIR.exists():
            for item in sorted(Config.INSTANCES_DIR.iterdir(), key=lambda p: p.name.lower()):
                if item.is_dir():
                    self.instance_selector.addItem(item.name, item.name)

        if selected_name:
            idx = self.instance_selector.findData(selected_name)
            if idx >= 0:
                self.instance_selector.setCurrentIndex(idx)

        self.instance_selector.blockSignals(False)
        self._update_controls_state()

    def _on_instance_changed(self):
        self.refresh()

    def _has_selected_instance(self) -> bool:
        return bool(self.instance_selector.currentData())

    def _get_selected_instance_path(self) -> Path | None:
        instance_name = self.instance_selector.currentData()
        if not instance_name:
            return None
        return Config.get_instance_path(instance_name)

    def _is_plugin_installed(self, plugin_name: str) -> bool:
        instance_path = self._get_selected_instance_path()
        if not instance_path:
            return False

        normalized = plugin_name.strip().lower()
        if not normalized:
            return False

        installs_path = instance_path / ".openclaw" / "plugins" / "installs.json"
        if not installs_path.exists():
            return False

        try:
            loaded = json.loads(installs_path.read_text(encoding="utf-8"))
        except Exception:
            return False

        if not isinstance(loaded, dict):
            return False

        install_records = loaded.get("installRecords")
        if not isinstance(install_records, dict):
            return False

        for record_key, record in install_records.items():
            candidates = []
            if isinstance(record_key, str):
                candidates.append(record_key)

            if isinstance(record, dict):
                for field in ("spec", "resolvedName", "resolvedSpec", "packageName", "name", "pluginId"):
                    value = record.get(field)
                    if isinstance(value, str):
                        candidates.append(value)

            for candidate in candidates:
                candidate_lower = candidate.strip().lower()
                if candidate_lower == normalized:
                    return True
                if candidate_lower.startswith(f"{normalized}@"):
                    return True

        return False

    def _set_field_pair_enabled(self, app_id_edit: QLineEdit, app_secret_edit: QLineEdit, enabled: bool):
        app_id_edit.setEnabled(enabled)
        app_secret_edit.setEnabled(enabled)

    def _update_plugin_gate_state(self):
        self._dingtalk_available = self._is_plugin_installed(self.DINGTALK_PLUGIN)
        self._weixin_available = self._is_plugin_installed(self.WEIXIN_PLUGIN)

        self._set_field_pair_enabled(self.dingtalk_app_id, self.dingtalk_app_secret, self._dingtalk_available)
        self.btn_weixin_login.setEnabled(self._weixin_available)

        self.dingtalk_hint.setText(
            "" if self._dingtalk_available else i18n.t("msg_channel_requires_plugin_dingtalk")
        )
        self.weixin_hint.setText(
            "" if self._weixin_available else i18n.t("msg_channel_requires_plugin_weixin")
        )

    def _update_controls_state(self):
        enabled = self._has_selected_instance()
        self.config_container.setEnabled(enabled)
        self.btn_save.setEnabled(enabled)

    def _read_config(self, config_path: Path) -> dict:
        if not config_path.exists():
            return {}
        loaded = json.loads(config_path.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, dict) else {}

    def _set_text(self, edit: QLineEdit, value):
        edit.setText(value if isinstance(value, str) else "")

    def _load_channel_values(self):
        instance_path = self._get_selected_instance_path()
        self._clear_fields()

        if not instance_path:
            self.status_label.setText(i18n.t("msg_select_instance_required"))
            return
        if not instance_path.exists():
            self.status_label.setText(i18n.t("msg_instance_not_found"))
            return

        config_path = instance_path / ".openclaw" / "openclaw.json"
        try:
            config_data = self._read_config(config_path)
            channels = config_data.get("channels")
            if not isinstance(channels, dict):
                channels = {}

            discord_obj = channels.get("discord")
            if isinstance(discord_obj, dict):
                self._set_text(self.discord_token, discord_obj.get("botToken"))

            telegram_obj = None
            active_key = "telegram"
            for key in self.telegram_KEYS:
                obj = channels.get(key)
                if isinstance(obj, dict):
                    telegram_obj = obj
                    active_key = key
                    break
            if telegram_obj is None:
                telegram_obj = {}
            self._active_telegram_key = active_key
            self._set_text(self.telegram_token, telegram_obj.get("botToken"))

            feishu_obj = channels.get("feishu")
            if isinstance(feishu_obj, dict):
                self._set_text(self.feishu_app_id, feishu_obj.get("appId"))
                self._set_text(self.feishu_app_secret, feishu_obj.get("appSecret"))

            dingtalk_obj = channels.get("dingtalk-connector")
            if isinstance(dingtalk_obj, dict):
                self._set_text(self.dingtalk_app_id, dingtalk_obj.get("clientId") or dingtalk_obj.get("appId"))
                self._set_text(self.dingtalk_app_secret, dingtalk_obj.get("clientSecret") or dingtalk_obj.get("appSecret"))

            qq_obj = channels.get("qqbot")
            if isinstance(qq_obj, dict):
                self._set_text(self.qq_app_id, qq_obj.get("appId"))
                self._set_text(self.qq_app_secret, qq_obj.get("clientSecret") or qq_obj.get("appSecret"))

            self.status_label.setText(i18n.t("status_ready"))
        except Exception as e:
            self.status_label.setText(i18n.t("msg_channel_config_load_failed"))
            QMessageBox.warning(self, i18n.t("title_warning"), str(e))

    def _clear_fields(self):
        for edit in [
            self.discord_token,
            self.telegram_token,
            self.feishu_app_id,
            self.feishu_app_secret,
            self.dingtalk_app_id,
            self.dingtalk_app_secret,
            self.qq_app_id,
            self.qq_app_secret,
        ]:
            edit.clear()

    def refresh(self):
        selected_name = self.instance_selector.currentData()
        self._load_instances(selected_name=selected_name)
        self._update_controls_state()
        self._load_channel_values()
        self._update_plugin_gate_state()

    def _merge_channel(self, channels_obj: dict, channel_key: str, values: dict):
        existing = channels_obj.get(channel_key)
        if not isinstance(existing, dict):
            existing = {}

        merged = dict(existing)
        merged.update(values)
        merged["enabled"] = True
        channels_obj[channel_key] = merged

    def _ensure_instance_stopped_for_save(self, instance_name: str) -> bool:
        if ProcessManager.get_status(instance_name) != "Running":
            return True

        reply = QMessageBox.question(
            self,
            i18n.t("title_confirm"),
            i18n.t("msg_channel_save_requires_stop_confirm", name=instance_name),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return False

        try:
            self.status_label.setText(i18n.t("msg_channel_stopping_instance", name=instance_name))
            ProcessManager.stop_instance(instance_name)

            import time
            for _ in range(30):
                if ProcessManager.get_status(instance_name) != "Running":
                    return True
                time.sleep(1)

            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("msg_channel_stop_timeout", name=instance_name))
            return False
        except Exception as e:
            QMessageBox.warning(
                self,
                i18n.t("title_warning"),
                i18n.t("msg_channel_stop_failed", name=instance_name, error=str(e)),
            )
            return False

    def save_channel_config(self):
        instance_path = self._get_selected_instance_path()
        instance_name = self.instance_selector.currentData()
        if not instance_path or not instance_name:
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("msg_select_instance_required"))
            return

        if not self._ensure_instance_stopped_for_save(instance_name):
            return

        config_path = instance_path / ".openclaw" / "openclaw.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            config_data = self._read_config(config_path)
            channels_obj = config_data.get("channels")
            if not isinstance(channels_obj, dict):
                channels_obj = {}

            self._merge_channel(
                channels_obj,
                "discord",
                {
                    "enabled": True,
                    "token": self.discord_token.text().strip(),
                    "dmPolicy": "open",
                    "allowFrom": ["*"]
                },
            )
            self._merge_channel(
                channels_obj,
                self._active_telegram_key,
                {
                    "enabled": True,
                    "botToken": self.telegram_token.text().strip(),
                    "dmPolicy": "open",
                    "allowFrom": ["*"]
                },
            )
            self._merge_channel(
                channels_obj,
                "feishu",
                {
                    "renderMode": "card",
                    "enabled": True,
                    "appId": self.feishu_app_id.text().strip(),
                    "appSecret": self.feishu_app_secret.text().strip(),
                    "dmPolicy": "open",
                    "allowFrom": ["*"]
                },
            )

            self._merge_channel(
                channels_obj,
                "qqbot",
                {
                    "enabled": True,
                    "appId": self.qq_app_id.text().strip(),
                    "clientSecret": self.qq_app_secret.text().strip(),
                    "dmPolicy": "open",
                    "allowFrom": ["*"]
                },
            )

            skipped = []
            if self._dingtalk_available:
                self._merge_channel(
                    channels_obj,
                    "dingtalk-connector",
                    {
                        "enabled": True,
                        "clientId": self.dingtalk_app_id.text().strip(),
                        "clientSecret": self.dingtalk_app_secret.text().strip(),
                        "gatewayToken": InstallManager.get_instance_gateway_token(instance_path, instance_name),
                        "dmPolicy": "open",
                        "allowFrom": ["*"]
                    },
                )

            config_data["channels"] = channels_obj
            config_path.write_text(json.dumps(config_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

            self.status_label.setText(i18n.t("msg_channel_config_saved"))
            if skipped:
                QMessageBox.warning(
                    self,
                    i18n.t("title_warning"),
                    i18n.t("msg_channel_partial_saved", channels=", ".join(skipped)),
                )
            else:
                QMessageBox.information(self, i18n.t("title_success"), i18n.t("msg_channel_config_saved"))
        except Exception as e:
            self.status_label.setText(i18n.t("msg_channel_config_save_failed"))
            QMessageBox.critical(
                self,
                i18n.t("title_error"),
                i18n.t("msg_channel_config_save_failed_with_error", error=str(e)),
            )

    def login_weixin_channel(self):
        instance_path = self._get_selected_instance_path()
        instance_name = self.instance_selector.currentData()
        if not instance_path or not instance_name:
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("msg_select_instance_required"))
            return

        if not self._weixin_available:
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("msg_channel_requires_plugin_weixin"))
            return

        try:
            ProcessManager.launch_instance_cli_with_command(
                instance_name,
                instance_path,
                ["channels", "login", "--channel", "openclaw-weixin"],
            )
            self.status_label.setText(i18n.t("msg_weixin_login_cli_launched", name=instance_name))
        except Exception as e:
            QMessageBox.critical(
                self,
                i18n.t("title_error"),
                i18n.t("msg_weixin_login_cli_launch_failed", error=str(e)),
            )

    def update_ui_texts(self):
        self.instance_label.setText(i18n.t("lbl_select_instance"))
        if self.instance_selector.count() > 0:
            self.instance_selector.setItemText(0, i18n.t("opt_select_instance"))
        self.btn_refresh.setText(i18n.t("btn_refresh"))
        self._update_channel_field_labels()
        self.discord_token.setPlaceholderText(i18n.t("ph_bot_token"))
        self.telegram_token.setPlaceholderText(i18n.t("ph_bot_token"))
        self.feishu_app_id.setPlaceholderText(i18n.t("ph_app_id"))
        self.feishu_app_secret.setPlaceholderText(i18n.t("ph_app_secret"))
        self.dingtalk_app_id.setPlaceholderText(i18n.t("ph_app_id"))
        self.dingtalk_app_secret.setPlaceholderText(i18n.t("ph_app_secret"))
        self.qq_app_id.setPlaceholderText(i18n.t("ph_app_id"))
        self.qq_app_secret.setPlaceholderText(i18n.t("ph_app_secret"))
        self.btn_weixin_login.setText(i18n.t("btn_channel_login"))
        self.btn_save.setText(i18n.t("btn_save"))
        self.refresh()
