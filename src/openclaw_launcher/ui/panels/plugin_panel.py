from pathlib import Path
import shutil
import subprocess

from PySide6.QtCore import QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.config import Config
from ...core.install_manager import InstallManager
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
        try:
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
            result = subprocess.run(
                command,
                cwd=str(self.openclaw_home),
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
            output = output.strip()

            if result.returncode != 0:
                msg = output or i18n.t("msg_plugin_install_failed_unknown")
                raise RuntimeError(msg)

            self.completed.emit(output)
        except Exception as e:
            self.error.emit(str(e))


class PluginPanel(QWidget):
    RECOMMENDED_PLUGINS = [
        {
            "name": "@m1heng-clawd/feishu",
            "url": "https://github.com/m1heng/clawdbot-feishu",
        },
        {
            "name": "@sliverp/qqbot",
            "url": "https://github.com/sliverp/qqbot",
        },
    ]

    def __init__(self):
        super().__init__()
        self.install_worker = None
        self.recommended_install_buttons = []

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

        self.recommended_group = QGroupBox()
        self.recommended_layout = QVBoxLayout(self.recommended_group)
        self.layout.addWidget(self.recommended_group)

        self.status_label = QLabel(i18n.t("status_ready"))
        self.layout.addWidget(self.status_label)

        install_row = QHBoxLayout()
        self.plugin_input = QLineEdit()
        self.plugin_input.setPlaceholderText(i18n.t("ph_plugin_name"))
        install_row.addWidget(self.plugin_input)

        self.btn_install = QPushButton(i18n.t("btn_install_plugin"))
        self.btn_install.clicked.connect(self.install_from_input)
        install_row.addWidget(self.btn_install)

        self.layout.addLayout(install_row)

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

        self.recommended_install_buttons = []

        for plugin in self.RECOMMENDED_PLUGINS:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)

            label = QLabel(plugin["name"])
            row_layout.addWidget(label)
            row_layout.addStretch()

            btn_install = QPushButton(i18n.t("btn_install"))
            btn_install.clicked.connect(
                lambda checked=False, package_name=plugin["name"]: self.start_install(package_name)
            )
            btn_install.setEnabled(self._has_selected_instance())
            row_layout.addWidget(btn_install)
            self.recommended_install_buttons.append(btn_install)

            btn_help = QPushButton(i18n.t("btn_help"))
            btn_help.clicked.connect(
                lambda checked=False, url=plugin["url"]: QDesktopServices.openUrl(QUrl(url))
            )
            row_layout.addWidget(btn_help)

            self.recommended_layout.addWidget(row_widget)

    def _candidate_extension_dirs(self, base_dir: Path):
        return [
            (".openclaw/extensions", (base_dir / ".openclaw" / "extensions").resolve()),
            ("extensions/", (base_dir / "extensions").resolve()),
        ]

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
        enable_install = self._has_selected_instance() and self.install_worker is None
        self.btn_install.setEnabled(enable_install)
        for button in self.recommended_install_buttons:
            button.setEnabled(enable_install)

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
            i18n.t("col_plugin_source"),
            i18n.t("col_plugin_name"),
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

        for source_label, source_dir in self._candidate_extension_dirs(instance_path):
            source_item = QTreeWidgetItem([source_label, str(source_dir)])
            self.plugin_tree.addTopLevelItem(source_item)

            if not source_dir.exists() or not source_dir.is_dir():
                empty_item = QTreeWidgetItem([i18n.t("status_not_found"), ""])
                source_item.addChild(empty_item)
                continue

            found = False
            for child in sorted(source_dir.iterdir(), key=lambda p: p.name.lower()):
                if child.is_dir():
                    plugin_item = QTreeWidgetItem(["", child.name, ""])
                    source_item.addChild(plugin_item)
                    self._add_uninstall_button(plugin_item, child)
                    found = True

            if not found:
                empty_item = QTreeWidgetItem([i18n.t("status_empty"), ""])
                source_item.addChild(empty_item)

            source_item.setExpanded(True)

        self.status_label.setText(i18n.t("status_ready"))

    def _add_uninstall_button(self, item: QTreeWidgetItem, plugin_path: Path):
        button = QPushButton(i18n.t("btn_uninstall"))
        button.clicked.connect(lambda checked=False, p=plugin_path: self.uninstall_plugin(p))
        self.plugin_tree.setItemWidget(item, 2, button)

    def uninstall_plugin(self, plugin_path: Path):
        if not plugin_path.exists() or not plugin_path.is_dir():
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("msg_uninstall_missing"))
            self.refresh_plugins()
            return

        reply = QMessageBox.warning(
            self,
            i18n.t("title_confirm"),
            i18n.t("msg_confirm_uninstall", name=plugin_path.name),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            shutil.rmtree(plugin_path)
            self.status_label.setText(i18n.t("msg_uninstall_success", name=plugin_path.name))
            self.refresh_plugins()
        except Exception as exc:
            QMessageBox.critical(
                self,
                i18n.t("title_error"),
                i18n.t("msg_uninstall_failed", name=plugin_path.name, error=str(exc)),
            )

    def install_from_input(self):
        plugin_name = self.plugin_input.text().strip()
        if not plugin_name:
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("msg_plugin_name_required"))
            return
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
        worker.completed.connect(lambda output, name=plugin_name: self.on_install_success(name, output))
        worker.error.connect(lambda error, name=plugin_name: self.on_install_error(name, error))
        worker.start()
        self.install_worker = worker

    def on_install_success(self, plugin_name: str, output: str):
        self._set_installing_state(False)
        self.install_worker = None
        self.status_label.setText(i18n.t("msg_plugin_install_success", name=plugin_name))
        self.refresh_plugins()

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
        self.install_worker = None
        self.status_label.setText(i18n.t("msg_plugin_install_failed_short", name=plugin_name))
        QMessageBox.critical(
            self,
            i18n.t("title_error"),
            i18n.t("msg_plugin_install_failed", name=plugin_name, error=error),
        )

    def _set_installing_state(self, installing: bool):
        self.btn_install.setEnabled((not installing) and self._has_selected_instance())
        self.btn_refresh.setEnabled(not installing)
        self.instance_selector.setEnabled(not installing)
        for button in self.recommended_install_buttons:
            button.setEnabled((not installing) and self._has_selected_instance())

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
