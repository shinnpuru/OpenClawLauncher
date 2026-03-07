from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QMessageBox,
    QProgressBar,
)
from PySide6.QtCore import QThread, Signal, QTimer
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl

from ...core.config import Config
from ...core.install_manager import InstallManager
from ...core.process_manager import ProcessManager
from ...core.runtime_manager import RuntimeManager
from ..i18n import i18n


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

            # Node.js runtime
            if not manager.get_default_version(RuntimeManager.SOFTWARE_NODE):
                node_versions = manager.get_available_versions(RuntimeManager.SOFTWARE_NODE)
                if not node_versions:
                    raise RuntimeError("No available Node.js versions")

                node_target = str(node_versions[0]["version"])
                self.progress.emit(i18n.t("onboard_status_installing_dep", name=i18n.t("runtime_node"), version=node_target))
                self.progress_percentage.emit(25)
                manager.install_version(RuntimeManager.SOFTWARE_NODE, node_target)
                self.progress_percentage.emit(50)
                manager.set_default_version(RuntimeManager.SOFTWARE_NODE, node_target)

            # OpenClaw runtime
            if not manager.get_default_version(RuntimeManager.SOFTWARE_OPENCLAW):
                self.progress.emit(i18n.t("onboard_status_refresh_openclaw"))
                self.progress_percentage.emit(60)
                manager.refresh_available_versions(RuntimeManager.SOFTWARE_OPENCLAW)
                openclaw_versions = manager.get_available_versions(RuntimeManager.SOFTWARE_OPENCLAW)
                if not openclaw_versions:
                    raise RuntimeError("No available OpenClaw versions")

                openclaw_target = str(openclaw_versions[0]["version"])
                self.progress.emit(i18n.t("onboard_status_installing_dep", name=i18n.t("runtime_openclaw"), version=openclaw_target))
                self.progress_percentage.emit(80)
                manager.install_version(RuntimeManager.SOFTWARE_OPENCLAW, openclaw_target)
                self.progress_percentage.emit(95)
                manager.set_default_version(RuntimeManager.SOFTWARE_OPENCLAW, openclaw_target)

            self.progress_percentage.emit(100)
            self.completed.emit()
        except Exception as e:
            self.error.emit(str(e))


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


class OnboardPanel(QWidget):
    dependencies_ready = Signal()
    sample_ready = Signal()

    SAMPLE_INSTANCE_NAME = "openclaw"
    SAMPLE_INSTANCE_PORT = 18789

    def __init__(self):
        super().__init__()
        self.dep_worker = None
        self.sample_worker = None

        self.layout = QVBoxLayout(self)

        self.lbl_title = QLabel(i18n.t("onboard_title"))
        self.lbl_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.layout.addWidget(self.lbl_title)

        self.lbl_desc = QLabel(i18n.t("onboard_desc"))
        self.lbl_desc.setWordWrap(True)
        self.layout.addWidget(self.lbl_desc)

        # Wiki / docs (top)
        self.btn_wiki = QPushButton(i18n.t("onboard_btn_wiki"))
        self.btn_wiki.clicked.connect(lambda: self.open_url("https://github.com/shinnpuru/OpenClawLauncher"))
        self.layout.addWidget(self.btn_wiki)

        self.layout.addSpacing(12)

        # Step 1: dependencies
        self.step_dep_widget = QWidget()
        self.step_dep_widget.setStyleSheet("border: 1px solid #d9d9d9; border-radius: 8px;")
        dep_layout = QHBoxLayout(self.step_dep_widget)
        dep_layout.setContentsMargins(10, 8, 10, 8)
        self.lbl_step_dep = QLabel(i18n.t("onboard_step_dependencies"))
        dep_layout.addWidget(self.lbl_step_dep)
        dep_layout.addStretch()
        self.lbl_dep_status = QLabel("")
        dep_layout.addWidget(self.lbl_dep_status)
        self.btn_install_deps = QPushButton(i18n.t("onboard_btn_install_dependencies"))
        self.btn_install_deps.clicked.connect(self.install_dependencies)
        dep_layout.addWidget(self.btn_install_deps)
        self.layout.addWidget(self.step_dep_widget)

        # Step 1 Progress Bar
        self.progress_dep = QProgressBar()
        self.progress_dep.setVisible(False)
        self.progress_dep.setMaximum(100)
        self.layout.addWidget(self.progress_dep)

        # Step 2: sample instance
        self.step_sample_widget = QWidget()
        self.step_sample_widget.setStyleSheet("border: 1px solid #d9d9d9; border-radius: 8px;")
        sample_layout = QHBoxLayout(self.step_sample_widget)
        sample_layout.setContentsMargins(10, 8, 10, 8)
        self.lbl_step_sample = QLabel(i18n.t("onboard_step_sample"))
        sample_layout.addWidget(self.lbl_step_sample)
        sample_layout.addStretch()
        self.lbl_sample_status = QLabel("")
        sample_layout.addWidget(self.lbl_sample_status)
        self.btn_create_sample = QPushButton(i18n.t("onboard_btn_create_sample"))
        self.btn_create_sample.clicked.connect(self.create_sample)
        sample_layout.addWidget(self.btn_create_sample)
        self.layout.addWidget(self.step_sample_widget)

        # Step 2 Progress Bar
        self.progress_sample = QProgressBar()
        self.progress_sample.setVisible(False)
        self.progress_sample.setMaximum(100)
        self.layout.addWidget(self.progress_sample)

        # Step 3: start sample instance
        self.step_start_widget = QWidget()
        self.step_start_widget.setStyleSheet("border: 1px solid #d9d9d9; border-radius: 8px;")
        start_layout = QHBoxLayout(self.step_start_widget)
        start_layout.setContentsMargins(10, 8, 10, 8)
        self.lbl_step_start = QLabel(i18n.t("onboard_step_start_instance"))
        start_layout.addWidget(self.lbl_step_start)
        start_layout.addStretch()
        self.lbl_start_status = QLabel("")
        start_layout.addWidget(self.lbl_start_status)
        self.btn_start_sample = QPushButton(i18n.t("onboard_btn_start_instance"))
        self.btn_start_sample.clicked.connect(self.start_sample_instance)
        start_layout.addWidget(self.btn_start_sample)
        self.layout.addWidget(self.step_start_widget)

        # Step 4: open WebUI
        self.step_webui_widget = QWidget()
        self.step_webui_widget.setStyleSheet("border: 1px solid #d9d9d9; border-radius: 8px;")
        webui_layout = QHBoxLayout(self.step_webui_widget)
        webui_layout.setContentsMargins(10, 8, 10, 8)
        self.lbl_step_webui = QLabel(i18n.t("onboard_step_open_webui"))
        self.lbl_step_webui.setStyleSheet("font-size: 15px; font-weight: 600;")
        webui_layout.addWidget(self.lbl_step_webui)
        webui_layout.addStretch()
        self.btn_open_webui = QPushButton(i18n.t("onboard_btn_open_webui"))
        self.btn_open_webui.clicked.connect(self.open_sample_webui)
        webui_layout.addWidget(self.btn_open_webui)
        self.layout.addWidget(self.step_webui_widget)

        self.layout.addSpacing(8)

        self.lbl_status = QLabel(i18n.t("status_ready"))
        self.layout.addWidget(self.lbl_status)

        self.layout.addStretch()

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

    def _apply_step_style(self, title_label: QLabel, status_label: QLabel, completed: bool):
        if completed:
            title_label.setStyleSheet("color: gray; font-size: 15px; font-weight: 600;")
            status_label.setStyleSheet("color: gray; font-size: 14px;")
        else:
            title_label.setStyleSheet("font-size: 15px; font-weight: 600;")
            status_label.setStyleSheet("font-size: 14px;")

    def refresh_status(self):
        deps_done = self._dependencies_ok()
        sample_done = self._sample_ok()
        running_done = self._sample_running()
        dep_task_running = bool(self.dep_worker and self.dep_worker.isRunning())
        sample_task_running = bool(self.sample_worker and self.sample_worker.isRunning())

        self.lbl_dep_status.setText(
            i18n.t("onboard_btn_installing")
            if dep_task_running
            else (i18n.t("onboard_step_done") if deps_done else i18n.t("onboard_step_pending"))
        )
        self.lbl_sample_status.setText(
            i18n.t("onboard_btn_creating")
            if sample_task_running
            else (i18n.t("onboard_step_done") if sample_done else i18n.t("onboard_step_pending"))
        )
        self.lbl_start_status.setText(i18n.t("onboard_step_done") if running_done else i18n.t("onboard_step_pending"))

        self._apply_step_style(self.lbl_step_dep, self.lbl_dep_status, deps_done)
        self._apply_step_style(self.lbl_step_sample, self.lbl_sample_status, sample_done)
        self._apply_step_style(self.lbl_step_start, self.lbl_start_status, running_done)

        if self.dep_worker and self.dep_worker.isRunning():
            self.btn_install_deps.setEnabled(False)
            self.btn_install_deps.setText(i18n.t("onboard_btn_installing"))
        else:
            self.btn_install_deps.setEnabled(not deps_done)
            self.btn_install_deps.setText(i18n.t("onboard_btn_install_dependencies") if not deps_done else i18n.t("onboard_done"))

        if self.sample_worker and self.sample_worker.isRunning():
            self.btn_create_sample.setEnabled(False)
            self.btn_create_sample.setText(i18n.t("onboard_btn_creating"))
        else:
            self.btn_create_sample.setEnabled((not sample_done) and deps_done)
            self.btn_create_sample.setText(i18n.t("onboard_btn_create_sample") if not sample_done else i18n.t("onboard_done"))

        self.btn_start_sample.setEnabled(sample_done and (not running_done))
        self.btn_start_sample.setText(i18n.t("onboard_btn_start_instance") if not running_done else i18n.t("onboard_done"))

        self.btn_open_webui.setEnabled(running_done)

        if dep_task_running:
            # 依赖安装期间可能会有更细粒度进度文案，通过 on_dep_progress 更新，这里不覆盖。
            pass
        elif sample_task_running:
            self.lbl_status.setText(i18n.t("onboard_status_creating_sample", name=self.SAMPLE_INSTANCE_NAME))
        elif deps_done and sample_done and running_done:
            self.lbl_status.setText(i18n.t("onboard_all_done"))
        elif not deps_done:
            self.lbl_status.setText(i18n.t("onboard_hint_install_dependencies"))
        elif not sample_done:
            self.lbl_status.setText(i18n.t("onboard_hint_create_sample"))
        else:
            self.lbl_status.setText(i18n.t("onboard_hint_start_instance"))

    def install_dependencies(self):
        if self.dep_worker and self.dep_worker.isRunning():
            return

        self.dep_worker = InstallDependenciesWorker()
        self.dep_worker.progress.connect(self.on_dep_progress)
        self.dep_worker.progress_percentage.connect(self.on_dep_progress_percentage)
        self.dep_worker.completed.connect(self.on_dep_finished)
        self.dep_worker.error.connect(self.on_dep_error)
        self.dep_worker.start()
        self.progress_dep.setVisible(True)
        self.progress_dep.setValue(0)
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

    def open_sample_webui(self):
        if not self._sample_ok():
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("msg_instance_not_found"))
            self.refresh_status()
            return

        instance_path = Config.get_instance_path(self.SAMPLE_INSTANCE_NAME)
        port = InstallManager.get_instance_port(instance_path)
        gateway_token = InstallManager.get_instance_gateway_token(instance_path, self.SAMPLE_INSTANCE_NAME)
        url = QUrl(f"http://localhost:{port}/?token={gateway_token}")
        QDesktopServices.openUrl(url)
        self.lbl_status.setText(i18n.t("onboard_msg_webui_opened", url=url.toString()))

    def open_url(self, url: str):
        QDesktopServices.openUrl(QUrl(url))

    def update_ui_texts(self):
        self.lbl_title.setText(i18n.t("onboard_title"))
        self.lbl_desc.setText(i18n.t("onboard_desc"))
        self.lbl_step_dep.setText(i18n.t("onboard_step_dependencies"))
        self.lbl_step_sample.setText(i18n.t("onboard_step_sample"))
        self.lbl_step_start.setText(i18n.t("onboard_step_start_instance"))
        self.lbl_step_webui.setText(i18n.t("onboard_step_open_webui"))
        self.btn_open_webui.setText(i18n.t("onboard_btn_open_webui"))
        self.btn_wiki.setText(i18n.t("onboard_btn_wiki"))
        self.lbl_support.setText(i18n.t("onboard_support_title"))
        self.btn_afdian.setText(i18n.t("onboard_btn_afdian"))
        self.btn_bilibili.setText(i18n.t("onboard_btn_bilibili"))
        self.btn_kofi.setText(i18n.t("onboard_btn_kofi"))
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

