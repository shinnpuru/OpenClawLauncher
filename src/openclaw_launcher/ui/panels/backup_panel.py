from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, 
                               QFileDialog, QMessageBox, QLabel)
from PySide6.QtCore import QThread, Signal
import shutil
from pathlib import Path
from datetime import datetime
from ...core.config import Config
from ..i18n import i18n


class BackupCreateWorker(QThread):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, instance_name: str, source_dir: Path, output_file: Path):
        super().__init__()
        self.instance_name = instance_name
        self.source_dir = source_dir
        self.output_file = output_file

    def run(self):
        try:
            shutil.make_archive(str(self.output_file), 'zip', str(self.source_dir))
            self.finished.emit(self.instance_name)
        except Exception as e:
            self.error.emit(str(e))


class BackupRestoreWorker(QThread):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, instance_name: str, zip_path: Path, target_dir: Path, remove_existing: bool):
        super().__init__()
        self.instance_name = instance_name
        self.zip_path = zip_path
        self.target_dir = target_dir
        self.remove_existing = remove_existing

    def run(self):
        try:
            if self.remove_existing and self.target_dir.exists():
                shutil.rmtree(self.target_dir)
            shutil.unpack_archive(str(self.zip_path), str(self.target_dir))
            self.finished.emit(self.instance_name)
        except Exception as e:
            self.error.emit(str(e))

class BackupPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.backup_worker = None
        self.restore_worker = None
        self.current_action = None
        self.current_instance_name = None
        self.layout = QVBoxLayout(self)

        # Top Bar
        top_layout = QVBoxLayout() # Using QV for now, or QH?
        # The user asked for "Refresh" button. 
        # Maybe align right?
        refresh_layout = QHBoxLayout()
        refresh_layout.addStretch()
        self.btn_refresh = QPushButton(i18n.t("btn_refresh"))
        self.btn_refresh.clicked.connect(self.refresh_lists)
        refresh_layout.addWidget(self.btn_refresh)
        self.layout.addLayout(refresh_layout)
        
        # Instance List for backup
        self.lbl_select_instance = QLabel(i18n.t("lbl_select_instance_backup"))
        self.layout.addWidget(self.lbl_select_instance)
        self.instance_list_widget = QListWidget()
        self.layout.addWidget(self.instance_list_widget)
        
        self.btn_backup = QPushButton(i18n.t("btn_create_backup"))
        self.btn_backup.clicked.connect(self.create_backup)
        self.layout.addWidget(self.btn_backup)
        
        # Backups List
        self.lbl_backups = QLabel(i18n.t("lbl_existing_backups"))
        self.layout.addWidget(self.lbl_backups)
        self.backup_list_widget = QListWidget()
        self.layout.addWidget(self.backup_list_widget)
        
        self.btn_restore = QPushButton(i18n.t("btn_restore_backup"))
        self.btn_restore.clicked.connect(self.restore_backup)
        self.layout.addWidget(self.btn_restore)

        self.lbl_status = QLabel()
        self.layout.addWidget(self.lbl_status)
        self._set_status(None, None)
        
        self.refresh_lists()

    def update_ui_texts(self):
        self.btn_refresh.setText(i18n.t("btn_refresh"))
        self.lbl_select_instance.setText(i18n.t("lbl_select_instance_backup"))
        self.btn_backup.setText(i18n.t("btn_create_backup"))
        self.lbl_backups.setText(i18n.t("lbl_existing_backups"))
        self.btn_restore.setText(i18n.t("btn_restore_backup"))
        self._set_status(self.current_action, self.current_instance_name)

    def refresh_lists(self):
        self.instance_list_widget.clear()
        if Config.INSTANCES_DIR.exists():
            for d in Config.INSTANCES_DIR.iterdir():
                if d.is_dir():
                    self.instance_list_widget.addItem(d.name)
        
        self.backup_list_widget.clear()
        backup_dir = Config.BASE_DIR / "backups"
        if backup_dir.exists():
            for f in backup_dir.glob("*.zip"):
                self.backup_list_widget.addItem(f.name)

    def _set_busy_state(self, busy: bool):
        self.btn_backup.setEnabled(not busy)
        self.btn_restore.setEnabled(not busy)
        self.btn_refresh.setEnabled(not busy)

    def _set_status(self, action, instance_name):
        self.current_action = action
        self.current_instance_name = instance_name

        if action == "backup" and instance_name:
            self.lbl_status.setText(i18n.t("status_backup_running", name=instance_name))
        elif action == "restore" and instance_name:
            self.lbl_status.setText(i18n.t("status_restore_running", name=instance_name))
        else:
            self.lbl_status.setText(i18n.t("status_backup_idle"))

    def create_backup(self):
        if self.backup_worker is not None or self.restore_worker is not None:
            return

        item = self.instance_list_widget.currentItem()
        if not item: return
        
        instance_name = item.text()
        src = Config.get_instance_path(instance_name)
        
        backup_dir = Config.BASE_DIR / "backups"
        if not backup_dir.exists():
            backup_dir.mkdir(parents=True)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{instance_name}_{timestamp}"
        output_file = backup_dir / backup_name
        
        self._set_busy_state(True)
        self._set_status("backup", instance_name)

        self.backup_worker = BackupCreateWorker(instance_name, src, output_file)
        self.backup_worker.finished.connect(self.on_backup_finished)
        self.backup_worker.error.connect(self.on_backup_error)
        self.backup_worker.start()

    def on_backup_finished(self, instance_name):
        QMessageBox.information(self, i18n.t("title_success"), i18n.t("msg_backup_success", name=instance_name))
        self.refresh_lists()
        self._set_busy_state(False)
        self._set_status(None, None)
        self.backup_worker = None

    def on_backup_error(self, error_msg):
        QMessageBox.critical(self, i18n.t("title_error"), error_msg)
        self._set_busy_state(False)
        self._set_status(None, None)
        self.backup_worker = None

    def restore_backup(self):
        if self.backup_worker is not None or self.restore_worker is not None:
            return

        item = self.backup_list_widget.currentItem()
        if not item: return
        
        zip_path = Config.BASE_DIR / "backups" / item.text()
        backup_stem = Path(item.text()).stem
        parts = backup_stem.rsplit("_", 2)
        instance_name = parts[0] if len(parts) >= 3 else backup_stem
        
        target_dir = Config.get_instance_path(instance_name)
        remove_existing = False
        
        if target_dir.exists():
            res = QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("msg_restore_warning", name=instance_name),
                                      QMessageBox.Yes | QMessageBox.No)
            if res == QMessageBox.No:
                return
            remove_existing = True

        self._set_busy_state(True)
        self._set_status("restore", instance_name)
        self.restore_worker = BackupRestoreWorker(instance_name, zip_path, target_dir, remove_existing)
        self.restore_worker.finished.connect(self.on_restore_finished)
        self.restore_worker.error.connect(self.on_restore_error)
        self.restore_worker.start()

    def on_restore_finished(self, instance_name):
        QMessageBox.information(self, i18n.t("title_success"), i18n.t("msg_restore_success", name=instance_name))
        self.refresh_lists()
        self._set_busy_state(False)
        self._set_status(None, None)
        self.restore_worker = None

    def on_restore_error(self, error_msg):
        QMessageBox.critical(self, i18n.t("title_error"), error_msg)
        self._set_busy_state(False)
        self._set_status(None, None)
        self.restore_worker = None

    def shutdown(self):
        for worker_attr in ("backup_worker", "restore_worker"):
            worker = getattr(self, worker_attr, None)
            if worker and worker.isRunning():
                worker.requestInterruption()
                worker.wait(2000)
                if worker.isRunning():
                    worker.terminate()
                    worker.wait(1000)
            setattr(self, worker_attr, None)
