from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                               QSystemTrayIcon, QMenu, QPushButton, QHBoxLayout, QLabel,
                               QStyle, QApplication, QMessageBox, QStackedWidget, QSplitter)
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QEvent, QTimer, QThread, Signal, Qt, QPropertyAnimation, QEasingCurve, QSize
from .panels.onboard_panel import OnboardPanel
from .panels.instance_panel import InstancePanel
from .panels.dependency_panel import DependencyPanel
from .panels.backup_panel import BackupPanel
from .panels.log_panel import LogPanel
from .panels.advanced_panel import AdvancedPanel
from .panels.plugin_panel import PluginPanel
from .panels.env_var_panel import EnvVarPanel
from .panels.channel_config_panel import ChannelConfigPanel
from .panels.ai_model_panel import LlamaCppTab, ModelSwitchTab
from ..core.config import Config
from ..core.process_manager import ProcessManager
from ..core.runtime_manager import RuntimeManager
from .i18n import i18n
from .theme_manager import theme_manager
from .sidebar_nav import SidebarNav


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
            available = manager.get_available_versions(RuntimeManager.SOFTWARE_OPENCLAW)
            if not available:
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
        self.resize(1200, 700)
        self._sidebar_width = 200
        self._sidebar_collapsed = False
        
        # Ensure Dirs
        Config.ensure_dirs()
        
        # Main Layout
        self.central_widget = QWidget()
        self.central_widget.setObjectName("MainRoot")
        self.setCentralWidget(self.central_widget)
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header with Language + Theme Switch
        self.top_bar = QWidget()
        self.top_bar.setObjectName("TopBar")
        header_layout = QHBoxLayout(self.top_bar)
        header_layout.setContentsMargins(10, 5, 10, 5)
        
        # Sidebar toggle button
        self.sidebar_toggle_btn = QPushButton("☰")
        self.sidebar_toggle_btn.setObjectName("SidebarToggleButton")
        self.sidebar_toggle_btn.setFixedSize(34, 34)
        self.sidebar_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.sidebar_toggle_btn.clicked.connect(self.toggle_sidebar)
        header_layout.addWidget(self.sidebar_toggle_btn)
        
        header_layout.addSpacing(10)
        
        self.title_label = QLabel(i18n.t("app_title"))
        self.title_label.setObjectName("AppTitleLabel")
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()

        self.theme_btn = QPushButton()
        self.theme_btn.setObjectName("ToolButton")
        self.theme_btn.clicked.connect(self.toggle_theme_mode)
        header_layout.addWidget(self.theme_btn)
        
        self.lang_btn = QPushButton(i18n.t("lang_switch"))
        self.lang_btn.setObjectName("ToolButton")
        self.lang_btn.clicked.connect(self.toggle_language)
        header_layout.addWidget(self.lang_btn)
        
        main_layout.addWidget(self.top_bar)
        
        # Content area with sidebar and stacked widget
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Sidebar
        self.sidebar = SidebarNav()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setMinimumWidth(self._sidebar_width)
        self.sidebar.setMaximumWidth(self._sidebar_width)
        self.sidebar.panel_selected.connect(self.switch_to_panel)
        self.sidebar.toggle_sidebar.connect(self.toggle_sidebar)
        content_layout.addWidget(self.sidebar)
        
        # Stacked widget for panels
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setObjectName("PanelsContainer")
        content_layout.addWidget(self.stacked_widget)
        
        main_layout.addWidget(content_widget)
        
        # Panels
        self.onboard_panel = OnboardPanel()
        self.instance_panel = InstancePanel()
        self.dependency_panel = DependencyPanel()
        self.backup_panel = BackupPanel()
        self.log_panel = LogPanel()
        self.plugin_panel = PluginPanel()
        self.env_var_panel = EnvVarPanel()
        self.channel_config_panel = ChannelConfigPanel()
        self.advanced_panel = AdvancedPanel()
        self.llamacpp_panel = LlamaCppTab(self)
        self.model_switch_panel = ModelSwitchTab(self)

        self.onboard_panel.dependencies_ready.connect(self.dependency_panel.refresh_all_cards)
        self.onboard_panel.sample_ready.connect(self.instance_panel.refresh_instances)
        self.onboard_panel.navigate_to_tab.connect(self.switch_to_tab)

        # Add panels to stacked widget
        self.panel_map = {
            "onboard": self.onboard_panel,
            "instances": self.instance_panel,
            "dependencies": self.dependency_panel,
            "backups": self.backup_panel,
            "logs": self.log_panel,
            "plugins": self.plugin_panel,
            "env_vars": self.env_var_panel,
            "channels": self.channel_config_panel,
            "llamacpp": self.llamacpp_panel,
            "model_switch": self.model_switch_panel,
            "advanced": self.advanced_panel,
        }
        
        for panel in self.panel_map.values():
            self.stacked_widget.addWidget(panel)
        
        # Setup sidebar sections
        self._setup_sidebar_sections()
        
        # System Tray logic if needed (optional)
        self.setup_tray()
        
        # Connect language change signal
        i18n.language_changed.connect(self.on_language_changed)
        theme_manager.theme_mode_changed.connect(self.on_theme_mode_changed)

        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.shutdown)
        
        self.update_ui_texts()
        # Set initial panel
        self.switch_to_panel("onboard")
        QTimer.singleShot(0, self._check_openclaw_updates_on_startup)
        QTimer.singleShot(300, self._launch_sample_on_startup)

    def _setup_sidebar_sections(self):
        """Setup sidebar sections based on i18n"""
        section_configs = {
            i18n.t("sidebar_section_main"): [
                (i18n.t("tab_onboard"), "onboard"),
                (i18n.t("tab_channels"), "channels"),
                (i18n.t("tab_llamacpp"), "llamacpp"),
                (i18n.t("tab_model_switch"), "model_switch"),
            ],
            i18n.t("sidebar_section_data"): [
                (i18n.t("tab_instances"), "instances"),
                (i18n.t("tab_instance_env"), "env_vars"),
                (i18n.t("tab_dependencies"), "dependencies"),
                (i18n.t("tab_backups"), "backups"),
            ],
            i18n.t("sidebar_section_advanced"): [
                (i18n.t("tab_logs"), "logs"),
                (i18n.t("tab_plugins"), "plugins"),
                (i18n.t("tab_advanced"), "advanced"),
            ],
        }
        self.sidebar.update_ui_texts(section_configs)

    def toggle_sidebar(self):
        """Toggle sidebar visibility"""
        self._sidebar_collapsed = not self._sidebar_collapsed
        
        if self._sidebar_collapsed:
            self.sidebar.setMaximumWidth(0)
            self.sidebar.setMinimumWidth(0)
            self.sidebar.set_collapsed(True)
            self.sidebar_toggle_btn.setText("▶")
        else:
            self.sidebar.setMaximumWidth(self._sidebar_width)
            self.sidebar.setMinimumWidth(self._sidebar_width)
            self.sidebar.set_collapsed(False)
            self.sidebar_toggle_btn.setText("☰")

    def switch_to_panel(self, panel_name: str):
        """Switch to a specific panel"""
        if panel_name in self.panel_map:
            self.stacked_widget.setCurrentWidget(self.panel_map[panel_name])
            self.sidebar.select_panel(panel_name)
            if panel_name == "advanced":
                refresh_startup_samples = getattr(self.advanced_panel, "refresh_startup_samples", None)
                if callable(refresh_startup_samples):
                    refresh_startup_samples()

    def _launch_sample_on_startup(self):
        if not Config.get_setting("launch_sample_on_startup", False):
            return

        sample_name = str(Config.get_setting("startup_sample_instance", "openclaw") or "").strip()
        if not sample_name:
            QMessageBox.warning(
                self,
                i18n.t("title_warning"),
                i18n.t("msg_startup_sample_launch_failed", name="(empty)", error=i18n.t("msg_instance_not_found")),
            )
            return

        try:
            if ProcessManager.get_status(sample_name) == "Running":
                return

            instance_path = Config.get_instance_path(sample_name)
            if not instance_path.exists() or not instance_path.is_dir():
                raise FileNotFoundError(i18n.t("msg_instance_not_found"))

            ProcessManager.start_instance(sample_name, instance_path)
        except Exception as e:
            QMessageBox.warning(
                self,
                i18n.t("title_warning"),
                i18n.t("msg_startup_sample_launch_failed", name=sample_name, error=str(e)),
            )

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
        new_lang = "zh" if i18n.current_lang == "en" else "en"
        i18n.set_language(new_lang)

    def on_language_changed(self, lang):
        self.update_ui_texts()
        # Propagate to panels if they have update_ui_texts method
        for panel in [self.onboard_panel, self.instance_panel, self.dependency_panel, self.backup_panel, self.log_panel, self.plugin_panel, self.env_var_panel, self.channel_config_panel, self.llamacpp_panel, self.model_switch_panel, self.advanced_panel]:
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
        self._setup_sidebar_sections()
        if hasattr(self, "tray_icon") and self.tray_icon:
            self.tray_icon.setToolTip(i18n.t("app_title"))
        if hasattr(self, "action_show") and self.action_show:
            self.action_show.setText(i18n.t("tray_show_window"))
        if hasattr(self, "action_quit") and self.action_quit:
            self.action_quit.setText(i18n.t("tray_quit"))

    def switch_to_tab(self, tab_key: str):
        """Handle navigation from panels to other panels"""
        panel_map = {
            "channels": "channels",
            "llamacpp": "llamacpp",
            "model_switch": "model_switch",
        }
        target_name = panel_map.get(str(tab_key or "").strip())
        if target_name is not None:
            self.switch_to_panel(target_name)
    
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

        for panel in [self.onboard_panel, self.instance_panel, self.dependency_panel, self.backup_panel, self.log_panel, self.plugin_panel, self.env_var_panel, self.channel_config_panel, self.llamacpp_panel, self.model_switch_panel, self.advanced_panel]:
            shutdown = getattr(panel, "shutdown", None)
            if callable(shutdown):
                try:
                    shutdown()
                except Exception:
                    pass

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
