from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QMessageBox,
    QProgressBar,
)
from PySide6.QtCore import QThread, Signal, QTimer, Qt
from PySide6.QtGui import QDesktopServices, QPixmap, QImageReader
from PySide6.QtCore import QUrl
from pathlib import Path
import os

from ...core.config import Config
from ...core.install_manager import InstallManager
from ...core.process_manager import ProcessManager
from ...core.runtime_manager import RuntimeManager
from ..i18n import i18n
from datetime import datetime


def _resolve_logo_path() -> str | None:
    candidates = []
    import sys, os
    if hasattr(sys, "_MEIPASS"):
        candidates.append(os.path.join(sys._MEIPASS, "teaser.png"))

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..",  "..", ".."))
    candidates.append(os.path.join(project_root, "teaser.png"))

    candidates.append(os.path.join(os.getcwd(), "teaser.png"))

    for path in candidates:
        if os.path.exists(path):
            return path
    return None

class InstallDependenciesWorker(QThread):
    completed = Signal()
    error = Signal(str)
    progress = Signal(str)
    progress_percentage = Signal(int)

    def __init__(self):
        super().__init__()

    def run(self):
        try:
            manager = RuntimeManager()

            # ensure logs dir exists and open installer log
            try:
                Config.ensure_dirs()
                log_path = Config.get_log_file("installer")
                log_f = open(log_path, "a", encoding="utf-8")
            except Exception:
                log_f = None

            def _write_log(msg: str):
                if not msg:
                    return
                try:
                    if log_f:
                        log_f.write(f"{datetime.now().isoformat()} {msg}\n")
                        log_f.flush()
                except Exception:
                    pass

            # Node.js runtime
            if not manager.get_default_version(RuntimeManager.SOFTWARE_NODE):
                node_versions = manager.get_available_versions(RuntimeManager.SOFTWARE_NODE)
                if not node_versions:
                    raise RuntimeError("No available Node.js versions")

                node_target = str(node_versions[0]["version"])
                msg = i18n.t("onboard_status_installing_dep", name=i18n.t("runtime_node"), version=node_target)
                self.progress.emit(msg)
                _write_log(msg)
                self.progress_percentage.emit(25)
                manager.install_version(RuntimeManager.SOFTWARE_NODE, node_target)
                self.progress_percentage.emit(50)
                manager.set_default_version(RuntimeManager.SOFTWARE_NODE, node_target)

            # OpenClaw runtime
            if not manager.get_default_version(RuntimeManager.SOFTWARE_OPENCLAW):
                msg = i18n.t("onboard_status_refresh_openclaw")
                self.progress.emit(msg)
                _write_log(msg)
                self.progress_percentage.emit(60)
                manager.refresh_available_versions(RuntimeManager.SOFTWARE_OPENCLAW)
                openclaw_versions = manager.get_available_versions(RuntimeManager.SOFTWARE_OPENCLAW)
                if not openclaw_versions:
                    raise RuntimeError("No available OpenClaw versions")

                openclaw_target = str(openclaw_versions[0]["version"])
                msg = i18n.t("onboard_status_installing_dep", name=i18n.t("runtime_openclaw"), version=openclaw_target)
                self.progress.emit(msg)
                _write_log(msg)
                self.progress_percentage.emit(80)
                manager.install_version(RuntimeManager.SOFTWARE_OPENCLAW, openclaw_target)
                self.progress_percentage.emit(95)
                manager.set_default_version(RuntimeManager.SOFTWARE_OPENCLAW, openclaw_target)

            self.progress_percentage.emit(100)
            msg = i18n.t("onboard_msg_dependencies_done")
            _write_log(msg)
            self.completed.emit()
        except Exception as e:
            # log error to installer log as well
            try:
                _write_log(f"Error: {str(e)}")
            except Exception:
                pass
            self.error.emit(str(e))
        finally:
            try:
                if 'log_f' in locals() and log_f:
                    log_f.close()
            except Exception:
                pass


class CreateSampleWorker(QThread):
    completed = Signal()
    error = Signal(str)
    progress_percentage = Signal(int)

    def __init__(self, instance_name: str, instance_port: int):
        super().__init__()
        self.instance_name = instance_name
        self.instance_port = instance_port

    def run(self):
        try:
            self.progress_percentage.emit(50)
            InstallManager.complete_install(self.instance_name, self.instance_port)
            self.progress_percentage.emit(100)
            self.completed.emit()
        except Exception as e:
            self.error.emit(str(e))


class UpdateOpenClawWorker(QThread):
    """Worker to update OpenClaw runtime to the latest version using InstallManager."""
    finished = Signal()
    error = Signal(str)
    progress = Signal(str)
    progress_percentage = Signal(int)

    def __init__(self, instance_name: str = ""):
        super().__init__()
        self.instance_name = instance_name

    def run(self):
        try:
            def _progress_callback(stage: str, current: int, total: int, detail: str):
                """Handle progress updates from InstallManager."""
                if stage == "overwriting":
                    self.progress.emit(i18n.t("onboard_status_installing_dep", name=i18n.t("runtime_openclaw"), version=detail or "latest"))
                    self.progress_percentage.emit(30)
                elif stage == "reinstalling":
                    self.progress.emit(i18n.t("onboard_status_installing_dep", name=i18n.t("runtime_openclaw"), version=""))
                    self.progress_percentage.emit(70)
                elif stage == "done":
                    self.progress_percentage.emit(100)

            # Use InstallManager's update function
            InstallManager.update_instance_to_default_version(
                self.instance_name,
                progress_callback=_progress_callback
            )

            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))


class OneClickWorker(QThread):
    """Performs the full one-click flow: install runtimes, create sample, start instance."""
    completed = Signal()
    error = Signal(str)
    progress = Signal(str)
    progress_percentage = Signal(int)

    def __init__(self, instance_name: str, instance_port: int):
        super().__init__()
        self.instance_name = instance_name
        self.instance_port = instance_port

    def run(self):
        try:
            manager = RuntimeManager()

            def _write_log(msg: str):
                try:
                    Config.ensure_dirs()
                    log_path = Config.get_log_file("installer")
                    with open(log_path, "a", encoding="utf-8") as log_f:
                        if msg:
                            log_f.write(f"{datetime.now().isoformat()} {msg}\n")
                            log_f.flush()
                except Exception:
                    pass

            # Step: ensure Node.js
            if self.isInterruptionRequested():
                raise RuntimeError("Interrupted")

            if not manager.get_default_version(RuntimeManager.SOFTWARE_NODE):
                node_versions = manager.get_available_versions(RuntimeManager.SOFTWARE_NODE)
                if not node_versions:
                    raise RuntimeError("No available Node.js versions")

                node_target = str(node_versions[0]["version"])
                msg = i18n.t("onboard_status_installing_dep", name=i18n.t("runtime_node"), version=node_target)
                self.progress.emit(msg)
                _write_log(msg)
                self.progress_percentage.emit(20)
                manager.install_version(RuntimeManager.SOFTWARE_NODE, node_target)
                self.progress_percentage.emit(40)
                manager.set_default_version(RuntimeManager.SOFTWARE_NODE, node_target)

            if self.isInterruptionRequested():
                raise RuntimeError("Interrupted")

            # Step: ensure OpenClaw runtime
            if not manager.get_default_version(RuntimeManager.SOFTWARE_OPENCLAW):
                msg = i18n.t("onboard_status_refresh_openclaw")
                self.progress.emit(msg)
                _write_log(msg)
                self.progress_percentage.emit(50)
                manager.refresh_available_versions(RuntimeManager.SOFTWARE_OPENCLAW)
                openclaw_versions = manager.get_available_versions(RuntimeManager.SOFTWARE_OPENCLAW)
                if not openclaw_versions:
                    raise RuntimeError("No available OpenClaw versions")

                openclaw_target = str(openclaw_versions[0]["version"])
                msg = i18n.t("onboard_status_installing_dep", name=i18n.t("runtime_openclaw"), version=openclaw_target)
                self.progress.emit(msg)
                _write_log(msg)
                self.progress_percentage.emit(70)
                manager.install_version(RuntimeManager.SOFTWARE_OPENCLAW, openclaw_target)
                self.progress_percentage.emit(85)
                manager.set_default_version(RuntimeManager.SOFTWARE_OPENCLAW, openclaw_target)

            if self.isInterruptionRequested():
                raise RuntimeError("Interrupted")

            # Create sample
            self.progress.emit(i18n.t("onboard_status_creating_sample", name=self.instance_name))
            _write_log(i18n.t("onboard_status_creating_sample", name=self.instance_name))
            self.progress_percentage.emit(90)
            InstallManager.complete_install(self.instance_name, self.instance_port)
            self.progress_percentage.emit(95)

            if self.isInterruptionRequested():
                raise RuntimeError("Interrupted")

            # Start instance
            self.progress.emit(i18n.t("onboard_status_starting_instance", name=self.instance_name))
            _write_log(i18n.t("onboard_status_starting_instance", name=self.instance_name))
            ProcessManager.start_instance(self.instance_name, Config.get_instance_path(self.instance_name))
            self.progress_percentage.emit(100)

            self.completed.emit()
        except Exception as e:
            try:
                _write_log(f"Error: {str(e)}")
            except Exception:
                pass
            self.error.emit(str(e))


class OnboardPanel(QWidget):
    dependencies_ready = Signal()
    sample_ready = Signal()
    navigate_to_tab = Signal(str)

    SAMPLE_INSTANCE_NAME = "openclaw"
    SAMPLE_INSTANCE_PORT = 18789

    def __init__(self):
        super().__init__()
        self.dep_worker = None
        self.sample_worker = None

        worker = getattr(self, "one_click_worker", None)
        if worker and worker.isRunning():
            try:
                worker.requestInterruption()
                worker.wait(1000)
                if worker.isRunning():
                    worker.terminate()
                    worker.wait(500)
            except Exception:
                pass
        self.one_click_worker = None

        # Ensure sample instance stopped on shutdown
        try:
            if self._sample_running():
                ProcessManager.stop_instance(self.SAMPLE_INSTANCE_NAME)
        except Exception:
            pass
        self.one_click_worker = None

        self.layout = QVBoxLayout(self)

        # Logo above the primary action
        self.lbl_logo = QLabel()
        self.lbl_logo.setAttribute(Qt.WA_TranslucentBackground, True)
        self.lbl_logo.setStyleSheet("background: transparent;")
        logo_path = _resolve_logo_path()
        if logo_path:
            reader = QImageReader(logo_path)
            reader.setAutoTransform(True)
            image = reader.read()
            if not image.isNull():
                logo_pixmap = QPixmap.fromImage(image)
                self.lbl_logo.setAlignment(Qt.AlignCenter)
                self.lbl_logo.setScaledContents(False)
                dpr = max(1.0, float(self.devicePixelRatioF()))
                target_width = int(180 * dpr)
                self.lbl_logo.setPixmap(
                    logo_pixmap.scaledToWidth(target_width, Qt.SmoothTransformation)
                )
        self.layout.addWidget(self.lbl_logo)

        self.layout.addStretch()

        self.lbl_title = QLabel(i18n.t("onboard_title"))
        self.lbl_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.layout.addWidget(self.lbl_title)

        # Main unified progress (used by one-click flow)
        self.progress_main = QProgressBar()
        self.progress_main.setVisible(False)
        self.progress_main.setMaximum(100)
        self.layout.addWidget(self.progress_main)

        # Hidden legacy progress bars kept for worker callbacks
        self.progress_dep = QProgressBar()
        self.progress_dep.setVisible(False)
        self.progress_dep.setMaximum(100)

        self.progress_sample = QProgressBar()
        self.progress_sample.setVisible(False)
        self.progress_sample.setMaximum(100)

        self.layout.addSpacing(8)

        self.lbl_status = QLabel(i18n.t("status_ready"))
        self.layout.addWidget(self.lbl_status)

        self.layout.addSpacing(10)

        # One-click install / start / stop button (single control for onboarding)
        self.btn_one_click = QPushButton(i18n.t("onboard_btn_install_dependencies"))
        self.btn_one_click.clicked.connect(self.one_click_action)
        self.layout.addWidget(self.btn_one_click)

        # Quick links under the start panel
        links_layout = QHBoxLayout()
        self.btn_webui_link = QPushButton(i18n.t("onboard_btn_open_webui"))
        self.btn_webui_link.clicked.connect(self.open_sample_webui)
        self.btn_cli_launcher = QPushButton(i18n.t("onboard_btn_open_cli"))
        self.btn_cli_launcher.clicked.connect(self.open_sample_cli)
        self.btn_update_version = QPushButton(i18n.t("btn_update_version"))
        self.btn_update_version.clicked.connect(self.update_openclaw_version)
        self.btn_docs = QPushButton(i18n.t("onboard_btn_open_docs"))
        self.btn_docs.clicked.connect(lambda: self.open_url("https://docs.openclaw.ai"))

        links_layout.addWidget(self.btn_webui_link)
        links_layout.addWidget(self.btn_cli_launcher)
        links_layout.addWidget(self.btn_update_version)
        links_layout.addWidget(self.btn_docs)
        self.layout.addLayout(links_layout)

        self.layout.addSpacing(10)

        # Sponsorship links
        self.lbl_support = QLabel(i18n.t("onboard_support_title"))
        self.lbl_support.setStyleSheet("font-size: 15px; font-weight: 600;")
        self.layout.addWidget(self.lbl_support)

        support_btn_layout = QHBoxLayout()
        self.btn_afdian = QPushButton(i18n.t("onboard_btn_afdian"))
        self.btn_bilibili = QPushButton(i18n.t("onboard_btn_bilibili"))
        self.btn_kofi = QPushButton(i18n.t("onboard_btn_kofi"))

        self.btn_afdian.clicked.connect(lambda: self.open_url("https://afdian.com/a/shinnpuru"))
        self.btn_bilibili.clicked.connect(lambda: self.open_url("https://space.bilibili.com/36464441"))
        self.btn_kofi.clicked.connect(lambda: self.open_url("https://ko-fi.com/U7U018MISY"))

        support_btn_layout.addWidget(self.btn_afdian)
        support_btn_layout.addWidget(self.btn_bilibili)
        support_btn_layout.addWidget(self.btn_kofi)
        self.layout.addLayout(support_btn_layout)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_status)
        self.refresh_timer.start(2000)

        self.refresh_status()

    def _dependencies_ok(self) -> bool:
        manager = RuntimeManager()
        return bool(manager.get_default_version(RuntimeManager.SOFTWARE_NODE)) and bool(
            manager.get_default_version(RuntimeManager.SOFTWARE_OPENCLAW)
        )

    def _sample_ok(self) -> bool:
        return Config.get_instance_path(self.SAMPLE_INSTANCE_NAME).exists()

    def _sample_running(self) -> bool:
        if not self._sample_ok():
            return False
        return ProcessManager.get_status(self.SAMPLE_INSTANCE_NAME) == "Running"

    def refresh_status(self):
        deps_done = self._dependencies_ok()
        sample_done = self._sample_ok()
        running_done = self._sample_running()

        if self.one_click_worker and self.one_click_worker.isRunning():
            self.btn_one_click.setEnabled(True)
            self.btn_one_click.setText(i18n.t("onboard_btn_installing") or "停止")
        elif running_done:
            self.btn_one_click.setEnabled(True)
            self.btn_one_click.setText(i18n.t("onboard_btn_stop_instance") or "停止 OpenClaw")
        elif not deps_done or not sample_done:
            self.btn_one_click.setEnabled(True)
            self.btn_one_click.setText("一键安装并启动 OpenClaw")
        else:
            self.btn_one_click.setEnabled(True)
            self.btn_one_click.setText(i18n.t("onboard_btn_start_instance") or "启动 OpenClaw")

        if self.one_click_worker and self.one_click_worker.isRunning():
            self.lbl_status.setText(i18n.t("onboard_status_creating_sample", name=self.SAMPLE_INSTANCE_NAME))
        elif running_done:
            self.lbl_status.setText(i18n.t("onboard_done"))
        elif not deps_done:
            self.lbl_status.setText("")
        elif not sample_done:
            self.lbl_status.setText(i18n.t("onboard_hint_create_sample"))
        else:
            self.lbl_status.setText(i18n.t("onboard_hint_configure_before_start"))

    def install_dependencies(self):
        if self.dep_worker and self.dep_worker.isRunning():
            return
        self.dep_worker = InstallDependenciesWorker()
        # Ensure Qt ownership and automatic safe deletion when finished
        try:
            self.dep_worker.setParent(self)
            self.dep_worker.finished.connect(self.dep_worker.deleteLater)
        except Exception:
            pass
        self.dep_worker.progress.connect(self.on_dep_progress)
        self.dep_worker.progress_percentage.connect(self.on_dep_progress_percentage)
        self.dep_worker.completed.connect(self.on_dep_finished)
        self.dep_worker.error.connect(self.on_dep_error)
        self.dep_worker.start()
        self.progress_dep.setVisible(True)
        self.progress_dep.setValue(0)
        self.refresh_status()

    def one_click_action(self):
        # 如果 worker 在运行，发出中断请求
        if self.one_click_worker and self.one_click_worker.isRunning():
            try:
                self.one_click_worker.requestInterruption()
            except Exception:
                pass
            return

        # 如果样例已经运行，停止实例
        if self._sample_running():
            try:
                ProcessManager.stop_instance(self.SAMPLE_INSTANCE_NAME)
            except Exception as e:
                QMessageBox.critical(self, i18n.t("title_error"), str(e))
            self.refresh_status()
            return

        # 依赖和样例都已就绪时，直接启动实例
        if self._dependencies_ok() and self._sample_ok():
            self.start_sample_instance()
            return

        # 启动一键流程
        if not self._dependencies_ok() or not self._sample_ok():
            self.one_click_worker = OneClickWorker(self.SAMPLE_INSTANCE_NAME, self.SAMPLE_INSTANCE_PORT)
            try:
                self.one_click_worker.setParent(self)
                self.one_click_worker.finished.connect(self.one_click_worker.deleteLater)
            except Exception:
                pass
            self.one_click_worker.progress.connect(self.on_one_click_progress)
            self.one_click_worker.progress_percentage.connect(self.on_one_click_progress_percentage)
            self.one_click_worker.completed.connect(self.on_one_click_finished)
            self.one_click_worker.error.connect(self.on_one_click_error)
            self.one_click_worker.start()
            self.progress_main.setVisible(True)
            self.progress_main.setValue(0)
            self.refresh_status()

    def on_one_click_progress(self, message: str):
        self.lbl_status.setText(message)

    def on_one_click_progress_percentage(self, percentage: int):
        self.progress_main.setValue(percentage)

    def on_one_click_finished(self):
        self.one_click_worker = None
        self.progress_main.setVisible(False)
        QMessageBox.information(self, i18n.t("title_success"), i18n.t("onboard_all_done"))
        self.refresh_status()

    def on_one_click_error(self, error: str):
        self.one_click_worker = None
        self.progress_main.setVisible(False)
        QMessageBox.critical(self, i18n.t("title_error"), i18n.t("onboard_msg_dependencies_failed", error=error))
        self.refresh_status()

    def on_dep_progress(self, message: str):
        self.lbl_status.setText(message)

    def on_dep_progress_percentage(self, percentage: int):
        self.progress_dep.setValue(percentage)

    def on_dep_finished(self):
        self.dep_worker = None
        self.progress_dep.setVisible(False)
        QMessageBox.information(self, i18n.t("title_success"), i18n.t("onboard_msg_dependencies_done"))
        self.dependencies_ready.emit()
        self.refresh_status()

    def on_dep_error(self, error: str):
        self.dep_worker = None
        self.progress_dep.setVisible(False)
        QMessageBox.critical(self, i18n.t("title_error"), i18n.t("onboard_msg_dependencies_failed", error=error))
        self.refresh_status()

    def create_sample(self):
        if not self._dependencies_ok():
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("onboard_msg_dependencies_required"))
            return

        if self.sample_worker and self.sample_worker.isRunning():
            return

        if self._sample_ok():
            self.refresh_status()
            return

        self.sample_worker = CreateSampleWorker(self.SAMPLE_INSTANCE_NAME, self.SAMPLE_INSTANCE_PORT)
        # Ensure Qt ownership and automatic safe deletion when finished
        try:
            self.sample_worker.setParent(self)
            self.sample_worker.finished.connect(self.sample_worker.deleteLater)
        except Exception:
            pass

        self.sample_worker.progress_percentage.connect(self.on_sample_progress_percentage)
        self.sample_worker.completed.connect(self.on_sample_finished)
        self.sample_worker.error.connect(self.on_sample_error)
        self.sample_worker.start()
        self.lbl_status.setText(i18n.t("onboard_status_creating_sample", name=self.SAMPLE_INSTANCE_NAME))
        self.progress_sample.setVisible(True)
        self.progress_sample.setValue(0)
        self.refresh_status()

    def on_sample_finished(self):
        self.sample_worker = None
        self.progress_sample.setVisible(False)
        QMessageBox.information(
            self,
            i18n.t("title_success"),
            i18n.t("onboard_msg_sample_done", name=self.SAMPLE_INSTANCE_NAME),
        )
        self.sample_ready.emit()
        self.refresh_status()

    def on_sample_progress_percentage(self, percentage: int):
        self.progress_sample.setValue(percentage)

    def on_sample_error(self, error: str):
        self.sample_worker = None
        self.progress_sample.setVisible(False)
        QMessageBox.critical(self, i18n.t("title_error"), i18n.t("onboard_msg_sample_failed", error=error))
        self.refresh_status()

    def start_sample_instance(self):
        if not self._sample_ok():
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("msg_instance_not_found"))
            self.refresh_status()
            return

        if self._sample_running():
            self.refresh_status()
            return

        try:
            ProcessManager.start_instance(self.SAMPLE_INSTANCE_NAME, Config.get_instance_path(self.SAMPLE_INSTANCE_NAME))
            QMessageBox.information(
                self,
                i18n.t("title_success"),
                i18n.t("onboard_msg_instance_started", name=self.SAMPLE_INSTANCE_NAME),
            )
            self.refresh_status()
        except Exception as e:
            QMessageBox.critical(
                self,
                i18n.t("title_error"),
                i18n.t("onboard_msg_instance_start_failed", error=str(e)),
            )

    def open_llamacpp_tab(self):
        self.navigate_to_tab.emit("llamacpp")

    def open_model_switch_tab(self):
        self.navigate_to_tab.emit("model_switch")

    def open_channel_config_tab(self):
        self.navigate_to_tab.emit("channels")

    def open_sample_webui(self):
        if not self._sample_ok():
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("msg_instance_not_found"))
            self.refresh_status()
            return

        instance_path = Config.get_instance_path(self.SAMPLE_INSTANCE_NAME)
        port = InstallManager.get_instance_port(instance_path)
        gateway_token = InstallManager.get_instance_gateway_token(instance_path, self.SAMPLE_INSTANCE_NAME)
        url = QUrl(f"http://127.0.0.1:{port}/#token={gateway_token}")
        QDesktopServices.openUrl(url)
        self.lbl_status.setText(i18n.t("onboard_msg_webui_opened", url=url.toString()))

    def open_sample_cli(self):
        if not self._sample_ok():
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("msg_instance_not_found"))
            self.refresh_status()
            return

        try:
            instance_path = Config.get_instance_path(self.SAMPLE_INSTANCE_NAME)
            ProcessManager.launch_instance_cli(self.SAMPLE_INSTANCE_NAME, instance_path)
            self.lbl_status.setText(i18n.t("onboard_msg_cli_opened", name=self.SAMPLE_INSTANCE_NAME))
        except Exception as e:
            QMessageBox.critical(self, i18n.t("title_error"), i18n.t("onboard_msg_cli_open_failed", error=str(e)))

    def open_url(self, url: str):
        QDesktopServices.openUrl(QUrl(url))

    def update_openclaw_version(self):
        """Update OpenClaw runtime to the latest version."""
        # If sample instance is running, warn user
        if self._sample_running():
            ret = QMessageBox.warning(
                self,
                i18n.t("title_warning"),
                i18n.t("msg_update_requires_stop", name=self.SAMPLE_INSTANCE_NAME),
                QMessageBox.Yes | QMessageBox.No,
            )
            if ret != QMessageBox.Yes:
                return
            try:
                ProcessManager.stop_instance(self.SAMPLE_INSTANCE_NAME)
            except Exception as e:
                QMessageBox.critical(self, i18n.t("title_error"), str(e))
                return

        # Check dependencies exist
        if not self._dependencies_ok():
            QMessageBox.warning(
                self,
                i18n.t("title_warning"),
                i18n.t("onboard_msg_dependencies_required"),
            )
            return

        # Confirm update
        res = QMessageBox.question(
            self,
            i18n.t("title_confirm_update"),
            i18n.t("msg_confirm_update_version", name="OpenClaw"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if res != QMessageBox.Yes:
            return

        # Start update worker
        self.update_worker = UpdateOpenClawWorker(self.SAMPLE_INSTANCE_NAME)
        try:
            self.update_worker.setParent(self)
            self.update_worker.finished.connect(self.update_worker.deleteLater)
        except Exception:
            pass

        self.update_worker.progress.connect(self.on_update_progress)
        self.update_worker.progress_percentage.connect(self.on_update_progress_percentage)
        self.update_worker.finished.connect(self.on_update_finished)
        self.update_worker.error.connect(self.on_update_error)

        self.progress_main.setVisible(True)
        self.progress_main.setValue(0)
        self.btn_update_version.setEnabled(False)
        self.update_worker.start()

    def on_update_progress(self, message: str):
        self.lbl_status.setText(message)

    def on_update_progress_percentage(self, percentage: int):
        self.progress_main.setValue(percentage)

    def on_update_finished(self):
        self.update_worker = None
        self.progress_main.setVisible(False)
        self.btn_update_version.setEnabled(True)
        QMessageBox.information(
            self,
            i18n.t("title_success"),
            i18n.t("msg_update_success", name="OpenClaw", new_name="OpenClaw"),
        )
        self.refresh_status()

    def on_update_error(self, error: str):
        self.update_worker = None
        self.progress_main.setVisible(False)
        self.btn_update_version.setEnabled(True)
        QMessageBox.critical(
            self,
            i18n.t("title_error"),
            i18n.t("msg_update_error", name="OpenClaw", error=error),
        )
        self.refresh_status()

    def update_ui_texts(self):
        self.lbl_title.setText(i18n.t("onboard_title"))
        self.btn_webui_link.setText(i18n.t("onboard_btn_open_webui"))
        self.btn_cli_launcher.setText(i18n.t("onboard_btn_open_cli"))
        self.btn_update_version.setText(i18n.t("btn_update_version"))
        self.btn_docs.setText(i18n.t("onboard_btn_open_docs"))
        self.btn_one_click.setText(self.btn_one_click.text())
        self.refresh_status()

    def shutdown(self):
        if hasattr(self, "refresh_timer") and self.refresh_timer:
            self.refresh_timer.stop()

        worker = self.dep_worker
        if worker and worker.isRunning():
            worker.requestInterruption()
            worker.wait(1000)
            if worker.isRunning():
                worker.terminate()
                worker.wait(500)
        self.dep_worker = None

        worker = self.sample_worker
        if worker and worker.isRunning():
            worker.requestInterruption()
            worker.wait(1000)
            if worker.isRunning():
                worker.terminate()
                worker.wait(500)
        self.sample_worker = None

        worker = getattr(self, "update_worker", None)
        if worker and worker.isRunning():
            worker.requestInterruption()
            worker.wait(1000)
            if worker.isRunning():
                worker.terminate()
                worker.wait(500)
        self.update_worker = None

