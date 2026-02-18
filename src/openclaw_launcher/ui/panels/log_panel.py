from PySide6.QtWidgets import (QWidget, QVBoxLayout, QListWidget, QTextEdit, 
                               QPushButton, QHBoxLayout, QComboBox)
from PySide6.QtCore import QTimer, QFileSystemWatcher
from ...core.config import Config
from ...core.process_manager import ProcessManager
from ..i18n import i18n

class LogPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.log_watcher = QFileSystemWatcher(self)
        self.log_watcher.fileChanged.connect(self.on_log_file_changed)
        self.watched_log_file = None
        
        self.instance_combo = QComboBox()
        self.instance_combo.currentIndexChanged.connect(self.on_instance_changed)
        self.layout.addWidget(self.instance_combo)
        
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.layout.addWidget(self.log_display)
        
        btn_layout = QHBoxLayout()
        self.btn_refresh = QPushButton(i18n.t("btn_refresh_logs"))
        self.btn_refresh.clicked.connect(self.load_log)
        btn_layout.addWidget(self.btn_refresh)
        
        self.btn_clear = QPushButton(i18n.t("btn_clear_logs"))
        self.btn_clear.clicked.connect(self.clear_logs)
        btn_layout.addWidget(self.btn_clear)
        
        self.layout.addLayout(btn_layout)
        
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_instances)
        self.refresh_timer.start(5000)
        
        self.refresh_instances()

    def on_instance_changed(self, *_):
        self._update_log_watch_target()
        self.load_log()

    def _update_log_watch_target(self):
        if self.watched_log_file and self.watched_log_file in self.log_watcher.files():
            self.log_watcher.removePath(self.watched_log_file)

        self.watched_log_file = None
        instance_name = self.instance_combo.currentText()
        if not instance_name:
            return

        log_path = Config.get_log_file(instance_name)
        if log_path.exists():
            self.watched_log_file = str(log_path)
            self.log_watcher.addPath(self.watched_log_file)

    def on_log_file_changed(self, _path):
        self.load_log()
        self._update_log_watch_target()

    def update_ui_texts(self):
        self.btn_refresh.setText(i18n.t("btn_refresh_logs"))
        self.btn_clear.setText(i18n.t("btn_clear_logs"))

    def refresh_instances(self):
        current = self.instance_combo.currentText()
        self.instance_combo.clear()
        if Config.INSTANCES_DIR.exists():
            for d in Config.INSTANCES_DIR.iterdir():
                if d.is_dir():
                    self.instance_combo.addItem(d.name)
        
        idx = self.instance_combo.findText(current)
        if idx >= 0:
            self.instance_combo.setCurrentIndex(idx)
        else:
            self._update_log_watch_target()

    def load_log(self):
        instance_name = self.instance_combo.currentText()
        if not instance_name:
            self.log_display.clear()
            return
            
        log_path = Config.get_log_file(instance_name)
        if log_path.exists():
            try:
                with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                    self.log_display.setPlainText(content)
                    self.log_display.verticalScrollBar().setValue(
                        self.log_display.verticalScrollBar().maximum()
                    )
            except Exception as e:
                self.log_display.setPlainText(i18n.t("msg_log_read_error", error=str(e)))
        else:
            self.log_display.setPlainText(i18n.t("msg_no_logs_found"))
            self._update_log_watch_target()

    def clear_logs(self):
        instance_name = self.instance_combo.currentText()
        if not instance_name: return
        log_path = Config.get_log_file(instance_name)
        if log_path.exists():
            with open(log_path, 'w') as f:
                f.write("")
        self.load_log()

    def shutdown(self):
        if self.refresh_timer.isActive():
            self.refresh_timer.stop()

        if self.watched_log_file and self.watched_log_file in self.log_watcher.files():
            self.log_watcher.removePath(self.watched_log_file)
        self.watched_log_file = None
