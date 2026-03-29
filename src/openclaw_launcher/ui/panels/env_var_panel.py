from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.config import Config
from ...core.install_manager import InstallManager
from ..i18n import i18n


class EnvVarPanel(QWidget):
    def __init__(self):
        super().__init__()

        self.layout = QVBoxLayout(self)

        instance_row = QHBoxLayout()
        self.instance_label = QLabel(i18n.t("lbl_select_instance"))
        instance_row.addWidget(self.instance_label)

        self.instance_selector = QComboBox()
        self.instance_selector.currentIndexChanged.connect(self.refresh)
        instance_row.addWidget(self.instance_selector)

        self.btn_refresh = QPushButton(i18n.t("btn_refresh"))
        self.btn_refresh.clicked.connect(self.refresh)
        instance_row.addWidget(self.btn_refresh)
        self.layout.addLayout(instance_row)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels([
            i18n.t("env_var_col_key"),
            i18n.t("env_var_col_value"),
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        self.btn_add = QPushButton(i18n.t("btn_add"))
        self.btn_add.clicked.connect(self.add_env_var)
        btn_row.addWidget(self.btn_add)

        self.btn_edit = QPushButton(i18n.t("btn_edit"))
        self.btn_edit.clicked.connect(self.edit_env_var)
        btn_row.addWidget(self.btn_edit)

        self.btn_delete = QPushButton(i18n.t("btn_delete"))
        self.btn_delete.clicked.connect(self.delete_env_var)
        btn_row.addWidget(self.btn_delete)

        btn_row.addStretch()
        self.layout.addLayout(btn_row)

        self.status_label = QLabel(i18n.t("status_ready"))
        self.layout.addWidget(self.status_label)

        self.layout.addStretch()

        self._load_instances()
        self.refresh()

    def _load_instances(self, selected_name: str | None = None):
        self.instance_selector.blockSignals(True)
        self.instance_selector.clear()
        self.instance_selector.addItem(i18n.t("opt_select_instance"), "")

        if Config.INSTANCES_DIR.exists():
            for item in sorted(Config.INSTANCES_DIR.iterdir(), key=lambda p: p.name.lower()):
                if item.is_dir():
                    self.instance_selector.addItem(item.name, item.name)

        if selected_name:
            idx = self.instance_selector.findData(selected_name)
            if idx >= 0:
                self.instance_selector.setCurrentIndex(idx)

        self.instance_selector.blockSignals(False)

    def _get_selected_instance_path(self):
        instance_name = self.instance_selector.currentData()
        if not instance_name:
            return None
        return Config.get_instance_path(instance_name)

    def _update_controls_state(self):
        enabled = bool(self.instance_selector.currentData())
        self.table.setEnabled(enabled)
        self.btn_add.setEnabled(enabled)
        self.btn_edit.setEnabled(enabled)
        self.btn_delete.setEnabled(enabled)

    def _reload_table(self):
        self.table.setRowCount(0)
        instance_path = self._get_selected_instance_path()
        if not instance_path:
            self.status_label.setText(i18n.t("msg_select_instance_required"))
            return

        entries = InstallManager.get_instance_env_entries(instance_path)
        for key in sorted(entries.keys()):
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(key))
            self.table.setItem(row, 1, QTableWidgetItem(str(entries.get(key, ""))))

        self.status_label.setText(i18n.t("status_ready"))

    def _ask_for_key_value(self, title: str, initial_key: str = "", initial_value: str = ""):
        key, ok = QInputDialog.getText(self, title, i18n.t("env_var_key_prompt"), text=initial_key)
        if not ok:
            return None, None, False

        key = key.strip()
        if not key or "=" in key:
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("msg_invalid_env_key"))
            return None, None, False

        value, ok = QInputDialog.getText(self, title, i18n.t("env_var_value_prompt"), text=initial_value)
        if not ok:
            return None, None, False

        return key, value, True

    def refresh(self):
        selected_name = self.instance_selector.currentData()
        self._load_instances(selected_name=selected_name)
        self._update_controls_state()
        self._reload_table()

    def add_env_var(self):
        instance_path = self._get_selected_instance_path()
        if not instance_path:
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("msg_select_instance_required"))
            return

        key, value, ok = self._ask_for_key_value(i18n.t("env_var_add_title"))
        if not ok:
            return

        try:
            InstallManager.set_instance_env_entry(instance_path, key, value)
            self.status_label.setText(i18n.t("msg_env_var_saved", key=key))
            self._reload_table()
        except Exception as e:
            QMessageBox.critical(self, i18n.t("title_error"), i18n.t("msg_operation_failed", error=str(e)))

    def edit_env_var(self):
        instance_path = self._get_selected_instance_path()
        if not instance_path:
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("msg_select_instance_required"))
            return

        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("msg_env_var_select_required"))
            return

        key_item = self.table.item(row, 0)
        value_item = self.table.item(row, 1)
        if not key_item:
            return

        old_key = key_item.text().strip()
        old_value = value_item.text() if value_item else ""
        key, value, ok = self._ask_for_key_value(i18n.t("env_var_edit_title"), old_key, old_value)
        if not ok:
            return

        try:
            if key != old_key:
                InstallManager.delete_instance_env_entry(instance_path, old_key)
            InstallManager.set_instance_env_entry(instance_path, key, value)
            self.status_label.setText(i18n.t("msg_env_var_saved", key=key))
            self._reload_table()
        except Exception as e:
            QMessageBox.critical(self, i18n.t("title_error"), i18n.t("msg_operation_failed", error=str(e)))

    def delete_env_var(self):
        instance_path = self._get_selected_instance_path()
        if not instance_path:
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("msg_select_instance_required"))
            return

        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, i18n.t("title_warning"), i18n.t("msg_env_var_select_required"))
            return

        key_item = self.table.item(row, 0)
        if not key_item:
            return
        key = key_item.text().strip()

        reply = QMessageBox.warning(
            self,
            i18n.t("title_confirm"),
            i18n.t("msg_confirm_delete_env_var", key=key),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            InstallManager.delete_instance_env_entry(instance_path, key)
            self.status_label.setText(i18n.t("msg_env_var_deleted", key=key))
            self._reload_table()
        except Exception as e:
            QMessageBox.critical(self, i18n.t("title_error"), i18n.t("msg_operation_failed", error=str(e)))

    def update_ui_texts(self):
        self.instance_label.setText(i18n.t("lbl_select_instance"))
        if self.instance_selector.count() > 0:
            self.instance_selector.setItemText(0, i18n.t("opt_select_instance"))
        self.btn_refresh.setText(i18n.t("btn_refresh"))
        self.btn_add.setText(i18n.t("btn_add"))
        self.btn_edit.setText(i18n.t("btn_edit"))
        self.btn_delete.setText(i18n.t("btn_delete"))
        self.table.setHorizontalHeaderLabels([
            i18n.t("env_var_col_key"),
            i18n.t("env_var_col_value"),
        ])
        self.refresh()
