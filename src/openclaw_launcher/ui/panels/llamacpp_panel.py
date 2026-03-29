from pathlib import Path
import os
import subprocess
import sys
from typing import Optional

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...core.config import Config
from ..i18n import i18n


class LlamaCppProcessWorker(QThread):
    """Worker thread for running llama.cpp server process."""

    output_ready = Signal(str)
    process_started = Signal()
    process_stopped = Signal()
    error_occurred = Signal(str)

    def __init__(
        self,
        model_path: str,
        mmproj_path: str = "",
        port: int = 8989,
        n_gpu_layers: int = 100,
        extra_params: str = "",
    ):
        super().__init__()
        self.model_path = model_path
        self.mmproj_path = mmproj_path
        self.port = port
        self.n_gpu_layers = n_gpu_layers
        self.extra_params = extra_params
        self.process = None
        self._running = False

    def run(self):
        try:
            llama_exe = self._find_llama_server()
            if not llama_exe:
                self.error_occurred.emit(i18n.t("llamacpp_server_not_found"))
                return

            cmd = [
                str(llama_exe),
                "-m",
                self.model_path,
                "--port",
                str(self.port),
                "-ngl",
                str(self.n_gpu_layers),
            ]

            mmproj_path = self.mmproj_path.strip()
            if mmproj_path:
                cmd.extend(["--mmproj", mmproj_path])

            if self.extra_params.strip():
                cmd.extend(self.extra_params.strip().split())

            self._running = True
            self.process_started.emit()

            if sys.platform == "win32":
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    universal_newlines=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            else:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    universal_newlines=True,
                )

            for line in iter(self.process.stdout.readline, ""):
                if not self._running:
                    break
                if line:
                    self.output_ready.emit(line.strip())

            self.process.stdout.close()
            self.process.wait()

        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self._running = False
            self.process_stopped.emit()

    def stop(self):
        self._running = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                try:
                    self.process.kill()
                    self.process.wait(timeout=2)
                except Exception:
                    pass
            self.process = None

    def _find_llama_server(self) -> Optional[Path]:
        """Find llama-server executable in common locations."""
        possible_names = ["llama-server", "llama-server.exe"]

        llama_dir = Path.cwd() / "llama"
        for name in possible_names:
            exe_path = llama_dir / name
            if exe_path.exists():
                return exe_path

        import shutil

        for name in possible_names:
            exe_path = shutil.which(name)
            if exe_path:
                return Path(exe_path)

        return None


class LlamaCppTab(QWidget):
    """Llama.cpp local server tab."""

    def __init__(self, parent_panel):
        super().__init__()
        self.parent_panel = parent_panel
        self.worker = None
        self._is_running = False
        self.init_ui()
        self.load_config()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        self.config_group = QGroupBox(i18n.t("llamacpp_model_group"))
        config_layout = QVBoxLayout(self.config_group)

        model_file_layout = QHBoxLayout()
        self.model_file_label = QLabel(i18n.t("llamacpp_model_file"))
        model_file_layout.addWidget(self.model_file_label)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.refresh_model_list()
        model_file_layout.addWidget(self.model_combo)

        self.browse_model_btn = QPushButton(i18n.t("btn_browse"))
        self.browse_model_btn.clicked.connect(self.browse_model_file)
        model_file_layout.addWidget(self.browse_model_btn)

        config_layout.addLayout(model_file_layout)

        mmproj_file_layout = QHBoxLayout()
        self.mmproj_file_label = QLabel(i18n.t("llamacpp_mmproj_file"))
        mmproj_file_layout.addWidget(self.mmproj_file_label)

        self.mmproj_combo = QComboBox()
        self.mmproj_combo.setEditable(True)
        mmproj_file_layout.addWidget(self.mmproj_combo)

        self.browse_mmproj_btn = QPushButton(i18n.t("btn_browse"))
        self.browse_mmproj_btn.clicked.connect(self.browse_mmproj_file)
        mmproj_file_layout.addWidget(self.browse_mmproj_btn)

        config_layout.addLayout(mmproj_file_layout)
        self.refresh_model_list()

        model_actions_layout = QHBoxLayout()
        self.refresh_models_btn = QPushButton(i18n.t("btn_refresh"))
        self.refresh_models_btn.clicked.connect(self.refresh_model_list)
        model_actions_layout.addWidget(self.refresh_models_btn)

        self.open_model_dir_btn = QPushButton(i18n.t("llamacpp_open_model_dir"))
        self.open_model_dir_btn.clicked.connect(self.open_model_directory)
        model_actions_layout.addWidget(self.open_model_dir_btn)
        config_layout.addLayout(model_actions_layout)

        port_layout = QHBoxLayout()
        self.port_label = QLabel(i18n.t("llamacpp_port"))
        port_layout.addWidget(self.port_label)

        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(8989)
        port_layout.addWidget(self.port_spin)
        port_layout.addStretch()

        config_layout.addLayout(port_layout)

        gpu_layout = QHBoxLayout()
        self.gpu_label = QLabel(i18n.t("llamacpp_gpu_layers"))
        gpu_layout.addWidget(self.gpu_label)

        self.gpu_layers_spin = QSpinBox()
        self.gpu_layers_spin.setRange(0, 1000)
        self.gpu_layers_spin.setValue(100)
        self.gpu_layers_spin.setSpecialValueText(i18n.t("llamacpp_cpu_only"))
        gpu_layout.addWidget(self.gpu_layers_spin)
        gpu_layout.addStretch()

        config_layout.addLayout(gpu_layout)

        api_layout = QHBoxLayout()
        self.api_label = QLabel(i18n.t("llamacpp_api_address"))
        api_layout.addWidget(self.api_label)

        self.api_address_display = QLineEdit()
        self.api_address_display.setReadOnly(True)
        self.api_address_display.setText(i18n.t("llamacpp_default_api_url", port=8989))
        self.port_spin.valueChanged.connect(self.update_api_address)
        api_layout.addWidget(self.api_address_display)

        config_layout.addLayout(api_layout)

        self.params_label = QLabel(i18n.t("llamacpp_extra_params_desc"))
        self.params_label.setStyleSheet("color: gray;")
        config_layout.addWidget(self.params_label)

        self.extra_params = QTextEdit()
        self.extra_params.setPlaceholderText(i18n.t("llamacpp_extra_params_placeholder"))
        self.extra_params.setMaximumHeight(80)
        config_layout.addWidget(self.extra_params)

        layout.addWidget(self.config_group)

        self.runtime_group = QGroupBox(i18n.t("llamacpp_runtime_group"))
        runtime_layout = QVBoxLayout(self.runtime_group)

        control_layout = QHBoxLayout()

        self.start_btn = QPushButton(i18n.t("llamacpp_start_server"))
        self.start_btn.clicked.connect(self.start_server)
        control_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton(i18n.t("llamacpp_stop_server"))
        self.stop_btn.clicked.connect(self.stop_server)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)

        control_layout.addStretch()

        runtime_layout.addLayout(control_layout)

        status_layout = QHBoxLayout()
        self.status_label = QLabel(i18n.t("llamacpp_status"))
        status_layout.addWidget(self.status_label)

        self.status_display = QLabel(i18n.t("llamacpp_status_stopped"))
        self.status_display.setStyleSheet("color: red; font-weight: bold;")
        status_layout.addWidget(self.status_display)
        status_layout.addStretch()

        runtime_layout.addLayout(status_layout)

        self.output_label = QLabel(i18n.t("llamacpp_output_log"))
        runtime_layout.addWidget(self.output_label)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setPlaceholderText(i18n.t("llamacpp_output_placeholder"))
        self.output_text.setMaximumHeight(150)
        runtime_layout.addWidget(self.output_text)

        layout.addWidget(self.runtime_group)

        layout.addStretch()

    def refresh_model_list(self):
        """Refresh the list of available .gguf models."""
        current_model = self.model_combo.currentText().strip()
        current_mmproj = self.mmproj_combo.currentText().strip() if hasattr(self, "mmproj_combo") else ""

        self.model_combo.clear()
        if hasattr(self, "mmproj_combo"):
            self.mmproj_combo.clear()
            self.mmproj_combo.addItem("")

        llama_dir = Path.cwd() / "llama"
        models = []

        if llama_dir.exists():
            for file in llama_dir.iterdir():
                if file.is_file() and file.suffix == ".gguf":
                    models.append(file.name)

        if models:
            self.model_combo.addItems(models)
            if hasattr(self, "mmproj_combo"):
                self.mmproj_combo.addItems(models)
        else:
            self.model_combo.addItem(i18n.t("llamacpp_no_models_found"))

        if current_model:
            self.model_combo.setCurrentText(current_model)
        if hasattr(self, "mmproj_combo") and current_mmproj:
            self.mmproj_combo.setCurrentText(current_mmproj)

    def browse_model_file(self):
        """Open file dialog to select a .gguf model file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            i18n.t("llamacpp_select_model"),
            str(Path.cwd() / "llama"),
            i18n.t("llamacpp_model_file_filter"),
        )
        if file_path:
            self.model_combo.setCurrentText(file_path)

    def browse_mmproj_file(self):
        """Open file dialog to select a .gguf mmproj file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            i18n.t("llamacpp_select_mmproj"),
            str(Path.cwd() / "llama"),
            i18n.t("llamacpp_model_file_filter"),
        )
        if file_path:
            self.mmproj_combo.setCurrentText(file_path)

    def _resolve_gguf_path(self, file_text: str) -> Optional[Path]:
        file_text = (file_text or "").strip()
        if not file_text:
            return None

        llama_dir = Path.cwd() / "llama"
        if Path(file_text).is_absolute():
            return Path(file_text)
        return llama_dir / file_text

    def open_model_directory(self):
        """Open the llama models directory."""
        llama_dir = Path.cwd() / "llama"
        llama_dir.mkdir(parents=True, exist_ok=True)

        import platform

        if platform.system() == "Windows":
            os.startfile(str(llama_dir))
        elif platform.system() == "Darwin":
            os.system(f'open "{llama_dir}"')
        else:
            os.system(f'xdg-open "{llama_dir}"')

    def update_api_address(self):
        """Update the displayed API address when port changes."""
        port = self.port_spin.value()
        self.api_address_display.setText(i18n.t("llamacpp_default_api_url", port=port))

    def start_server(self):
        """Start the llama.cpp server."""
        if self._is_running:
            return

        model_path = self.model_combo.currentText()
        if not model_path or model_path == i18n.t("llamacpp_no_models_found"):
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("llamacpp_no_model_selected"))
            return

        model_full_path = self._resolve_gguf_path(model_path)
        if not model_full_path:
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("llamacpp_no_model_selected"))
            return

        if not model_full_path.exists():
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("llamacpp_model_not_found"))
            return

        mmproj_path = self.mmproj_combo.currentText()
        mmproj_full_path = self._resolve_gguf_path(mmproj_path)
        if mmproj_full_path and not mmproj_full_path.exists():
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("llamacpp_mmproj_not_found"))
            return

        port = self.port_spin.value()
        gpu_layers = self.gpu_layers_spin.value()
        extra_params = self.extra_params.toPlainText()

        self.output_text.clear()
        self.output_text.append(i18n.t("llamacpp_starting_server", model=model_path))

        self.worker = LlamaCppProcessWorker(
            model_path=str(model_full_path),
            mmproj_path=str(mmproj_full_path) if mmproj_full_path else "",
            port=port,
            n_gpu_layers=gpu_layers,
            extra_params=extra_params,
        )
        self.worker.output_ready.connect(self.on_output)
        self.worker.process_started.connect(self.on_process_started)
        self.worker.process_stopped.connect(self.on_process_stopped)
        self.worker.error_occurred.connect(self.on_process_error)
        self.worker.start()

    def stop_server(self):
        """Stop the llama.cpp server."""
        if self.worker:
            self.output_text.append(i18n.t("llamacpp_stopping_server"))
            self.worker.stop()

    def test_api(self):
        """Test if the llama.cpp API is accessible."""
        import json
        import urllib.request

        port = self.port_spin.value()
        url = f"http://127.0.0.1:{port}/v1/models"

        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read().decode())
                models = data.get("data", [])
                if models:
                    model_info = []
                    for m in models:
                        model_info.append(f"  - {m.get('id', 'unknown')}")
                    QMessageBox.information(
                        self,
                        i18n.t("title_success"),
                        i18n.t("llamacpp_api_test_success", models="\n".join(model_info)),
                    )
                else:
                    QMessageBox.information(
                        self,
                        i18n.t("title_success"),
                        i18n.t("llamacpp_api_test_no_models"),
                    )
        except Exception as e:
            QMessageBox.warning(
                self,
                i18n.t("title_warning"),
                i18n.t("llamacpp_api_test_failed", error=str(e)),
            )

    def on_output(self, text):
        """Handle output from the server process."""
        self.output_text.append(text)
        scrollbar = self.output_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def on_process_started(self):
        """Handle server process started."""
        self._is_running = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_display.setText(i18n.t("llamacpp_status_running"))
        self.status_display.setStyleSheet("color: green; font-weight: bold;")
        self.save_config()

    def on_process_stopped(self):
        """Handle server process stopped."""
        self._is_running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_display.setText(i18n.t("llamacpp_status_stopped"))
        self.status_display.setStyleSheet("color: red; font-weight: bold;")
        self.worker = None

    def on_process_error(self, error):
        """Handle server process error."""
        self.output_text.append(f"[ERROR] {error}")
        QMessageBox.critical(self, i18n.t("title_error"), i18n.t("llamacpp_server_error", error=error))

    def save_config(self):
        """Save current configuration."""
        config = {
            "model": self.model_combo.currentText(),
            "mmproj_model": self.mmproj_combo.currentText(),
            "port": self.port_spin.value(),
            "gpu_layers": self.gpu_layers_spin.value(),
            "extra_params": self.extra_params.toPlainText(),
        }
        Config.set_setting("llamacpp_config", config)

    def load_config(self):
        """Load saved configuration."""
        config = Config.get_setting("llamacpp_config", {})
        if isinstance(config, dict):
            model = config.get("model", "")
            if model:
                index = self.model_combo.findText(model)
                if index >= 0:
                    self.model_combo.setCurrentIndex(index)
                else:
                    self.model_combo.setCurrentText(model)

            mmproj_model = config.get("mmproj_model", "")
            if mmproj_model:
                index = self.mmproj_combo.findText(mmproj_model)
                if index >= 0:
                    self.mmproj_combo.setCurrentIndex(index)
                else:
                    self.mmproj_combo.setCurrentText(mmproj_model)

            port = config.get("port", 8989)
            self.port_spin.setValue(port)

            gpu_layers = config.get("gpu_layers", 100)
            self.gpu_layers_spin.setValue(gpu_layers)

            extra_params = config.get("extra_params", "")
            self.extra_params.setPlainText(extra_params)

    def shutdown(self):
        """Shutdown the tab and stop any running processes."""
        if self.worker:
            self.worker.stop()
            self.worker.wait(3000)
            self.worker = None
        self._is_running = False

    def update_ui_texts(self):
        """Update UI texts when language changes."""
        self.config_group.setTitle(i18n.t("llamacpp_model_group"))
        self.runtime_group.setTitle(i18n.t("llamacpp_runtime_group"))
        self.model_file_label.setText(i18n.t("llamacpp_model_file"))
        self.mmproj_file_label.setText(i18n.t("llamacpp_mmproj_file"))
        self.refresh_models_btn.setText(i18n.t("btn_refresh"))
        self.browse_model_btn.setText(i18n.t("btn_browse"))
        self.browse_mmproj_btn.setText(i18n.t("btn_browse"))
        self.open_model_dir_btn.setText(i18n.t("llamacpp_open_model_dir"))

        self.port_label.setText(i18n.t("llamacpp_port"))
        self.gpu_label.setText(i18n.t("llamacpp_gpu_layers"))
        self.gpu_layers_spin.setSpecialValueText(i18n.t("llamacpp_cpu_only"))
        self.api_label.setText(i18n.t("llamacpp_api_address"))
        self.update_api_address()

        self.params_label.setText(i18n.t("llamacpp_extra_params_desc"))
        self.extra_params.setPlaceholderText(i18n.t("llamacpp_extra_params_placeholder"))

        self.start_btn.setText(i18n.t("llamacpp_start_server"))
        self.stop_btn.setText(i18n.t("llamacpp_stop_server"))
        self.status_label.setText(i18n.t("llamacpp_status"))
        self.output_label.setText(i18n.t("llamacpp_output_log"))
        self.output_text.setPlaceholderText(i18n.t("llamacpp_output_placeholder"))

        if self._is_running:
            self.status_display.setText(i18n.t("llamacpp_status_running"))
        else:
            self.status_display.setText(i18n.t("llamacpp_status_stopped"))

        self.refresh_model_list()
