from pathlib import Path
import subprocess
import json
from datetime import datetime

from PySide6.QtCore import QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.config import Config
from ...core.install_manager import InstallManager
from ...core.process_manager import ProcessManager
from ..i18n import i18n


class PluginInstallWorker(QThread):
    completed = Signal(str)
    error = Signal(str)

    def __init__(self, openclaw_home: Path, plugin_name: str, instance_name: str):
        super().__init__()
        self.openclaw_home = openclaw_home
        self.plugin_name = plugin_name
        self.instance_name = instance_name

    def run(self):
        log_file_path = Config.get_log_file(self.instance_name)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(log_file_path, "a", encoding="utf-8", buffering=1) as log_file:
                log_file.write("\n===== Plugin install started =====\n")
                log_file.write(f"time: {datetime.now().isoformat(timespec='seconds')}\n")
                log_file.write(f"instance: {self.instance_name}\n")
                log_file.write(f"plugin: {self.plugin_name}\n")

                if ProcessManager.get_status(self.instance_name) == "Running":
                    raise RuntimeError(i18n.t("msg_plugin_install_requires_stopped_instance"))

                env = InstallManager.get_runtime_env(
                    instance_path=self.openclaw_home,
                    instance_name=self.instance_name,
                )
                try:
                    node_cmd = InstallManager.resolve_runtime_tool(env, "node")
                except FileNotFoundError:
                    raise RuntimeError(i18n.t("msg_plugin_node_not_found"))

                command = [
                    node_cmd,
                    "openclaw.mjs",
                    "plugins",
                    "install",
                    self.plugin_name,
                ]
                log_file.write(f"cwd: {self.openclaw_home}\n")
                log_file.write(f"command: {' '.join(command)}\n")

                captured_lines = []
                process = subprocess.Popen(
                    command,
                    cwd=str(self.openclaw_home),
                    env=env,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=1,
                )

                if process.stdout is not None:
                    for raw_line in process.stdout:
                        log_file.write(raw_line)
                        line = raw_line.rstrip("\r\n")
                        if line:
                            captured_lines.append(line)

                return_code = process.wait()
                output = "\n".join(captured_lines).strip()

                if return_code != 0:
                    msg = output or i18n.t("msg_plugin_install_failed_unknown")
                    log_file.write(f"Plugin install failed (exit={return_code}): {msg}\n")
                    log_file.write("===== Plugin install failed =====\n")
                    raise RuntimeError(msg)

                log_file.write("===== Plugin install completed =====\n")
                self.completed.emit(output)
        except Exception as e:
            try:
                with open(log_file_path, "a", encoding="utf-8", buffering=1) as log_file:
                    log_file.write(f"Plugin install exception: {e}\n")
                    log_file.write("===== Plugin install aborted =====\n")
            except Exception:
                pass
            self.error.emit(str(e))


class PluginUninstallWorker(QThread):
    completed = Signal(str, bool, str)
    error = Signal(str, str, str)

    def __init__(
        self,
        openclaw_home: Path,
        instance_name: str,
        plugin_name: str,
        plugin_path: Path,
    ):
        super().__init__()
        self.openclaw_home = openclaw_home
        self.instance_name = instance_name
        self.plugin_name = plugin_name
        self.plugin_path = plugin_path

    def run(self):
        log_file_path = Config.get_log_file(self.instance_name)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(log_file_path, "a", encoding="utf-8", buffering=1) as log_file:
                log_file.write("\n===== Plugin uninstall started =====\n")
                log_file.write(f"time: {datetime.now().isoformat(timespec='seconds')}\n")
                log_file.write(f"instance: {self.instance_name}\n")
                log_file.write(f"plugin: {self.plugin_name}\n")

                if ProcessManager.get_status(self.instance_name) == "Running":
                    raise RuntimeError(i18n.t("msg_plugin_install_requires_stopped_instance"))

                env = InstallManager.get_runtime_env(
                    instance_path=self.openclaw_home,
                    instance_name=self.instance_name,
                )
                try:
                    node_cmd = InstallManager.resolve_runtime_tool(env, "node")
                except FileNotFoundError:
                    raise RuntimeError(i18n.t("msg_plugin_node_not_found"))

                command = [
                    node_cmd,
                    "openclaw.mjs",
                    "plugins",
                    "uninstall",
                    self.plugin_name,
                ]
                log_file.write(f"cwd: {self.openclaw_home}\n")
                log_file.write(f"command: {' '.join(command)}\n")

                captured_lines = []
                process = subprocess.Popen(
                    command,
                    cwd=str(self.openclaw_home),
                    env=env,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=1,
                )

                if process.stdout is not None:
                    for raw_line in process.stdout:
                        log_file.write(raw_line)
                        line = raw_line.rstrip("\r\n")
                        if line:
                            captured_lines.append(line)

                return_code = process.wait()
                output = "\n".join(captured_lines).strip()

                if return_code != 0:
                    msg = output or i18n.t("msg_uninstall_failed", name=self.plugin_name, error="unknown")
                    log_file.write(f"Plugin uninstall failed (exit={return_code}): {msg}\n")
                    log_file.write("===== Plugin uninstall failed =====\n")
                    raise RuntimeError(msg)

                log_file.write("===== Plugin uninstall completed =====\n")

            self.completed.emit(self.plugin_name, self.plugin_path.exists(), str(self.plugin_path))
        except Exception as e:
            try:
                with open(log_file_path, "a", encoding="utf-8", buffering=1) as log_file:
                    log_file.write(f"Plugin uninstall exception: {e}\n")
                    log_file.write("===== Plugin uninstall aborted =====\n")
            except Exception:
                pass
            self.error.emit(self.plugin_name, str(e), str(self.plugin_path))


class PluginPanel(QWidget):
    RECOMMENDED_PLUGINS = [
        {
            "name": "@dingtalk-real-ai/dingtalk-connector",
            "url": "https://github.com/DingTalk-Real-AI/dingtalk-openclaw-connector",
            "description_key": "desc_plugin_dingtalk",
        },
        {
            "name": "@tencent-weixin/openclaw-weixin",
            "url": "https://github.com/Tencent/openclaw-weixin",
            "description_key": "desc_plugin_weixin",
        },
        {
            "name": "@xquik/tweetclaw",
            "url": "https://github.com/Xquik-dev/tweetclaw",
            "description_key": "desc_plugin_tweetclaw",
        },
    ]

    def __init__(self):
        super().__init__()
        self.install_worker = None
        self.uninstall_worker = None
        self.recommended_install_buttons = {}

        self.layout = QVBoxLayout(self)
        
        instance_row = QHBoxLayout()
        self.instance_label = QLabel(i18n.t("lbl_select_instance"))
        instance_row.addWidget(self.instance_label)

        self.instance_selector = QComboBox()
        self.instance_selector.currentIndexChanged.connect(self._on_instance_changed)
        instance_row.addWidget(self.instance_selector)

        self.btn_refresh = QPushButton(i18n.t("btn_refresh"))
        self.btn_refresh.clicked.connect(self.refresh_plugins)
        instance_row.addWidget(self.btn_refresh)
        self.layout.addLayout(instance_row)

        self.plugin_tree = QTreeWidget()
        self.plugin_tree.setColumnCount(3)
        self.plugin_tree.setRootIsDecorated(True)
        self.layout.addWidget(self.plugin_tree)

        self.status_label = QLabel(i18n.t("status_ready"))
        self.layout.addWidget(self.status_label)

        self.install_progress = QProgressBar()
        self.install_progress.setVisible(False)
        self.install_progress.setTextVisible(False)
        self.layout.addWidget(self.install_progress)

        self.uninstall_progress = QProgressBar()
        self.uninstall_progress.setVisible(False)
        self.uninstall_progress.setTextVisible(True)
        self.uninstall_progress.setFormat(i18n.t("progress_delete_running"))
        self.layout.addWidget(self.uninstall_progress)

        install_row = QHBoxLayout()
        self.plugin_input = QLineEdit()
        self.plugin_input.setPlaceholderText(i18n.t("ph_plugin_name"))
        install_row.addWidget(self.plugin_input)

        self.btn_install = QPushButton(i18n.t("btn_install_plugin"))
        self.btn_install.clicked.connect(self.install_from_input)
        install_row.addWidget(self.btn_install)

        self.layout.addLayout(install_row)

        self.recommended_group = QGroupBox(i18n.t("section_recommended_plugins"))
        self.recommended_layout = QVBoxLayout(self.recommended_group)
        self.layout.addWidget(self.recommended_group)
        self._build_recommended_rows()

        self.update_ui_texts()
        self._load_instances()
        self.refresh_plugins()

    def _build_recommended_rows(self):
        while self.recommended_layout.count():
            item = self.recommended_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.recommended_install_buttons = {}

        for plugin in self.RECOMMENDED_PLUGINS:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)

            text_widget = QWidget()
            text_layout = QVBoxLayout(text_widget)
            text_layout.setContentsMargins(0, 0, 0, 0)
            text_layout.setSpacing(2)

            label = QLabel(plugin["name"])
            text_layout.addWidget(label)

            description = QLabel(i18n.t(plugin["description_key"]))
            description.setWordWrap(True)
            text_layout.addWidget(description)

            row_layout.addWidget(text_widget, 1)
            row_layout.addStretch()

            btn_install = QPushButton(i18n.t("btn_install"))
            btn_install.clicked.connect(
                lambda checked=False, package_name=plugin["name"]: self.start_recommended_install(package_name)
            )
            row_layout.addWidget(btn_install)
            self.recommended_install_buttons[plugin["name"]] = btn_install

            btn_help = QPushButton(i18n.t("btn_help"))
            btn_help.clicked.connect(
                lambda checked=False, url=plugin["url"]: QDesktopServices.openUrl(QUrl(url))
            )
            row_layout.addWidget(btn_help)

            self.recommended_layout.addWidget(row_widget)

        self._update_recommended_controls_state()

    def _update_recommended_controls_state(self):
        enable_install = (
            self._has_selected_instance()
            and self.install_worker is None
            and self.uninstall_worker is None
        )
        for plugin_name, button in self.recommended_install_buttons.items():
            is_installed = self._is_recommended_plugin_installed(plugin_name)
            button.setEnabled(enable_install and (not is_installed))

    def _is_recommended_plugin_installed(self, plugin_name: str) -> bool:
        normalized = plugin_name.strip().lower()
        if not normalized:
            return False

        install_records = self._read_install_records()
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

    def _read_install_records(self) -> dict:
        instance_path = self._get_selected_instance_path()
        if not instance_path:
            return {}

        installs_path = instance_path / ".openclaw" / "plugins" / "installs.json"
        if not installs_path.exists():
            return {}

        try:
            loaded = json.loads(installs_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

        if not isinstance(loaded, dict):
            return {}

        install_records = loaded.get("installRecords")
        return install_records if isinstance(install_records, dict) else {}

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
        self._update_install_controls_state()

    def _on_instance_changed(self):
        self._update_install_controls_state()
        self.refresh_plugins()

    def _has_selected_instance(self) -> bool:
        return bool(self.instance_selector.currentData())

    def _update_install_controls_state(self):
        enable_install = self._has_selected_instance() and self.install_worker is None and self.uninstall_worker is None
        self.btn_install.setEnabled(enable_install)
        self._update_recommended_controls_state()

    def _get_selected_instance_path(self) -> Path | None:
        instance_name = self.instance_selector.currentData()
        if not instance_name:
            return None
        return Config.get_instance_path(instance_name)

    def _detect_openclaw_home(self) -> Path:
        instance_path = self._get_selected_instance_path()
        if not instance_path:
            raise FileNotFoundError(i18n.t("msg_select_instance_required"))
        if (instance_path / "openclaw.mjs").exists():
            return instance_path
        raise FileNotFoundError(i18n.t("msg_openclaw_home_not_found"))

    def refresh_plugins(self):
        self.plugin_tree.clear()
        self.plugin_tree.setHeaderLabels([
            i18n.t("col_plugin_name"),
            i18n.t("col_plugin_version"),
            i18n.t("col_plugin_action"),
        ])

        selected_name = self.instance_selector.currentData()
        self._load_instances(selected_name=selected_name)

        instance_path = self._get_selected_instance_path()
        if not instance_path:
            self.status_label.setText(i18n.t("msg_select_instance_required"))
            return
        if not instance_path.exists():
            self.status_label.setText(i18n.t("msg_instance_not_found"))
            return

        install_records = self._read_install_records()
        if not install_records:
            empty_item = QTreeWidgetItem([i18n.t("status_empty"), "", ""])
            self.plugin_tree.addTopLevelItem(empty_item)
            self.status_label.setText(i18n.t("status_ready"))
            self._update_recommended_controls_state()
            return

        rows = []
        unknown_path = instance_path / ".openclaw" / "plugins" / "unknown-install-path"
        for record_key, record in install_records.items():
            if not isinstance(record, dict):
                continue

            uninstall_name = ""
            for field in ("resolvedName", "spec", "name", "packageName"):
                value = record.get(field)
                if isinstance(value, str) and value.strip():
                    uninstall_name = value.strip()
                    break
            if not uninstall_name and isinstance(record_key, str):
                uninstall_name = record_key.strip()
            if not uninstall_name:
                continue

            # determine version
            version = ""
            for vf in ("resolvedVersion", "version", "packageVersion", "resolvedSpec"):
                v = record.get(vf)
                if isinstance(v, str) and v.strip():
                    if vf == "resolvedSpec" and "@" in v:
                        parts = v.rsplit("@", 1)
                        if len(parts) == 2 and parts[1].strip():
                            version = parts[1].strip()
                        else:
                            version = v.strip()
                    else:
                        version = v.strip()
                    break

            install_path_value = record.get("installPath")
            install_path = Path(install_path_value) if isinstance(install_path_value, str) and install_path_value else unknown_path
            rows.append((uninstall_name, version, install_path))

        if not rows:
            empty_item = QTreeWidgetItem([i18n.t("status_empty"), "", ""])
            self.plugin_tree.addTopLevelItem(empty_item)
            self.status_label.setText(i18n.t("status_ready"))
            self._update_recommended_controls_state()
            return

        for display_name, version, install_path in sorted(rows, key=lambda x: x[0].lower()):
            plugin_item = QTreeWidgetItem([display_name, version, ""])
            self.plugin_tree.addTopLevelItem(plugin_item)
            self._add_uninstall_button(plugin_item, display_name, install_path)

        self.status_label.setText(i18n.t("status_ready"))
        self._update_recommended_controls_state()

    def _add_uninstall_button(self, item: QTreeWidgetItem, plugin_name: str, plugin_path: Path):
        button = QPushButton(i18n.t("btn_uninstall"))
        button.clicked.connect(lambda checked=False, n=plugin_name, p=plugin_path: self.uninstall_plugin(n, p))
        self.plugin_tree.setItemWidget(item, 2, button)

    def uninstall_plugin(self, plugin_name: str, plugin_path: Path):
        if self.uninstall_worker:
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("msg_plugin_uninstall_busy"))
            return
        if self.install_worker:
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("msg_plugin_install_busy"))
            return

        if not plugin_path.exists() or not plugin_path.is_dir():
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("msg_uninstall_missing"))
            self.refresh_plugins()
            return

        reply = QMessageBox.warning(
            self,
            i18n.t("title_confirm"),
            i18n.t("msg_confirm_uninstall", name=plugin_name),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        instance_name = self.instance_selector.currentData()
        if not instance_name:
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("msg_select_instance_required"))
            return

        try:
            openclaw_home = self._detect_openclaw_home()
        except Exception as e:
            QMessageBox.critical(self, i18n.t("title_error"), str(e))
            return

        if ProcessManager.get_status(instance_name) == "Running":
            QMessageBox.warning(
                self,
                i18n.t("title_warning"),
                i18n.t("msg_plugin_install_requires_stopped_instance"),
            )
            return

        self.status_label.setText(i18n.t("msg_plugin_uninstalling", name=plugin_name))
        self._set_uninstalling_state(True)

        worker = PluginUninstallWorker(
            openclaw_home=openclaw_home,
            instance_name=instance_name,
            plugin_name=plugin_name,
            plugin_path=plugin_path,
        )
        try:
            worker.setParent(self)
            worker.finished.connect(worker.deleteLater)
        except Exception:
            pass

        worker.completed.connect(self.on_uninstall_finished)
        worker.error.connect(self.on_uninstall_error)
        worker.finished.connect(self._cleanup_uninstall_worker)
        worker.start()
        self.uninstall_worker = worker

    def on_uninstall_finished(self, plugin_name: str, residual_exists: bool, plugin_path_str: str):
        self._set_uninstalling_state(False)

        plugin_path = Path(plugin_path_str)
        if residual_exists:
            self._show_manual_cleanup_dialog(
                plugin_path,
                i18n.t("msg_uninstall_manual_cleanup_detected", name=plugin_name, path=str(plugin_path)),
            )
            self.status_label.setText(i18n.t("title_warning"))
        else:
            self.status_label.setText(i18n.t("msg_uninstall_success", name=plugin_name))

        self.refresh_plugins()

    def on_uninstall_error(self, plugin_name: str, error_msg: str, plugin_path_str: str):
        self._set_uninstalling_state(False)

        plugin_path = Path(plugin_path_str)
        if plugin_path.exists():
            self._show_manual_cleanup_dialog(
                plugin_path,
                i18n.t("msg_uninstall_manual_cleanup_hint", name=plugin_name, path=str(plugin_path), error=error_msg),
            )
        else:
            QMessageBox.critical(
                self,
                i18n.t("title_error"),
                i18n.t("msg_uninstall_failed", name=plugin_name, error=error_msg),
            )

        self.status_label.setText(i18n.t("title_warning"))
        self.refresh_plugins()

    def _show_manual_cleanup_dialog(self, path: Path, message: str):
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Warning)
        dialog.setWindowTitle(i18n.t("title_warning"))
        dialog.setText(message)
        btn_open = dialog.addButton(i18n.t("btn_open_folder"), QMessageBox.ActionRole)
        dialog.addButton(QMessageBox.Close)
        dialog.exec()

        if dialog.clickedButton() == btn_open and path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def install_from_input(self):
        plugin_name = self.plugin_input.text().strip()
        if not plugin_name:
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("msg_plugin_name_required"))
            return
        self.start_install(plugin_name)

    def start_recommended_install(self, plugin_name: str):
        self.start_install(plugin_name)

    def start_install(self, plugin_name: str):
        if self.install_worker:
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("msg_plugin_install_busy"))
            return

        if not self._get_selected_instance_path():
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("msg_select_instance_required"))
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

        self._set_installing_state(True)
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

        worker.completed.connect(lambda output, name=plugin_name: self.on_install_success(name, output))
        worker.error.connect(lambda error, name=plugin_name: self.on_install_error(name, error))
        worker.finished.connect(self._cleanup_install_worker)
        worker.start()
        self.install_worker = worker

    def on_install_success(self, plugin_name: str, output: str):
        self._set_installing_state(False)

        config_apply_error = None
        try:
            self._apply_plugin_default_channel_config(plugin_name)
        except Exception as e:
            config_apply_error = str(e)

        self.status_label.setText(i18n.t("msg_plugin_install_success", name=plugin_name))
        self.refresh_plugins()

        if config_apply_error:
            QMessageBox.warning(
                self,
                i18n.t("title_warning"),
                f"{i18n.t('msg_plugin_install_success', name=plugin_name)}\n\n"
                f"写入默认 channels 配置失败：{config_apply_error}",
            )

        if output:
            preview = "\n".join(output.splitlines()[-10:])
            QMessageBox.information(
                self,
                i18n.t("title_success"),
                i18n.t("msg_plugin_install_output", name=plugin_name, output=preview),
            )
        else:
            QMessageBox.information(
                self,
                i18n.t("title_success"),
                i18n.t("msg_plugin_install_success", name=plugin_name),
            )

    def on_install_error(self, plugin_name: str, error: str):
        self._set_installing_state(False)
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

    def _cleanup_uninstall_worker(self):
        worker = self.uninstall_worker
        if worker is None:
            return
        self.uninstall_worker = None
        worker.deleteLater()

    def _apply_plugin_default_channel_config(self, plugin_name: str):
        normalized = plugin_name.strip().lower()
        default_entry = None

        if normalized == "qqbot" or normalized.endswith("/qqbot"):
            default_entry = (
                "qqbot",
                {
                    "enabled": True,
                    "appId": "Your AppID",
                    "clientSecret": "Your AppSecret",
                },
            )
        elif normalized == "dingtalk-connector" or normalized.endswith("/dingtalk-connector"):
            instance_path = self._get_selected_instance_path()
            instance_name = self.instance_selector.currentData()
            if not instance_path or not instance_name:
                return

            gateway_token = InstallManager.get_instance_gateway_token(instance_path, instance_name)
            default_entry = (
                "dingtalk-connector",
                {
                    "enabled": True,
                    "clientId": "Your client id",
                    "clientSecret": "your secret",
                    "gatewayToken": gateway_token,
                },
            )

        if default_entry is None:
            return

        instance_path = self._get_selected_instance_path()
        if not instance_path:
            return

        config_path = instance_path / ".openclaw" / "openclaw.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        config_data = {}
        if config_path.exists():
            loaded = json.loads(config_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                config_data = loaded

        channels_obj = config_data.get("channels")
        if not isinstance(channels_obj, dict):
            channels_obj = {}

        channel_key, defaults = default_entry
        existing = channels_obj.get(channel_key)
        if not isinstance(existing, dict):
            existing = {}

        merged = dict(existing)
        for key, value in defaults.items():
            if key == "enabled":
                merged[key] = True
            elif key not in merged:
                merged[key] = value

        channels_obj[channel_key] = merged
        config_data["channels"] = channels_obj
        config_path.write_text(json.dumps(config_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def _set_installing_state(self, installing: bool):
        self.btn_install.setEnabled((not installing) and self._has_selected_instance() and self.uninstall_worker is None)
        self.btn_refresh.setEnabled(not installing)
        self.instance_selector.setEnabled(not installing)
        self.plugin_tree.setEnabled(not installing)
        for button in self.recommended_install_buttons.values():
            button.setEnabled((not installing) and self._has_selected_instance())
        self.install_progress.setVisible(installing)
        if installing:
            self.install_progress.setRange(0, 0)
        else:
            self.install_progress.setRange(0, 1)
            self.install_progress.setValue(0)

    def _set_uninstalling_state(self, uninstalling: bool):
        self.btn_install.setEnabled((not uninstalling) and self._has_selected_instance() and self.install_worker is None)
        self.btn_refresh.setEnabled(not uninstalling)
        self.instance_selector.setEnabled(not uninstalling)
        self.plugin_input.setEnabled(not uninstalling)
        self.plugin_tree.setEnabled(not uninstalling)
        for button in self.recommended_install_buttons.values():
            button.setEnabled((not uninstalling) and self._has_selected_instance() and self.install_worker is None)

        self.uninstall_progress.setVisible(uninstalling)
        if uninstalling:
            self.uninstall_progress.setRange(0, 0)
            self.uninstall_progress.setFormat(i18n.t("progress_delete_running"))
        else:
            self.uninstall_progress.setRange(0, 1)
            self.uninstall_progress.setValue(0)

    def update_ui_texts(self):
        self.instance_label.setText(i18n.t("lbl_select_instance"))
        if self.instance_selector.count() > 0:
            self.instance_selector.setItemText(0, i18n.t("opt_select_instance"))
        self.plugin_input.setPlaceholderText(i18n.t("ph_plugin_name"))
        self.btn_install.setText(i18n.t("btn_install_plugin"))
        self.btn_refresh.setText(i18n.t("btn_refresh"))
        self.recommended_group.setTitle(i18n.t("section_recommended_plugins"))
        self._build_recommended_rows()
        self.refresh_plugins()

    def shutdown(self):
        worker = self.install_worker
        if worker and worker.isRunning():
            worker.requestInterruption()
            worker.wait(2000)
            if worker.isRunning():
                worker.terminate()
                worker.wait(1000)
        self.install_worker = None

        uninstall_worker = self.uninstall_worker
        if uninstall_worker and uninstall_worker.isRunning():
            uninstall_worker.requestInterruption()
            uninstall_worker.wait(2000)
            if uninstall_worker.isRunning():
                uninstall_worker.terminate()
                uninstall_worker.wait(1000)
        self.uninstall_worker = None
