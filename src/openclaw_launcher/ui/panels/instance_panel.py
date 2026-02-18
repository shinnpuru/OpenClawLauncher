from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QListWidget, QListWidgetItem, QLabel, QInputDialog, QMessageBox)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, Slot, QUrl
from PySide6.QtGui import QDesktopServices
from urllib.parse import urlencode
from ...core.config import Config
from ...core.process_manager import ProcessManager
from ...core.install_manager import InstallManager
from ...core.runtime_manager import RuntimeManager
from ..i18n import i18n
import shutil

class InstanceCreateWorker(QThread):
    finished = Signal()
    error = Signal(str)

    def __init__(self, name, port):
        super().__init__()
        self.name = name
        self.port = port

    def run(self):
        try:
            # InstallManager now automatically picks up the runtime environments
            # and copies from the downloaded OpenClaw runtime.
            InstallManager.complete_install(self.name, self.port)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

class InstancePanel(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        
        # Header
        self.header_label = QLabel(i18n.t("header_clean_launcher"))
        self.layout.addWidget(self.header_label)
        
        # Instance List
        self.instance_list = QListWidget()
        self.layout.addWidget(self.instance_list)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_create = QPushButton(i18n.t("btn_create_instance"))
        self.btn_create.clicked.connect(self.create_instance)
        btn_layout.addWidget(self.btn_create)
        
        self.btn_refresh = QPushButton(i18n.t("btn_refresh"))
        self.btn_refresh.clicked.connect(self.refresh_instances)
        btn_layout.addWidget(self.btn_refresh)
        
        self.layout.addLayout(btn_layout)
        
        # Status
        self.status_label = QLabel(i18n.t("status_ready"))
        self.layout.addWidget(self.status_label)
        
        # Refresh logic
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_instances)
        self.refresh_timer.start(2000)
        
        self.refresh_instances()

    def update_ui_texts(self):
        self.header_label.setText(i18n.t("header_clean_launcher"))
        self.btn_create.setText(i18n.t("btn_create_instance"))
        self.btn_refresh.setText(i18n.t("btn_refresh"))
        self.refresh_instances()
        # We don't change status label here as it might be dynamic, but initial one is reset
        if self.status_label.text() == i18n.t("status_ready", lang="en") or self.status_label.text() == i18n.t("status_ready", lang="zh"):
             self.status_label.setText(i18n.t("status_ready"))

    def _create_instance_row_widget(self, name, raw_status):
        translated_status = i18n.t("status_running") if raw_status == "Running" else i18n.t("status_stopped")
        if raw_status == "Stopped (Exited)":
            translated_status = i18n.t("status_stopped_exited")

        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(8, 4, 8, 4)

        name_label = QLabel(f"{name} ({translated_status})")
        row_layout.addWidget(name_label)
        row_layout.addStretch()

        btn_start = QPushButton(i18n.t("btn_start"))
        btn_start.clicked.connect(lambda checked=False, n=name: self.start_instance(n))
        row_layout.addWidget(btn_start)

        btn_stop = QPushButton(i18n.t("btn_stop"))
        btn_stop.clicked.connect(lambda checked=False, n=name: self.stop_instance(n))
        row_layout.addWidget(btn_stop)

        btn_delete = QPushButton(i18n.t("btn_delete"))
        btn_delete.clicked.connect(lambda checked=False, n=name: self.delete_instance(n))
        row_layout.addWidget(btn_delete)

        btn_open_webui = QPushButton(i18n.t("btn_open_webui"))
        btn_open_webui.clicked.connect(lambda checked=False, n=name: self.open_webui(n))
        row_layout.addWidget(btn_open_webui)

        btn_open_folder = QPushButton(i18n.t("btn_open_folder"))
        btn_open_folder.clicked.connect(lambda checked=False, n=name: self.open_instance_folder(n))
        row_layout.addWidget(btn_open_folder)

        btn_cli_launcher = QPushButton(i18n.t("btn_cli_launcher"))
        btn_cli_launcher.clicked.connect(lambda checked=False, n=name: self.launch_instance_cli(n))
        row_layout.addWidget(btn_cli_launcher)

        is_running = raw_status == "Running"
        btn_start.setEnabled(not is_running)
        btn_stop.setEnabled(is_running)

        return row_widget

    def refresh_instances(self):
        self.instance_list.clear()
        if Config.INSTANCES_DIR.exists():
            for item in sorted(Config.INSTANCES_DIR.iterdir(), key=lambda path: path.name.lower()):
                if item.is_dir():
                    raw_status = ProcessManager.get_status(item.name)
                    list_item = QListWidgetItem()
                    row_widget = self._create_instance_row_widget(item.name, raw_status)
                    list_item.setSizeHint(row_widget.sizeHint())
                    self.instance_list.addItem(list_item)
                    self.instance_list.setItemWidget(list_item, row_widget)

    def create_instance(self):
        missing_dependencies = self._get_missing_dependencies()
        if missing_dependencies:
            missing_text = "\n".join(f"- {dep}" for dep in missing_dependencies)
            QMessageBox.warning(
                self,
                i18n.t("title_warning"),
                i18n.t("msg_create_missing_dependencies", deps=missing_text),
            )
            return

        name, ok = QInputDialog.getText(self, i18n.t("dialog_new_instance"), i18n.t("dialog_enter_name"))
        if not (ok and name):
            return

        if (Config.INSTANCES_DIR / name).exists():
            QMessageBox.warning(self, i18n.t("title_error"), i18n.t("error_instance_exists"))
            return

        port, port_ok = QInputDialog.getInt(
            self,
            i18n.t("dialog_new_instance"),
            i18n.t("dialog_enter_port"),
            3000,
            1,
            65535,
            1,
        )
        if not port_ok:
            return

        # Use threaded implementation
        self.status_label.setText(i18n.t("msg_creating_instance", name=name))
        self.btn_create.setEnabled(False)

        self.worker = InstanceCreateWorker(name, port)
        self.worker.finished.connect(lambda: self.on_create_finished(name))
        self.worker.error.connect(lambda msg: self.on_create_error(name, msg))
        self.worker.start()

    def _get_missing_dependencies(self):
        missing = []
        runtime_manager = RuntimeManager()

        runtime_requirements = [
            (RuntimeManager.SOFTWARE_NODE, i18n.t("runtime_node")),
            (RuntimeManager.SOFTWARE_OPENCLAW, i18n.t("runtime_openclaw")),
        ]

        for software_key, display_name in runtime_requirements:
            if not runtime_manager.get_default_version(software_key):
                missing.append(display_name)

        return missing

    def on_create_finished(self, name):
         self.status_label.setText(i18n.t("msg_create_success", name=name))
         self.refresh_instances()
         self.btn_create.setEnabled(True)
         self.worker = None

    def on_create_error(self, name, error_msg):
         QMessageBox.critical(self, i18n.t("title_error"), i18n.t("msg_create_error", name=name, error=error_msg))
         self.status_label.setText(i18n.t("msg_create_failed"))
         self.btn_create.setEnabled(True)
         self.worker = None

    def start_instance(self, name):
        
        try:
            ProcessManager.start_instance(name, Config.get_instance_path(name))
            self.status_label.setText(i18n.t("msg_started", name=name))
            self.refresh_instances()
        except Exception as e:
            QMessageBox.critical(self, i18n.t("title_error"), str(e))

    def stop_instance(self, name):
        
        try:
            ProcessManager.stop_instance(name)
            self.status_label.setText(i18n.t("msg_stopped", name=name))
            self.refresh_instances()
        except Exception as e:
            QMessageBox.critical(self, i18n.t("title_error"), str(e))

    def delete_instance(self, name):
        
        res = QMessageBox.warning(self, i18n.t("title_confirm"), i18n.t("msg_confirm_delete", name=name),
                                  QMessageBox.Yes | QMessageBox.No)
        if res == QMessageBox.Yes:
            try:
                if (Config.INSTANCES_DIR / name).exists():
                     shutil.rmtree(Config.get_instance_path(name))
                self.status_label.setText(i18n.t("msg_deleted", name=name))
                self.refresh_instances()
            except Exception as e:
                 QMessageBox.critical(self, i18n.t("title_error"), str(e))

    def open_webui(self, name):
        instance_path = Config.get_instance_path(name)
        port = InstallManager.get_instance_port(instance_path)
        gateway_token = InstallManager.get_instance_gateway_token(instance_path, name)
        query = urlencode({"token": gateway_token})
        url = f"http://localhost:{port}/?{query}"
        QDesktopServices.openUrl(QUrl(url))
        self.status_label.setText(i18n.t("msg_open_webui", name=name, url=url))

    def open_instance_folder(self, name):
        instance_path = Config.get_instance_path(name)
        openclaw_folder = instance_path / ".openclaw"
        openclaw_folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(openclaw_folder)))
        self.status_label.setText(i18n.t("msg_open_folder", name=name, path=str(openclaw_folder)))

    def launch_instance_cli(self, name):
        try:
            ProcessManager.launch_instance_cli(name, Config.get_instance_path(name))
            self.status_label.setText(i18n.t("msg_cli_launched", name=name))
        except Exception as e:
            QMessageBox.critical(self, i18n.t("title_error"), i18n.t("msg_cli_launch_failed", error=str(e)))

    def shutdown(self):
        if self.refresh_timer.isActive():
            self.refresh_timer.stop()

        worker = getattr(self, "worker", None)
        if worker and worker.isRunning():
            worker.requestInterruption()
            worker.wait(2000)
            if worker.isRunning():
                worker.terminate()
                worker.wait(1000)
        self.worker = None
