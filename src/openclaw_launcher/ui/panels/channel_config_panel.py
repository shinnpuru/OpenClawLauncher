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
from .plugin_panel import PluginPanel, PluginInstallWorker

class ChannelConfigPanel(QWidget):
    DINGTALK_PLUGIN = "@dingtalk-real-ai/dingtalk-connector"
    WEIXIN_PLUGIN = "@tencent-weixin/openclaw-weixin"
    FEISHU_PLUGIN = "@openclaw/feishu"
    QQ_PLUGIN = "@openclaw/qqbot"

    def __init__(self):
        super().__init__()
        self.install_worker = None
        self._dingtalk_available = False
        self._weixin_available = False
        self._feishu_available = False
        self._qqbot_available = False

        self.main_layout = QVBoxLayout(self)

        instance_row = QHBoxLayout()
        self.instance_label = QLabel(i18n.t("lbl_select_instance"))
        instance_row.addWidget(self.instance_label)

        self.instance_selector = QComboBox()
        self.instance_selector.currentIndexChanged.connect(self._on_instance_changed)
        instance_row.addWidget(self.instance_selector)

        self.btn_refresh = QPushButton(i18n.t("btn_refresh"))
        self.btn_refresh.clicked.connect(self.refresh)
        instance_row.addWidget(self.btn_refresh)
        self.main_layout.addLayout(instance_row)

        self.status_label = QLabel(i18n.t("status_ready"))
        self.main_layout.addWidget(self.status_label)

        self.config_container = QWidget()
        self.main_layout.addWidget(self.config_container)

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
        self.feishu_app_secret.setEchoMode(QLineEdit.EchoMode.Password)
        self.feishu_app_id.setPlaceholderText(i18n.t("ph_app_id"))
        self.feishu_app_secret.setPlaceholderText(i18n.t("ph_app_secret"))
        self.feishu_app_id_label = QLabel()
        self.feishu_app_secret_label = QLabel()
        self.channel_form.addRow(self.feishu_app_id_label, self.feishu_app_id)
        self.channel_form.addRow(self.feishu_app_secret_label, self.feishu_app_secret)
        self.feishu_hint_layout = QHBoxLayout()
        self.feishu_hint = QLabel("")
        self.feishu_hint.setStyleSheet("color: orange;")
        self.feishu_hint.setWordWrap(True)
        self.btn_install_feishu = QPushButton(i18n.t("btn_install"))
        self.btn_install_feishu.clicked.connect(lambda: self.start_install(self.FEISHU_PLUGIN))
        self.btn_install_feishu.hide()
        self.feishu_hint_layout.addWidget(self.feishu_hint)
        self.feishu_hint_layout.addWidget(self.btn_install_feishu)
        self.feishu_hint_layout.addStretch()
        group_layout.addLayout(self.feishu_hint_layout)

        self.qq_app_id = QLineEdit()
        self.qq_app_secret = QLineEdit()
        self.qq_app_secret.setEchoMode(QLineEdit.EchoMode.Password)
        self.qq_app_id.setPlaceholderText(i18n.t("ph_app_id"))
        self.qq_app_secret.setPlaceholderText(i18n.t("ph_app_secret"))
        self.qq_app_id_label = QLabel()
        self.qq_app_secret_label = QLabel()
        self.channel_form.addRow(self.qq_app_id_label, self.qq_app_id)
        self.channel_form.addRow(self.qq_app_secret_label, self.qq_app_secret)
        self.qq_hint_layout = QHBoxLayout()
        self.qq_hint = QLabel("")
        self.qq_hint.setStyleSheet("color: orange;")
        self.qq_hint.setWordWrap(True)
        self.btn_install_qq = QPushButton(i18n.t("btn_install"))
        self.btn_install_qq.clicked.connect(lambda: self.start_install(self.QQ_PLUGIN))
        self.btn_install_qq.hide()
        self.qq_hint_layout.addWidget(self.qq_hint)
        self.qq_hint_layout.addWidget(self.btn_install_qq)
        self.qq_hint_layout.addStretch()
        group_layout.addLayout(self.qq_hint_layout)

        self.dingtalk_app_id = QLineEdit()
        self.dingtalk_app_secret = QLineEdit()
        self.dingtalk_app_secret.setEchoMode(QLineEdit.EchoMode.Password)
        self.dingtalk_app_id.setPlaceholderText(i18n.t("ph_app_id"))
        self.dingtalk_app_secret.setPlaceholderText(i18n.t("ph_app_secret"))
        self.dingtalk_app_id_label = QLabel()
        self.dingtalk_app_secret_label = QLabel()
        self.channel_form.addRow(self.dingtalk_app_id_label, self.dingtalk_app_id)
        self.channel_form.addRow(self.dingtalk_app_secret_label, self.dingtalk_app_secret)
        self.dingtalk_hint_layout = QHBoxLayout()
        self.dingtalk_hint = QLabel("")
        self.dingtalk_hint.setStyleSheet("color: orange;")
        self.dingtalk_hint.setWordWrap(True)
        self.btn_install_dingtalk = QPushButton(i18n.t("btn_install"))
        self.btn_install_dingtalk.clicked.connect(lambda: self.start_install(self.DINGTALK_PLUGIN))
        self.btn_install_dingtalk.hide()
        self.dingtalk_hint_layout.addWidget(self.dingtalk_hint)
        self.dingtalk_hint_layout.addWidget(self.btn_install_dingtalk)
        self.dingtalk_hint_layout.addStretch()
        group_layout.addLayout(self.dingtalk_hint_layout)

        self.weixin_login_row = QHBoxLayout()
        self.weixin_login_label = QLabel()
        self.weixin_login_row.addWidget(self.weixin_login_label)
        self.weixin_login_row.addStretch()
        self.btn_weixin_login = QPushButton(i18n.t("btn_channel_login"))
        self.btn_weixin_login.clicked.connect(self.login_weixin_channel)
        self.weixin_login_row.addWidget(self.btn_weixin_login)
        self.channel_form.addRow(self.weixin_login_row)
        self.weixin_hint_layout = QHBoxLayout()
        self.weixin_hint = QLabel("")
        self.weixin_hint.setStyleSheet("color: orange;")
        self.weixin_hint.setWordWrap(True)
        self.btn_install_weixin = QPushButton(i18n.t("btn_install"))
        self.btn_install_weixin.clicked.connect(lambda: self.start_install(self.WEIXIN_PLUGIN))
        self.btn_install_weixin.hide()
        self.weixin_hint_layout.addWidget(self.weixin_hint)
        self.weixin_hint_layout.addWidget(self.btn_install_weixin)
        self.weixin_hint_layout.addStretch()
        group_layout.addLayout(self.weixin_hint_layout)

        self.btn_save = QPushButton(i18n.t("btn_save"))
        self.btn_save.clicked.connect(self.save_channel_config)
        self.main_layout.addWidget(self.btn_save)

        self.main_layout.addStretch()

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

    def _set_field_pair_enabled(self, app_id_edit: QLineEdit, app_secret_edit: QLineEdit, enabled: bool):
        app_id_edit.setEnabled(enabled)
        app_secret_edit.setEnabled(enabled)

    def _update_plugin_gate_state(self):
        instance_path = self._get_selected_instance_path()
        self._dingtalk_available = PluginPanel.is_plugin_installed(instance_path, self.DINGTALK_PLUGIN)
        self._weixin_available = PluginPanel.is_plugin_installed(instance_path, self.WEIXIN_PLUGIN)
        self._feishu_available = PluginPanel.is_plugin_installed(instance_path, self.FEISHU_PLUGIN)
        self._qqbot_available = PluginPanel.is_plugin_installed(instance_path, self.QQ_PLUGIN)

        self._set_field_pair_enabled(self.dingtalk_app_id, self.dingtalk_app_secret, self._dingtalk_available)
        self._set_field_pair_enabled(self.feishu_app_id, self.feishu_app_secret, self._feishu_available)
        self._set_field_pair_enabled(self.qq_app_id, self.qq_app_secret, self._qqbot_available)
        self.btn_weixin_login.setEnabled(self._weixin_available)

        self.dingtalk_hint.setText(
            "" if self._dingtalk_available else i18n.t("msg_channel_requires_plugin_dingtalk")
        )
        self.feishu_hint.setText(
            "" if self._feishu_available else i18n.t("msg_channel_requires_plugin_feishu")
        )
        self.qq_hint.setText(
            "" if self._qqbot_available else i18n.t("msg_channel_requires_plugin_qq")
        )
        self.weixin_hint.setText(
            "" if self._weixin_available else i18n.t("msg_channel_requires_plugin_weixin")
        )

        self.btn_install_dingtalk.setVisible(not self._dingtalk_available)
        self.btn_install_feishu.setVisible(not self._feishu_available)
        self.btn_install_qq.setVisible(not self._qqbot_available)
        self.btn_install_weixin.setVisible(not self._weixin_available)

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
            obj = channels.get(active_key)
            if isinstance(obj, dict):
                telegram_obj = obj
            if telegram_obj is None:
                telegram_obj = {}
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
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
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
                "telegram",
                {
                    "enabled": True,
                    "botToken": self.telegram_token.text().strip(),
                    "dmPolicy": "open",
                    "allowFrom": ["*"]
                },
            )
            skipped = []
            if self._feishu_available:
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
            else:
                skipped.append("Feishu")

            if self._qqbot_available:
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
            else:
                skipped.append("QQBot")

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
            else:
                skipped.append("DingTalk")

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

    def _detect_openclaw_home(self) -> Path:
        instance_path = self._get_selected_instance_path()
        if not instance_path:
            raise FileNotFoundError(i18n.t("msg_select_instance_required"))
        if (instance_path / "openclaw.mjs").exists():
            return instance_path
        raise FileNotFoundError(i18n.t("msg_openclaw_home_not_found"))

    def start_install(self, plugin_name: str):
        if self.install_worker:
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("msg_plugin_install_busy"))
            return

        instance_name = self.instance_selector.currentData()
        if not instance_name:
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("msg_select_instance_required"))
            return

        if ProcessManager.get_status(instance_name) == "Running":
            QMessageBox.warning(
                self,
                i18n.t("title_warning"),
                i18n.t("msg_plugin_install_requires_stopped_instance"),
            )
            return

        try:
            openclaw_home = self._detect_openclaw_home()
        except Exception as e:
            QMessageBox.critical(self, i18n.t("title_error"), str(e))
            return

        self.status_label.setText(i18n.t("msg_plugin_installing", name=plugin_name))

        worker = PluginInstallWorker(
            openclaw_home=openclaw_home,
            plugin_name=plugin_name,
            instance_name=instance_name,
        )
        try:
            worker.setParent(self)
            worker.finished.connect(worker.deleteLater)
        except Exception:
            pass

        worker.completed.connect(lambda output: self._on_install_completed(plugin_name, output))
        worker.error.connect(lambda error: self._on_install_error(plugin_name, error))
        worker.finished.connect(self._cleanup_install_worker)
        worker.start()
        self.install_worker = worker

    def _on_install_completed(self, plugin_name: str, output: str):
        self.status_label.setText(i18n.t("msg_plugin_install_success", name=plugin_name))
        self._update_plugin_gate_state()
        QMessageBox.information(
            self,
            i18n.t("title_success"),
            i18n.t("msg_plugin_install_success", name=plugin_name),
        )

    def _on_install_error(self, plugin_name: str, error: str):
        self.status_label.setText(i18n.t("msg_plugin_install_failed_short", name=plugin_name))
        QMessageBox.critical(
            self,
            i18n.t("title_error"),
            i18n.t("msg_plugin_install_failed", name=plugin_name, error=error),
        )

    def _cleanup_install_worker(self):
        worker = self.install_worker
        if worker is None:
            return
        self.install_worker = None
        worker.deleteLater()

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
