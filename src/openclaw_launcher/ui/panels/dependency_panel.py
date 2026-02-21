from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, 
    QScrollArea, QFrame, QGridLayout, QMessageBox, QStyle, QSizePolicy, QProgressDialog
)
from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtGui import QFont, QIcon, QDesktopServices
from ...core.runtime_manager import RuntimeManager
from ...core.process_manager import ProcessManager
from ..i18n import i18n

class DownloadWorker(QThread):
    completed = Signal()
    error = Signal(str)
    progress = Signal(int, int, str)

    def __init__(self, manager, software, version):
        super().__init__()
        self.manager = manager
        self.software = software
        self.version = version

    def run(self):
        try:
            self.manager.install_version(self.software, self.version, callback=self._on_progress)
            self.completed.emit()
        except Exception as e:
            self.error.emit(str(e))

    def _on_progress(self, payload):
        if not isinstance(payload, dict):
            return

        current = payload.get("current")
        total = payload.get("total")
        message = payload.get("message", "")

        safe_current = int(current) if isinstance(current, (int, float)) else -1
        safe_total = int(total) if isinstance(total, (int, float)) else -1
        self.progress.emit(safe_current, safe_total, str(message))

class SoftwareCard(QFrame):
    def __init__(self, title_key, software_key, manager, parent_panel, collapsed: bool = False):
        super().__init__()
        self.manager = manager
        self.software_key = software_key
        self.title_key = title_key # Store the key, not the translated string
        self.parent_panel = parent_panel
        self._collapsed = bool(collapsed)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        # Allow vertical resizing, preferring minimum height
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        
        self.layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Icon
        icon_label = QLabel()
        icon = self.style().standardIcon(QStyle.SP_ComputerIcon) # Generic icon
        icon_label.setPixmap(icon.pixmap(32, 32))
        header_layout.addWidget(icon_label)
        
        self.title_label = QLabel(i18n.t(self.title_key))
        font = QFont()
        font.setBold(True)
        font.setPointSize(14)
        self.title_label.setFont(font)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        self.toggle_btn = QPushButton()
        self.toggle_btn.setFixedWidth(28)
        self.toggle_btn.setFixedHeight(24)
        self.toggle_btn.setFlat(True)
        self.toggle_btn.clicked.connect(self.toggle_collapsed)
        header_layout.addWidget(self.toggle_btn)
        self.layout.addLayout(header_layout)

        # Content container + layout (for collapsing)
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.content_widget)

        self._sync_collapsed_state()
        
        self.refresh_ui()

    def toggle_collapsed(self):
        self._collapsed = not self._collapsed
        self._sync_collapsed_state()

    def _sync_collapsed_state(self):
        self.content_widget.setVisible(not self._collapsed)
        arrow_icon_type = QStyle.SP_ArrowRight if self._collapsed else QStyle.SP_ArrowDown
        self.toggle_btn.setIcon(self.style().standardIcon(arrow_icon_type))
        self.toggle_btn.setText("")

    def refresh_ui(self):
        # Update title in case language changed
        self.title_label.setText(i18n.t(self.title_key))
        self._sync_collapsed_state()

        # Clear existing content
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                # For nested layouts, we must recursively clear items or delete the widget containing layout
                # Since we wrapped rows in QWidgets below, it's safer.
                pass

        # 1. Installed Types
        installed_label = QLabel(i18n.t("section_installed"))
        font = QFont()
        font.setBold(True)
        installed_label.setFont(font)
        self.content_layout.addWidget(installed_label)

        installed_versions = self.manager.get_installed_versions(self.software_key)
        default_version = self.manager.get_default_version(self.software_key)
        
        if not installed_versions:
            no_inst = QLabel(i18n.t("status_no_installed"))
            no_inst.setStyleSheet("color: gray;")
            self.content_layout.addWidget(no_inst)
        else:
            for ver in installed_versions:
                row_widget = QWidget()
                row = QHBoxLayout(row_widget)
                row.setContentsMargins(0, 0, 0, 0)
                is_default = ver['version'] == default_version
                
                v_label = QLabel(ver['version'])
                if is_default:
                    v_label.setStyleSheet("font-weight: bold; text-decoration: underline;")
                else:
                    v_label.setStyleSheet("font-weight: bold;")
                row.addWidget(v_label)

                if is_default:
                    default_tag = QLabel(i18n.t("tag_default"))
                    default_tag.setStyleSheet("font-size: 11px; font-weight: bold;")
                    row.addWidget(default_tag)
                
                row.addStretch()
                
                d_label = QLabel(ver['date'])
                d_label.setStyleSheet("color: gray;")
                row.addWidget(d_label)

                btn_default = QPushButton(i18n.t("btn_set_default"))
                btn_default.setMinimumWidth(100)
                if is_default:
                    btn_default.setEnabled(False)
                    btn_default.setText(i18n.t("btn_default_in_use"))
                else:
                    btn_default.clicked.connect(
                        lambda checked=False, s=self.software_key, v=ver['version']: self.parent_panel.set_default_version(s, v)
                    )
                row.addWidget(btn_default)
                
                btn_del = QPushButton(i18n.t("btn_delete"))
                # Remove fixed width, let layout handle it or set a minimum
                btn_del.setMinimumWidth(80) 
                btn_del.setEnabled(False) # Impl later
                row.addWidget(btn_del)
                
                self.content_layout.addWidget(row_widget)

        self.content_layout.addSpacing(15)

        # 2. Available Types
        available_label = QLabel(i18n.t("section_available"))
        available_label.setFont(font)
        self.content_layout.addWidget(available_label)

        avail_versions = self.manager.get_available_versions(self.software_key)
        
        if not avail_versions:
             self.content_layout.addWidget(QLabel(i18n.t("msg_no_versions")))
        else:
            # Grid for available versions
            grid_widget = QWidget()
            grid = QGridLayout(grid_widget)
            grid.setContentsMargins(0, 0, 0, 0)
            
            # Headers
            lbl_ver = QLabel(i18n.t("col_version"))
            lbl_ver.setStyleSheet("color: gray;")
            grid.addWidget(lbl_ver, 0, 0)
            
            lbl_date = QLabel(i18n.t("col_date"))
            lbl_date.setStyleSheet("color: gray;")
            grid.addWidget(lbl_date, 0, 1)
            
            grid.setColumnStretch(1, 1) # Space out the date

            for i, ver in enumerate(avail_versions):
                v_str = ver['version']
                date_str = ver['date']
                
                # Check if already installed
                is_installed = self.manager.is_installed(self.software_key, v_str)
                is_downloading = self.parent_panel.is_downloading_version(self.software_key, v_str)
                
                v_label = QLabel(v_str)
                grid.addWidget(v_label, i+1, 0)
                
                d_label = QLabel(date_str)
                d_label.setStyleSheet("color: gray;")
                grid.addWidget(d_label, i+1, 1)
                
                btn_dl = QPushButton(i18n.t("btn_download"))
                btn_dl.setMinimumWidth(100) # Increased min width
                
                if is_installed:
                    btn_dl.setEnabled(False)
                    btn_dl.setText(i18n.t("btn_installed"))
                elif is_downloading:
                    btn_dl.setEnabled(False)
                    btn_dl.setText(i18n.t("btn_downloading"))
                else:
                    # Fix closure
                    btn_dl.clicked.connect(lambda checked=False, s=self.software_key, v=v_str: self.parent_panel.start_download(s, v))
                
                grid.addWidget(btn_dl, i+1, 2)
            
            self.content_layout.addWidget(grid_widget)


class DependencyPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.runtime_manager = RuntimeManager()
        self.download_worker = None
        self.progress_dialog = None
        self._current_download_software = ""
        self._current_download_version = ""
        self.main_layout = QVBoxLayout(self)

        # Top Bar
        top_layout = QHBoxLayout()
        top_layout.addStretch()
        self.lbl_openclaw_last_refresh = QLabel()
        self.lbl_openclaw_last_refresh.setStyleSheet("color: gray; font-size: 11px;")
        top_layout.addWidget(self.lbl_openclaw_last_refresh)
        self.btn_refresh = QPushButton(i18n.t("btn_refresh"))
        self.btn_refresh.clicked.connect(lambda: self.refresh_all_cards(force_remote_refresh=True))
        top_layout.addWidget(self.btn_refresh)
        self.main_layout.addLayout(top_layout)

        self._update_openclaw_last_refresh_text()
        
        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        content_widget = QWidget()
        self.scroll_layout = QVBoxLayout(content_widget)
        self.scroll_layout.setSpacing(20)
        
        self.cards = []
        
        # Pass KEYS instead of Translated Text
        self.card_openclaw = SoftwareCard("runtime_openclaw", RuntimeManager.SOFTWARE_OPENCLAW, self.runtime_manager, self)
        self.scroll_layout.addWidget(self.card_openclaw)
        self.cards.append(self.card_openclaw)
        
        self.card_node = SoftwareCard("runtime_node", RuntimeManager.SOFTWARE_NODE, self.runtime_manager, self)
        self.scroll_layout.addWidget(self.card_node)
        self.cards.append(self.card_node)

        self.card_python = SoftwareCard("runtime_python", RuntimeManager.SOFTWARE_PYTHON, self.runtime_manager, self, collapsed=True)
        self.scroll_layout.addWidget(self.card_python)
        self.cards.append(self.card_python)

        self.card_uv = SoftwareCard("runtime_uv", RuntimeManager.SOFTWARE_UV, self.runtime_manager, self, collapsed=True)
        self.scroll_layout.addWidget(self.card_uv)
        self.cards.append(self.card_uv)

        self.scroll_layout.addStretch()
        scroll.setWidget(content_widget)
        self.main_layout.addWidget(scroll)

    def start_download(self, software, version):
        if self.download_worker:
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("msg_download_busy"))
            return

        self._current_download_software = software
        self._current_download_version = version
        self.progress_dialog = QProgressDialog(
            i18n.t("status_downloading", version=version),
            "",
            0,
            0,
            self,
        )
        self.progress_dialog.setWindowTitle(i18n.t("btn_downloading"))
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setCancelButton(None)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.show()
        
        self.download_worker = DownloadWorker(self.runtime_manager, software, version)
        self.download_worker.progress.connect(self.on_download_progress)
        self.download_worker.completed.connect(self.on_download_finished)
        self.download_worker.error.connect(self.on_download_error)
        self.download_worker.start()
        self.refresh_all_cards()

    def is_downloading_version(self, software: str, version: str) -> bool:
        worker = getattr(self, "download_worker", None)
        if not worker:
            return False
        return self._current_download_software == software and self._current_download_version == version

    def on_download_progress(self, current: int, total: int, message: str):
        if not self.progress_dialog:
            return

        if total > 0 and current >= 0:
            if self.progress_dialog.maximum() == 0:
                self.progress_dialog.setRange(0, 100)

            percent = int(min(100, max(0, current * 100 / total)))
            self.progress_dialog.setValue(percent)
        else:
            self.progress_dialog.setRange(0, 0)

        if message:
            self.progress_dialog.setLabelText(message)
        else:
            self.progress_dialog.setLabelText(i18n.t("status_downloading", version=self._current_download_version))

    def set_default_version(self, software, version):
        try:
            self.runtime_manager.set_default_version(software, version)
            message = i18n.t("msg_set_default_success", version=version)
            if ProcessManager.has_running_instances():
                message = message + "\n" + i18n.t("msg_default_restart_hint")
            QMessageBox.information(
                self,
                i18n.t("title_success"),
                message
            )
            self.refresh_all_cards()
        except Exception as err:
            QMessageBox.critical(self, i18n.t("title_error"), i18n.t("msg_set_default_failed", error=str(err)))

    def on_download_finished(self):
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        self._current_download_software = ""
        self._current_download_version = ""
        self.download_worker = None
        QMessageBox.information(self, i18n.t("title_success"), i18n.t("msg_download_complete"))
        self.refresh_all_cards()

    def on_download_error(self, err):
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        self._current_download_software = ""
        self._current_download_version = ""
        self.download_worker = None
        QMessageBox.critical(self, i18n.t("title_error"), i18n.t("msg_download_failed", error=err))
        self.refresh_all_cards()

    def refresh_all_cards(self, force_remote_refresh: bool = False):
        if force_remote_refresh:
            self.runtime_manager.refresh_available_versions(RuntimeManager.SOFTWARE_OPENCLAW)
        self._update_openclaw_last_refresh_text()
        for card in self.cards:
            card.refresh_ui() # This now handles title update too

    def _update_openclaw_last_refresh_text(self):
        refreshed_at = self.runtime_manager.get_available_versions_refreshed_at(RuntimeManager.SOFTWARE_OPENCLAW)
        if refreshed_at:
            self.lbl_openclaw_last_refresh.setText(i18n.t("lbl_openclaw_last_refresh", time=refreshed_at))
        else:
            self.lbl_openclaw_last_refresh.setText(i18n.t("lbl_openclaw_last_refresh_never"))

    def update_ui_texts(self):
        self.btn_refresh.setText(i18n.t("btn_refresh"))
        self._update_openclaw_last_refresh_text()
        self.refresh_all_cards()

    def shutdown(self):
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        self._current_download_software = ""
        self._current_download_version = ""
        worker = self.download_worker
        if worker and worker.isRunning():
            worker.requestInterruption()
            worker.wait(2000)
            if worker.isRunning():
                worker.terminate()
                worker.wait(1000)
        self.download_worker = None
