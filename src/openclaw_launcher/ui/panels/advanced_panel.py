from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QCheckBox, QGroupBox, QScrollArea, QMessageBox, QComboBox
)
from ...core.config import Config
from ...core.autostart_manager import AutoStartManager
from ...core.process_manager import ProcessManager
from ..i18n import i18n
import shutil
import os
import stat
import time

class AdvancedPanel(QWidget):
    def __init__(self):
        super().__init__()
        # Use a main layout for the widget itself but containing the ScrollArea
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # ScrollArea
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.content_widget = QWidget()
        self.layout = QVBoxLayout(self.content_widget)
        self.scroll.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll)

        # ----------------------
        # General Settings (通用)
        # ----------------------
        self.grp_general = QGroupBox()
        self.layout_general = QVBoxLayout(self.grp_general)

        # Close Action
        self.lbl_close_action = QLabel()
        self.chk_minimize_tray = QCheckBox()
        self.lbl_tray_desc = QLabel()
        self.lbl_tray_desc.setStyleSheet("color: gray; font-size: 11px;")
        
        self.layout_general.addWidget(self.lbl_close_action)
        self.layout_general.addWidget(self.chk_minimize_tray)
        self.layout_general.addWidget(self.lbl_tray_desc)
        self.layout_general.addSpacing(10)

        # Update Check
        self.lbl_check_updates = QLabel()
        self.chk_check_updates = QCheckBox()
        self.lbl_updates_desc = QLabel()
        self.lbl_updates_desc.setStyleSheet("color: gray; font-size: 11px;")

        self.layout_general.addWidget(self.lbl_check_updates)
        self.layout_general.addWidget(self.chk_check_updates)
        self.layout_general.addWidget(self.lbl_updates_desc)
        self.layout_general.addSpacing(10)

        # Windows A2UI Patch
        self.lbl_windows_patch = QLabel()
        self.chk_windows_patch = QCheckBox()
        self.lbl_windows_patch_desc = QLabel()
        self.lbl_windows_patch_desc.setStyleSheet("color: gray; font-size: 11px;")
        self.lbl_windows_patch_desc.setWordWrap(True)

        self.layout_general.addWidget(self.lbl_windows_patch)
        self.layout_general.addWidget(self.chk_windows_patch)
        self.layout_general.addWidget(self.lbl_windows_patch_desc)
        self.layout_general.addSpacing(10)

        # Auto Start
        self.lbl_auto_start = QLabel()
        self.chk_auto_start = QCheckBox()
        self.lbl_auto_start_desc = QLabel()
        self.lbl_auto_start_desc.setStyleSheet("color: gray; font-size: 11px;")
        self.lbl_auto_start_status = QLabel()
        self.lbl_auto_start_status.setStyleSheet("color: gray; font-size: 11px;")

        self.layout_general.addWidget(self.lbl_auto_start)
        self.layout_general.addWidget(self.chk_auto_start)
        self.layout_general.addWidget(self.lbl_auto_start_desc)
        self.layout_general.addWidget(self.lbl_auto_start_status)
        self.layout_general.addSpacing(10)

        # Startup Behavior
        self.lbl_startup_behavior = QLabel()
        self.chk_start_minimized = QCheckBox()
        self.chk_auto_start_llamacpp = QCheckBox()
        self.chk_launch_sample_on_startup = QCheckBox()
        self.cmb_startup_sample = QComboBox()
        self.lbl_startup_behavior_desc = QLabel()
        self.lbl_startup_behavior_desc.setStyleSheet("color: gray; font-size: 11px;")
        self.lbl_startup_behavior_desc.setWordWrap(True)

        startup_sample_row = QHBoxLayout()
        startup_sample_row.addWidget(self.chk_launch_sample_on_startup)
        startup_sample_row.addWidget(self.cmb_startup_sample)

        self.layout_general.addWidget(self.lbl_startup_behavior)
        self.layout_general.addWidget(self.chk_start_minimized)
        self.layout_general.addWidget(self.chk_auto_start_llamacpp)
        self.layout_general.addLayout(startup_sample_row)
        self.layout_general.addWidget(self.lbl_startup_behavior_desc)
        self.layout_general.addSpacing(10)

        self.layout.addWidget(self.grp_general)

        # ----------------------
        # Sources (源)
        # ----------------------
        self.grp_sources = QGroupBox()
        self.layout_sources = QVBoxLayout(self.grp_sources)

        # Helper method for source input row
        def create_source_row(label_key, desc_key, config_key, default_val):
            lbl = QLabel()
            ipt = QLineEdit()
            # Restore value
            current_val = Config.get_setting(config_key, default_val)
            ipt.setText(current_val)
            
            desc = QLabel()
            desc.setStyleSheet("color: gray; font-size: 11px;")
            desc.setWordWrap(True)
            
            btn_save = QPushButton("Save")
            
            row = QHBoxLayout()
            row.addWidget(ipt)
            row.addWidget(btn_save)

            self.layout_sources.addWidget(lbl)
            self.layout_sources.addLayout(row)
            self.layout_sources.addWidget(desc)
            self.layout_sources.addSpacing(10)
            
            # Connect save
            # Use default args to capture current key/ipt
            btn_save.clicked.connect(lambda checked=False, k=config_key, i=ipt: self.save_source(k, i.text()))
            
            return lbl, ipt, desc, btn_save, desc_key, label_key

        # Github Proxy
        self.src_github = create_source_row("lbl_github_proxy", "desc_github_proxy", "github_proxy", "https://ghfast.top/https://github.com")
        # PyPI Mirror
        self.src_pypi = create_source_row("lbl_pypi_mirror", "desc_pypi_mirror", "pypi_mirror", "https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple")
        # Node Mirror
        self.src_node = create_source_row("lbl_node_mirror", "desc_node_mirror", "node_mirror", "https://npmmirror.com/mirrors/node")
        # npm Registry
        self.src_npm = create_source_row("lbl_npm_registry", "desc_npm_registry", "npm_registry", "https://registry.npmmirror.com")
        
        self.layout.addWidget(self.grp_sources)

        # ----------------------
        # Troubleshoot (故障排除)
        # ----------------------
        self.grp_troubleshoot = QGroupBox()
        self.layout_troubleshoot = QVBoxLayout(self.grp_troubleshoot)
        
        self.lbl_troubleshoot_hint = QLabel()
        self.lbl_troubleshoot_hint.setStyleSheet("color: orange;")
        self.layout_troubleshoot.addWidget(self.lbl_troubleshoot_hint)
        self.layout_troubleshoot.addSpacing(5)

        # Clear Dependencies
        row_dependencies = QHBoxLayout()
        self.lbl_clear_dependencies = QLabel()
        self.btn_clear_dependencies = QPushButton()
        row_dependencies.addWidget(self.lbl_clear_dependencies)
        row_dependencies.addStretch()
        row_dependencies.addWidget(self.btn_clear_dependencies)
        self.layout_troubleshoot.addLayout(row_dependencies)

        self.lbl_clear_dependencies_desc = QLabel()
        self.lbl_clear_dependencies_desc.setStyleSheet("color: gray; font-size: 11px;")
        self.lbl_clear_dependencies_desc.setWordWrap(True)
        self.layout_troubleshoot.addWidget(self.lbl_clear_dependencies_desc)

        # Clear Instances
        row_instances = QHBoxLayout()
        self.lbl_clear_instances = QLabel()
        self.btn_clear_instances = QPushButton()
        row_instances.addWidget(self.lbl_clear_instances)
        row_instances.addStretch()
        row_instances.addWidget(self.btn_clear_instances)
        self.layout_troubleshoot.addLayout(row_instances)

        # Clear Backups
        row_backups = QHBoxLayout()
        self.lbl_clear_backups = QLabel()
        self.btn_clear_backups = QPushButton()
        row_backups.addWidget(self.lbl_clear_backups)
        row_backups.addStretch()
        row_backups.addWidget(self.btn_clear_backups)
        self.layout_troubleshoot.addLayout(row_backups)

        self.layout.addWidget(self.grp_troubleshoot)
        self.layout.addStretch()

        # Connect General Settings
        self.chk_minimize_tray.stateChanged.connect(lambda: self.save_general("minimize_to_tray", self.chk_minimize_tray.isChecked()))
        self.chk_check_updates.stateChanged.connect(lambda: self.save_general("check_updates", self.chk_check_updates.isChecked()))
        self.chk_windows_patch.stateChanged.connect(lambda: self.save_general("windows_a2ui_patch", self.chk_windows_patch.isChecked()))
        self.chk_auto_start_llamacpp.stateChanged.connect(lambda: self.save_general("auto_start_llamacpp", self.chk_auto_start_llamacpp.isChecked()))
        self.chk_auto_start.stateChanged.connect(self.on_auto_start_changed)
        self.chk_start_minimized.stateChanged.connect(lambda: self.save_general("start_minimized", self.chk_start_minimized.isChecked()))
        self.chk_launch_sample_on_startup.stateChanged.connect(self.on_launch_sample_on_startup_changed)
        self.cmb_startup_sample.currentIndexChanged.connect(self.on_startup_sample_changed)

        # Connect Troubleshoot Actions
        self.btn_clear_dependencies.clicked.connect(self.execute_clear_dependencies)
        self.btn_clear_instances.clicked.connect(self.execute_clear_instances)
        self.btn_clear_backups.clicked.connect(self.execute_clear_backups)

        self.update_ui_texts()
        self.load_settings()

    def load_settings(self):
        self.chk_minimize_tray.setChecked(Config.get_setting("minimize_to_tray", False))
        self.chk_check_updates.setChecked(Config.get_setting("check_updates", False))
        self.chk_windows_patch.setChecked(Config.get_setting("windows_a2ui_patch", True))
        self.chk_auto_start_llamacpp.setChecked(Config.get_setting("auto_start_llamacpp", False))
        self.chk_start_minimized.setChecked(Config.get_setting("start_minimized", False))
        auto_start_checked = Config.get_setting("auto_start", False)
        if AutoStartManager.is_supported():
            try:
                auto_start_checked = AutoStartManager.is_enabled()
                Config.set_setting("auto_start", auto_start_checked)
            except Exception:
                pass
        self.chk_auto_start.blockSignals(True)
        self.chk_auto_start.setChecked(auto_start_checked)
        self.chk_auto_start.blockSignals(False)

        startup_sample_name = str(Config.get_setting("startup_sample_instance", "openclaw") or "").strip()
        self._reload_startup_sample_options(selected_name=startup_sample_name)

        launch_sample_checked = Config.get_setting("launch_sample_on_startup", False)
        self.chk_launch_sample_on_startup.blockSignals(True)
        self.chk_launch_sample_on_startup.setChecked(bool(launch_sample_checked))
        self.chk_launch_sample_on_startup.blockSignals(False)
        self._update_startup_sample_controls_state()

        self.refresh_auto_start_status()

    def _reload_startup_sample_options(self, selected_name: str | None = None):
        names = []
        if Config.INSTANCES_DIR.exists():
            names = [
                item.name
                for item in sorted(Config.INSTANCES_DIR.iterdir(), key=lambda p: p.name.lower())
                if item.is_dir()
            ]

        self.cmb_startup_sample.blockSignals(True)
        self.cmb_startup_sample.clear()
        if names:
            for name in names:
                self.cmb_startup_sample.addItem(name, name)
        else:
            self.cmb_startup_sample.addItem(i18n.t("opt_no_samples"), "")

        effective_selected = (selected_name or "").strip()
        if not effective_selected:
            effective_selected = str(Config.get_setting("startup_sample_instance", "openclaw") or "").strip()

        idx = self.cmb_startup_sample.findData(effective_selected)
        if idx >= 0:
            self.cmb_startup_sample.setCurrentIndex(idx)
        elif names:
            self.cmb_startup_sample.setCurrentIndex(0)
            Config.set_setting("startup_sample_instance", self.cmb_startup_sample.currentData())
        else:
            Config.set_setting("startup_sample_instance", "")
        self.cmb_startup_sample.blockSignals(False)

    def _update_startup_sample_controls_state(self):
        has_samples = bool(self.cmb_startup_sample.count() and self.cmb_startup_sample.currentData())
        self.cmb_startup_sample.setEnabled(self.chk_launch_sample_on_startup.isChecked() and has_samples)

    def on_launch_sample_on_startup_changed(self):
        enabled = self.chk_launch_sample_on_startup.isChecked()
        self.save_general("launch_sample_on_startup", enabled)
        self._update_startup_sample_controls_state()

    def on_startup_sample_changed(self):
        sample_name = self.cmb_startup_sample.currentData() or ""
        self.save_general("startup_sample_instance", sample_name)

    def refresh_startup_samples(self):
        selected_name = str(Config.get_setting("startup_sample_instance", "openclaw") or "").strip()
        self._reload_startup_sample_options(selected_name=selected_name)
        self._update_startup_sample_controls_state()

    def update_ui_texts(self):
        # General
        self.grp_general.setTitle(i18n.t("grp_general"))
        self.lbl_close_action.setText(i18n.t("lbl_close_action"))
        self.chk_minimize_tray.setText(i18n.t("opt_minimize_tray"))
        self.lbl_tray_desc.setText(i18n.t("desc_close_action")) 

        self.lbl_check_updates.setText(i18n.t("lbl_check_updates"))
        self.chk_check_updates.setText(i18n.t("opt_enabled"))
        self.lbl_updates_desc.setText(i18n.t("desc_check_updates"))

        self.lbl_windows_patch.setText(i18n.t("lbl_windows_patch"))
        self.chk_windows_patch.setText(i18n.t("opt_enabled"))
        self.lbl_windows_patch_desc.setText(i18n.t("desc_windows_patch"))

        self.lbl_auto_start.setText(i18n.t("lbl_auto_start"))
        self.chk_auto_start.setText(i18n.t("opt_enabled"))
        self.lbl_auto_start_desc.setText(i18n.t("desc_auto_start"))
        self.refresh_auto_start_status()

        self.lbl_startup_behavior.setText(i18n.t("lbl_startup_behavior"))
        self.chk_start_minimized.setText(i18n.t("opt_start_minimized"))
        self.chk_auto_start_llamacpp.setText(i18n.t("opt_auto_start_llamacpp"))
        self.chk_launch_sample_on_startup.setText(i18n.t("opt_launch_sample_on_startup"))
        self.lbl_startup_behavior_desc.setText(i18n.t("desc_startup_behavior"))

        startup_sample_name = str(Config.get_setting("startup_sample_instance", "openclaw") or "").strip()
        self._reload_startup_sample_options(selected_name=startup_sample_name)
        self._update_startup_sample_controls_state()

        # Sources
        self.grp_sources.setTitle(i18n.t("grp_sources"))
        
        def update_src_row(row_tuple):
            lbl, ipt, desc, btn, desc_key, label_key = row_tuple
            lbl.setText(i18n.t(label_key))
            desc.setText(i18n.t(desc_key))
            btn.setText(i18n.t("btn_save"))
        
        update_src_row(self.src_github)
        update_src_row(self.src_pypi)
        update_src_row(self.src_node)
        update_src_row(self.src_npm)

        # Troubleshoot
        self.grp_troubleshoot.setTitle(i18n.t("grp_troubleshoot"))
        self.lbl_troubleshoot_hint.setText(i18n.t("lbl_troubleshoot_hint"))
        self.lbl_clear_dependencies.setText(i18n.t("lbl_clear_dependencies"))
        self.btn_clear_dependencies.setText(i18n.t("btn_execute"))
        self.lbl_clear_dependencies_desc.setText(i18n.t("desc_clear_dependencies"))
        self.lbl_clear_instances.setText(i18n.t("lbl_clear_instances"))
        self.btn_clear_instances.setText(i18n.t("btn_execute"))
        self.lbl_clear_backups.setText(i18n.t("lbl_clear_backups"))
        self.btn_clear_backups.setText(i18n.t("btn_execute"))

    def save_general(self, key, value):
        Config.set_setting(key, value)

    def on_auto_start_changed(self):
        value = self.chk_auto_start.isChecked()
        try:
            AutoStartManager.set_enabled(value)
            Config.set_setting("auto_start", value)
            self.refresh_auto_start_status()
        except Exception as e:
            self.chk_auto_start.blockSignals(True)
            self.chk_auto_start.setChecked(not value)
            self.chk_auto_start.blockSignals(False)
            self.refresh_auto_start_status()
            QMessageBox.critical(self, i18n.t("title_error"), i18n.t("msg_auto_start_failed", error=str(e)))

    def refresh_auto_start_status(self):
        if not AutoStartManager.is_supported():
            self.lbl_auto_start_status.setText(i18n.t("auto_start_status_unknown"))
            return

        try:
            if AutoStartManager.is_enabled():
                self.lbl_auto_start_status.setText(i18n.t("auto_start_status_enabled"))
            else:
                self.lbl_auto_start_status.setText(i18n.t("auto_start_status_disabled"))
        except Exception:
            self.lbl_auto_start_status.setText(i18n.t("auto_start_status_unknown"))
    
    def save_source(self, key, value):
        Config.set_setting(key, value)
        message = i18n.t("msg_saved_setting").format(key=key)
        QMessageBox.information(self, i18n.t("title_success"), message)

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

    def execute_clear_dependencies(self):
        reply = QMessageBox.question(
            self,
            i18n.t("title_confirm"),
            i18n.t("msg_confirm_clear_dependencies"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            runtime_dir = Config.BASE_DIR / "runtime"
            if runtime_dir.exists():
                self._remove_dir_with_retries(runtime_dir)
            runtime_dir.mkdir(parents=True, exist_ok=True)
            QMessageBox.information(self, i18n.t("title_success"), i18n.t("msg_clear_dependencies_success"))
        except Exception as e:
            QMessageBox.critical(self, i18n.t("title_error"), i18n.t("msg_operation_failed", error=str(e)))

    def execute_clear_instances(self):
        reply = QMessageBox.question(
            self,
            i18n.t("title_confirm"),
            i18n.t("msg_confirm_clear_instances"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            ProcessManager.stop_all_instances()
            time.sleep(0.2)
            if Config.INSTANCES_DIR.exists():
                self._remove_dir_with_retries(Config.INSTANCES_DIR)
            Config.INSTANCES_DIR.mkdir(parents=True, exist_ok=True)
            QMessageBox.information(self, i18n.t("title_success"), i18n.t("msg_clear_instances_success"))
        except Exception as e:
            QMessageBox.critical(self, i18n.t("title_error"), i18n.t("msg_operation_failed", error=str(e)))

    def execute_clear_backups(self):
        reply = QMessageBox.question(
            self,
            i18n.t("title_confirm"),
            i18n.t("msg_confirm_clear_backups"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            backup_dir = Config.BASE_DIR / "backups"
            if backup_dir.exists():
                self._remove_dir_with_retries(backup_dir)
            backup_dir.mkdir(parents=True, exist_ok=True)
            QMessageBox.information(self, i18n.t("title_success"), i18n.t("msg_clear_backups_success"))
        except Exception as e:
            QMessageBox.critical(self, i18n.t("title_error"), i18n.t("msg_operation_failed", error=str(e)))
