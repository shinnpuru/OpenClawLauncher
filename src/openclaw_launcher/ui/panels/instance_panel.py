from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QListWidget, QListWidgetItem, QLabel, QInputDialog, QMessageBox, QProgressBar)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, Slot, QUrl
from PySide6.QtGui import QDesktopServices
from urllib.parse import urlencode
from ...core.config import Config
from ...core.process_manager import ProcessManager
from ...core.install_manager import InstallManager
from ...core.runtime_manager import RuntimeManager
from ..i18n import i18n
from .backup_panel import BackupCreateWorker
import shutil
import os
import stat
import time
from pathlib import Path
from datetime import datetime

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

class InstanceUpdateWorker(QThread):
    finished = Signal(str)
    error = Signal(str)
    progress = Signal(str, int, int, str)

    def __init__(self, name):
        super().__init__()
        self.name = name

    def run(self):
        try:
            def _progress_callback(stage, current, total, detail):
                self.progress.emit(stage, current, total, detail)

            new_name = InstallManager.update_instance_to_default_version(
                self.name,
                progress_callback=_progress_callback,
            )
            self.finished.emit(new_name)
        except Exception as e:
            self.error.emit(str(e))


class InstanceDeleteWorker(QThread):
    finished = Signal(str, bool, str)
    error = Signal(str, str, str)

    def __init__(self, name):
        super().__init__()
        self.name = name

    def run(self):
        instance_path = Config.get_instance_path(self.name)
        try:
            if ProcessManager.get_status(self.name) == "Running":
                ProcessManager.stop_instance(self.name)

            if instance_path.exists():
                self._remove_dir_with_retries(instance_path)

            self.finished.emit(self.name, instance_path.exists(), str(instance_path))
        except Exception as e:
            self.error.emit(self.name, str(e), str(instance_path))

    def _remove_dir_with_retries(self, target_dir, retries=5, delay=0.2):
        def _onerror(func, path, exc_info):
            try:
                os.chmod(path, stat.S_IWRITE)
                func(path)
            except Exception:
                pass

        last_error = None
        for attempt in range(retries):
            try:
                if target_dir.exists():
                    shutil.rmtree(target_dir, onerror=_onerror)
                return
            except Exception as e:
                last_error = e
                if attempt < retries - 1:
                    time.sleep(delay)

        if last_error:
            raise last_error

class InstancePanel(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.worker = None
        self.backup_worker = None
        self._update_instance_name = None
        
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

        self.update_progress = QProgressBar()
        self.update_progress.setVisible(False)
        self.update_progress.setTextVisible(True)
        self.layout.addWidget(self.update_progress)

        self.delete_progress = QProgressBar()
        self.delete_progress.setVisible(False)
        self.delete_progress.setTextVisible(True)
        self.layout.addWidget(self.delete_progress)
        
        self.backup_progress = QProgressBar()
        self.backup_progress.setVisible(False)
        self.backup_progress.setTextVisible(True)
        self.backup_progress.setFormat(i18n.t("progress_backup_creating"))
        self.layout.addWidget(self.backup_progress)
        
        # Refresh logic
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_instances)
        self.refresh_timer.start(2000)
        
        self.refresh_instances()

    def update_ui_texts(self):
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

        btn_update = QPushButton(i18n.t("btn_update_version"))
        btn_update.clicked.connect(lambda checked=False, n=name: self.update_instance(n))
        row_layout.addWidget(btn_update)

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
        btn_update.setEnabled(not is_running)

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
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("msg_instance_task_busy"))
            return

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
            18789,
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

    def update_instance(self, name):
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("msg_instance_task_busy"))
            return

        if ProcessManager.get_status(name) == "Running":
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("msg_update_requires_stop", name=name))
            return

        res = QMessageBox.warning(
            self,
            i18n.t("title_confirm_update"),
            i18n.t("msg_confirm_update_version", name=name),
            QMessageBox.Yes | QMessageBox.No,
        )
        if res != QMessageBox.Yes:
            return

        # Ask if user wants to backup before updating
        backup_res = QMessageBox.question(
            self,
            i18n.t("title_backup_instance"),
            i18n.t("msg_backup_before_update", name=name),
            QMessageBox.Yes | QMessageBox.No,
        )
        
        # Store the instance name for backup error handling
        self._update_instance_name = name
        
        if backup_res == QMessageBox.Yes:
            self.status_label.setText(i18n.t("msg_backing_up_instance", name=name))
            self._create_backup_for_update(name)
        else:
            self._start_update(name)

    def on_update_progress(self, stage, current, total, detail):
        if stage == "overwriting":
            self.update_progress.setRange(0, 0)
            self.update_progress.setFormat(i18n.t("progress_update_preparing"))
            return

        if stage == "reinstalling":
            self.update_progress.setRange(0, 0)
            self.update_progress.setFormat(i18n.t("progress_update_migrating"))
            return

        if stage == "done":
            self.update_progress.setRange(0, 1)
            self.update_progress.setValue(1)
            self.update_progress.setFormat(i18n.t("progress_update_done"))

    def _create_backup_for_update(self, name):
        """Create backup before updating, then proceed with update."""
        instance_path = Config.get_instance_path(name)
        
        backup_dir = Config.BASE_DIR / "backups"
        if not backup_dir.exists():
            backup_dir.mkdir(parents=True, exist_ok=True)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{name}_{timestamp}"
        output_file = backup_dir / backup_name
        
        self.backup_worker = BackupCreateWorker(name, instance_path, output_file)
        self.backup_worker.progress_percentage.connect(self._on_backup_progress)
        self.backup_worker.finished.connect(lambda instance_name: self._on_backup_finished_for_update(instance_name))
        self.backup_worker.error.connect(lambda error_msg: self._on_backup_error_for_update(error_msg))
        self.backup_progress.setVisible(True)
        self.backup_progress.setValue(0)
        self.backup_worker.start()

    def _on_backup_progress(self, percentage: int):
        """Update backup progress bar."""
        self.backup_progress.setValue(percentage)

    def _on_backup_finished_for_update(self, instance_name):
        """After backup completes, start the update."""
        self.backup_progress.setVisible(False)
        QMessageBox.information(
            self,
            i18n.t("title_success"),
            i18n.t("msg_backup_success", name=instance_name, path=str(Config.BASE_DIR / "backups")),
        )
        self.backup_worker = None
        self._start_update(instance_name)

    def _on_backup_error_for_update(self, error_msg):
        """Backup failed, don't proceed with update."""
        self.backup_progress.setVisible(False)
        instance_name = getattr(self, '_update_instance_name', 'Unknown')
        QMessageBox.critical(
            self,
            i18n.t("title_error"),
            i18n.t("msg_backup_error", name=instance_name, error=error_msg),
        )
        self.backup_worker = None
        self.status_label.setText(i18n.t("status_ready"))

    def _start_update(self, name):
        """Start the actual instance update."""
        self.status_label.setText(i18n.t("msg_updating_instance", name=name))
        self.btn_create.setEnabled(False)
        self.update_progress.setVisible(True)
        self.update_progress.setRange(0, 0)
        self.update_progress.setFormat(i18n.t("progress_update_preparing"))

        self.worker = InstanceUpdateWorker(name)
        self.worker.finished.connect(lambda new_name: self.on_update_finished(name, new_name))
        self.worker.error.connect(lambda msg: self.on_update_error(name, msg))
        self.worker.progress.connect(self.on_update_progress)
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

    def on_update_finished(self, name, updated_name):
        self.status_label.setText(i18n.t("msg_update_success", name=name, new_name=updated_name))
        self.update_progress.setVisible(False)
        self.refresh_instances()
        self.btn_create.setEnabled(True)
        self.worker = None

    def on_update_error(self, name, error_msg):
        QMessageBox.critical(self, i18n.t("title_error"), i18n.t("msg_update_error", name=name, error=error_msg))
        self.status_label.setText(i18n.t("msg_update_failed", name=name))
        self.update_progress.setVisible(False)
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
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("msg_instance_task_busy"))
            return

        res = QMessageBox.warning(self, i18n.t("title_confirm"), i18n.t("msg_confirm_delete", name=name),
                                  QMessageBox.Yes | QMessageBox.No)
        if res != QMessageBox.Yes:
            return

        self.status_label.setText(i18n.t("msg_deleting_instance", name=name))
        self.btn_create.setEnabled(False)
        self.delete_progress.setVisible(True)
        self.delete_progress.setRange(0, 0)
        self.delete_progress.setFormat(i18n.t("progress_delete_running"))

        self.worker = InstanceDeleteWorker(name)
        self.worker.finished.connect(self.on_delete_finished)
        self.worker.error.connect(self.on_delete_error)
        self.worker.start()

    def on_delete_finished(self, name, residual_exists, instance_path_str):
        self.delete_progress.setVisible(False)
        self.btn_create.setEnabled(True)

        instance_path = Path(instance_path_str)
        if residual_exists:
            self._show_manual_cleanup_dialog(
                name,
                instance_path,
                i18n.t("msg_delete_manual_cleanup_detected", name=name, path=str(instance_path)),
            )
            self.status_label.setText(i18n.t("title_warning"))
        else:
            self.status_label.setText(i18n.t("msg_deleted", name=name))

        self.refresh_instances()
        self.worker = None

    def on_delete_error(self, name, error_msg, instance_path_str):
        self.delete_progress.setVisible(False)
        self.btn_create.setEnabled(True)

        instance_path = Path(instance_path_str)
        if instance_path.exists():
            self._show_manual_cleanup_dialog(
                name,
                instance_path,
                i18n.t("msg_delete_manual_cleanup_hint", name=name, path=str(instance_path), error=error_msg),
            )
        else:
            QMessageBox.warning(self, i18n.t("title_warning"), error_msg)

        self.status_label.setText(i18n.t("title_warning"))
        self.refresh_instances()
        self.worker = None

    def _show_manual_cleanup_dialog(self, name, path, message):
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Warning)
        dialog.setWindowTitle(i18n.t("title_warning"))
        dialog.setText(message)
        btn_open = dialog.addButton(i18n.t("btn_open_folder"), QMessageBox.ActionRole)
        dialog.addButton(QMessageBox.Close)
        dialog.exec()

        if dialog.clickedButton() == btn_open and path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

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
