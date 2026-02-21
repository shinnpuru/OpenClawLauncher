from PySide6.QtWidgets import (QMainWindow, QTabWidget, QWidget, QVBoxLayout,
                               QSystemTrayIcon, QMenu, QPushButton, QHBoxLayout, QLabel,
                               QStyle, QApplication, QMessageBox)
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QEvent, QTimer, QThread, Signal
from .panels.instance_panel import InstancePanel
from .panels.dependency_panel import DependencyPanel
from .panels.backup_panel import BackupPanel
from .panels.log_panel import LogPanel
from .panels.advanced_panel import AdvancedPanel
from ..core.config import Config
from ..core.process_manager import ProcessManager
from ..core.runtime_manager import RuntimeManager
from .i18n import i18n
from .theme_manager import theme_manager


class OpenClawUpdateCheckWorker(QThread):
    result_ready = Signal(str, str)

    def _parse_version(self, version: str):
        if not version:
            return (0,)

        normalized = str(version).strip().lstrip("v")
        parts = []
        token = ""
        for ch in normalized:
            if ch.isdigit():
                token += ch
            else:
                if token:
                    parts.append(int(token))
                    token = ""
        if token:
            parts.append(int(token))

        return tuple(parts) if parts else (0,)

    def run(self):
        current_version = ""
        latest_version = ""
        try:
            manager = RuntimeManager()
            current_version = manager.get_default_version(RuntimeManager.SOFTWARE_OPENCLAW) or ""
            manager.refresh_available_versions(RuntimeManager.SOFTWARE_OPENCLAW)
            available = manager.get_available_versions(RuntimeManager.SOFTWARE_OPENCLAW)
            if available:
                latest_version = str(available[0].get("version", "")).strip()

            if current_version and latest_version and self._parse_version(latest_version) > self._parse_version(current_version):
                self.result_ready.emit(current_version, latest_version)
                return
        except Exception:
            pass

        self.result_ready.emit("", "")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._force_quit = False
        self._is_shutting_down = False
        self._update_check_worker = None
        self.setWindowTitle("OpenClaw Launcher")
        self.resize(1000, 700)
        
        # Ensure Dirs
        Config.ensure_dirs()
        
        # Main Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # Header with Language + Theme Switch
        header_layout = QHBoxLayout()
        self.title_label = QLabel(i18n.t("app_title"))
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()

        self.theme_btn = QPushButton()
        self.theme_btn.clicked.connect(self.toggle_theme_mode)
        header_layout.addWidget(self.theme_btn)
        
        self.lang_btn = QPushButton(i18n.t("lang_switch"))
        self.lang_btn.clicked.connect(self.toggle_language)
        header_layout.addWidget(self.lang_btn)
        
        self.layout.addLayout(header_layout)
        
        # Tabs
        self.tabs = QTabWidget()
        
        # Panels
        self.instance_panel = InstancePanel()
        self.dependency_panel = DependencyPanel()
        self.backup_panel = BackupPanel()
        self.log_panel = LogPanel()
        self.advanced_panel = AdvancedPanel()
        
        # Add Tabs
        self.tabs.addTab(self.instance_panel, i18n.t("tab_instances"))
        self.tabs.addTab(self.dependency_panel, i18n.t("tab_dependencies"))
        self.tabs.addTab(self.backup_panel, i18n.t("tab_backups"))
        self.tabs.addTab(self.log_panel, i18n.t("tab_logs"))
        self.tabs.addTab(self.advanced_panel, i18n.t("tab_advanced"))
        
        self.layout.addWidget(self.tabs)
        
        # System Tray logic if needed (optional)
        self.setup_tray()
        
        # Connect language change signal
        i18n.language_changed.connect(self.on_language_changed)
        theme_manager.theme_mode_changed.connect(self.on_theme_mode_changed)

        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.shutdown)
        
        self.update_ui_texts()
        QTimer.singleShot(0, self._check_openclaw_updates_on_startup)

    def _check_openclaw_updates_on_startup(self):
        if not Config.get_setting("check_updates", True):
            return

        if self._update_check_worker and self._update_check_worker.isRunning():
            return

        worker = OpenClawUpdateCheckWorker()
        worker.result_ready.connect(self._on_openclaw_update_check_result)
        worker.finished.connect(worker.deleteLater)
        self._update_check_worker = worker
        worker.start()

    def _on_openclaw_update_check_result(self, current_version: str, latest_version: str):
        worker = self._update_check_worker
        if worker and worker.isFinished():
            self._update_check_worker = None

        if not current_version or not latest_version:
            return

        QMessageBox.information(
            self,
            i18n.t("title_update_available"),
            i18n.t("msg_openclaw_update_available", current=current_version, latest=latest_version),
        )

    def toggle_language(self):
        new_lang = "zh" if i18n.current_lang == "en" else "zh"
        i18n.set_language(new_lang)

    def on_language_changed(self, lang):
        self.update_ui_texts()
        # Propagate to panels if they have update_ui_texts method
        for panel in [self.instance_panel, self.dependency_panel, self.backup_panel, self.log_panel, self.advanced_panel]:
            if hasattr(panel, 'update_ui_texts'):
                panel.update_ui_texts()

    def on_theme_mode_changed(self, mode):
        self.update_theme_button_text()

    def toggle_theme_mode(self):
        order = ["light", "dark", "system"]
        current = theme_manager.current_mode
        try:
            idx = order.index(current)
        except ValueError:
            idx = 2
        next_mode = order[(idx + 1) % len(order)]
        theme_manager.set_mode(next_mode)

    def update_theme_button_text(self):
        mode = theme_manager.current_mode
        mode_map = {
            "light": i18n.t("opt_theme_light"),
            "dark": i18n.t("opt_theme_dark"),
            "system": i18n.t("opt_theme_system"),
        }
        mode_text = mode_map.get(mode, i18n.t("opt_theme_system"))
        self.theme_btn.setText(i18n.t("btn_theme_mode", mode=mode_text))

    def update_ui_texts(self):
        self.setWindowTitle(i18n.t("app_title"))
        self.title_label.setText(i18n.t("app_title"))
        self.update_theme_button_text()

        self.lang_btn.setText(i18n.t("lang_switch"))
        self.tabs.setTabText(0, i18n.t("tab_instances"))
        self.tabs.setTabText(1, i18n.t("tab_dependencies"))
        self.tabs.setTabText(2, i18n.t("tab_backups"))
        self.tabs.setTabText(3, i18n.t("tab_logs"))
        self.tabs.setTabText(4, i18n.t("tab_advanced"))
        if hasattr(self, "tray_icon") and self.tray_icon:
            self.tray_icon.setToolTip(i18n.t("app_title"))
        if hasattr(self, "action_show") and self.action_show:
            self.action_show.setText(i18n.t("tray_show_window"))
        if hasattr(self, "action_quit") and self.action_quit:
            self.action_quit.setText(i18n.t("tray_quit"))
    
    def setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = None
            return

        self.tray_icon = QSystemTrayIcon(self)
        tray_icon = self.windowIcon()
        if tray_icon.isNull():
            tray_icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
            self.setWindowIcon(tray_icon)
        self.tray_icon.setIcon(tray_icon)
        self.tray_icon.setToolTip(i18n.t("app_title"))

        self.tray_menu = QMenu(self)
        self.action_show = QAction(i18n.t("tray_show_window"), self)
        self.action_quit = QAction(i18n.t("tray_quit"), self)
        self.action_show.triggered.connect(self.show_from_tray)
        self.action_quit.triggered.connect(self.quit_from_tray)
        self.tray_menu.addAction(self.action_show)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(self.action_quit)
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_from_tray()

    def show_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def quit_from_tray(self):
        self._force_quit = True
        QApplication.instance().quit()

    def shutdown(self):
        if self._is_shutting_down:
            return
        self._is_shutting_down = True

        worker = self._update_check_worker
        if worker and worker.isRunning():
            worker.requestInterruption()
            worker.wait(1000)
        self._update_check_worker = None

        for panel in [self.instance_panel, self.dependency_panel, self.backup_panel, self.log_panel, self.advanced_panel]:
            shutdown = getattr(panel, "shutdown", None)
            if callable(shutdown):
                try:
                    shutdown()
                except Exception:
                    pass

        keep_alive = Config.get_setting("keep_alive", False)
        if not keep_alive:
            ProcessManager.stop_all_instances()

        if getattr(self, "tray_icon", None):
            self.tray_icon.hide()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange:
            if self.isMinimized() and Config.get_setting("minimize_to_tray", False):
                if getattr(self, "tray_icon", None) and self.tray_icon.isVisible():
                    QTimer.singleShot(0, self.hide)

    def closeEvent(self, event):
        if self._force_quit:
            self.shutdown()
            event.accept()
            return

        if Config.get_setting("minimize_to_tray", False):
            if getattr(self, "tray_icon", None) and self.tray_icon.isVisible():
                self.hide()
                event.ignore()
                return

        self.shutdown()
        super().closeEvent(event)
