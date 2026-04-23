from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit,
                               QPushButton, QHBoxLayout, QComboBox)
from PySide6.QtCore import QTimer, QFileSystemWatcher
from ...core.config import Config
from ..i18n import i18n
import subprocess
import os

class LogPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.log_watcher = QFileSystemWatcher(self)
        self.log_watcher.fileChanged.connect(self.on_log_file_changed)
        self.watched_log_file = None
        
        self.log_combo = QComboBox()
        self.log_combo.currentIndexChanged.connect(self.on_log_changed)
        self.layout.addWidget(self.log_combo)
        
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.layout.addWidget(self.log_display)
        
        btn_layout = QHBoxLayout()
        self.btn_open = QPushButton(i18n.t("btn_open_logs"))
        self.btn_open.clicked.connect(self.open_log_file)
        btn_layout.addWidget(self.btn_open)
        
        self.btn_clear = QPushButton(i18n.t("btn_clear_logs"))
        self.btn_clear.clicked.connect(self.clear_logs)
        btn_layout.addWidget(self.btn_clear)
        
        self.layout.addLayout(btn_layout)
        
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_logs)
        self.refresh_timer.start(5000)
        
        self.refresh_logs()

    def on_log_changed(self, *_):
        self._update_log_watch_target()
        self.load_log()

    def _selected_log_path(self):
        data = self.log_combo.currentData()
        if not data:
            return None
        return Config.LOGS_DIR / data

    def _scan_log_files(self):
        if not Config.LOGS_DIR.exists():
            return []
        files = [p for p in Config.LOGS_DIR.rglob("*.log") if p.is_file()]
        files.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
        return files

    def _update_log_watch_target(self):
        if self.watched_log_file and self.watched_log_file in self.log_watcher.files():
            self.log_watcher.removePath(self.watched_log_file)

        self.watched_log_file = None
        log_path = self._selected_log_path()
        if not log_path:
            return

        if log_path.exists():
            self.watched_log_file = str(log_path)
            self.log_watcher.addPath(self.watched_log_file)

    def on_log_file_changed(self, _path):
        self.load_log()
        self._update_log_watch_target()

    def update_ui_texts(self):
        self.btn_open.setText(i18n.t("btn_open_logs"))
        self.btn_clear.setText(i18n.t("btn_clear_logs"))

    def refresh_logs(self):
        current = self.log_combo.currentData()
        self.log_combo.clear()

        for path in self._scan_log_files():
            relative = str(path.relative_to(Config.LOGS_DIR)).replace("\\", "/")
            self.log_combo.addItem(relative, relative)

        idx = self.log_combo.findData(current)
        if idx >= 0:
            self.log_combo.setCurrentIndex(idx)
        else:
            self._update_log_watch_target()
            self.load_log()

    def load_log(self):
        log_path = self._selected_log_path()
        if not log_path:
            self.log_display.clear()
            return

        if log_path.exists():
            try:
                with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                    # Only show the last 100 lines
                    last_100_lines = lines[-100:] if len(lines) > 100 else lines
                    content = ''.join(last_100_lines)
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
        log_path = self._selected_log_path()
        if not log_path:
            return
        if log_path.exists():
            with open(log_path, 'w') as f:
                f.write("")
        self.load_log()

    def open_log_file(self):
        """Open the log file with the system's default application"""
        log_path = self._selected_log_path()
        if not log_path:
            return

        if log_path.exists():
            if os.name == 'nt':  # Windows
                os.startfile(str(log_path))
            else:  # Linux/Mac
                subprocess.run(['open' if os.uname().sysname == 'Darwin' else 'xdg-open', str(log_path)])
        else:
            self.log_display.setPlainText(i18n.t("msg_no_logs_found"))

    def shutdown(self):
        if self.refresh_timer.isActive():
            self.refresh_timer.stop()

        if self.watched_log_file and self.watched_log_file in self.log_watcher.files():
            self.log_watcher.removePath(self.watched_log_file)
        self.watched_log_file = None
