from __future__ import annotations

import subprocess
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .audit import AuditLogger
from .config import AppConfig, ConfigStore, LauncherProfile, ROLE_PRESETS
from .process_manager import ProcessManager
from .safety import in_virtualenv, remediation_instructions, validate_loopback_host
from .task_master import TaskMasterPlanner


class MainWindow(QMainWindow):
    def __init__(self, config_store: ConfigStore | None = None):
        super().__init__()
        self.setWindowTitle("llama-server Launcher (Host Only)")
        self.resize(1100, 800)

        self.config_store = config_store or ConfigStore()
        self.config = self.config_store.load()
        self.audit = AuditLogger()
        self.process_manager = ProcessManager(self.audit)
        self.task_master = TaskMasterPlanner()

        self.profile_table = QTableWidget(0, 6)
        self.profile_table.setHorizontalHeaderLabels(["Name", "Role", "Host", "Port", "Mode", "Status"])

        self.name_input = QLineEdit()
        self.role_input = QComboBox()
        self.role_input.addItems(ROLE_PRESETS)
        self.server_input = QLineEdit()
        self.model_input = QLineEdit()
        self.projector_input = QLineEdit()
        self.host_input = QLineEdit("127.0.0.1")
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(8080)
        self.ctx_input = QSpinBox()
        self.ctx_input.setRange(256, 1048576)
        self.ctx_input.setValue(8192)
        self.gpu_layers_input = QSpinBox()
        self.gpu_layers_input.setRange(0, 1000)
        self.extra_args_input = QLineEdit()
        self.start_mode_input = QComboBox()
        self.start_mode_input.addItems(["always_on", "on_demand"])
        self.idle_shutdown_input = QSpinBox()
        self.idle_shutdown_input.setRange(0, 10080)
        self.task_master_toggle = QCheckBox("Enable Task Master (read-only planning)")
        self.task_master_toggle.setChecked(self.config.task_master_enabled)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        add_btn = QPushButton("Add/Update Profile")
        remove_btn = QPushButton("Remove Profile")
        start_btn = QPushButton("Start")
        stop_btn = QPushButton("Stop")
        restart_btn = QPushButton("Restart")
        health_btn = QPushButton("Health/Status")
        new_window_btn = QPushButton("Open Another Window")

        add_btn.clicked.connect(self.add_or_update_profile)
        remove_btn.clicked.connect(self.remove_profile)
        start_btn.clicked.connect(self.start_selected)
        stop_btn.clicked.connect(self.stop_selected)
        restart_btn.clicked.connect(self.restart_selected)
        health_btn.clicked.connect(self.health_selected)
        new_window_btn.clicked.connect(self.open_new_window)
        self.task_master_toggle.stateChanged.connect(self.on_task_master_toggle)

        controls = QHBoxLayout()
        for button in [add_btn, remove_btn, start_btn, stop_btn, restart_btn, health_btn, new_window_btn]:
            controls.addWidget(button)

        form = QFormLayout()
        form.addRow("Profile Name", self.name_input)
        form.addRow("Role", self.role_input)
        form.addRow("llama-server Binary", self.server_input)
        form.addRow("Model Path", self.model_input)
        form.addRow("Projector Path", self.projector_input)
        form.addRow("Host", self.host_input)
        form.addRow("Port", self.port_input)
        form.addRow("Context Size", self.ctx_input)
        form.addRow("GPU Layers", self.gpu_layers_input)
        form.addRow("Extra Args (space-separated)", self.extra_args_input)
        form.addRow("Start Mode", self.start_mode_input)
        form.addRow("Idle Shutdown Minutes (0=off)", self.idle_shutdown_input)

        layout = QVBoxLayout()
        layout.addWidget(self.task_master_toggle)
        layout.addWidget(self.profile_table)
        layout.addLayout(form)
        layout.addLayout(controls)
        layout.addWidget(QLabel("Task Master & process logs"))
        layout.addWidget(self.log_output)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        self.refresh_profiles()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_logs)
        self.timer.start(800)

        if not in_virtualenv():
            self.warn_not_in_venv()

    def warn_not_in_venv(self) -> None:
        QMessageBox.warning(self, "Virtual Environment Required", remediation_instructions())

    def selected_profile(self) -> LauncherProfile | None:
        row = self.profile_table.currentRow()
        if row < 0:
            return None
        profile_id = self.profile_table.item(row, 0).data(1)
        for profile in self.config.profiles:
            if profile.id == profile_id:
                return profile
        return None

    def refresh_profiles(self) -> None:
        self.profile_table.setRowCount(len(self.config.profiles))
        for idx, profile in enumerate(self.config.profiles):
            name_item = QTableWidgetItem(profile.name)
            name_item.setData(1, profile.id)
            self.profile_table.setItem(idx, 0, name_item)
            self.profile_table.setItem(idx, 1, QTableWidgetItem(profile.role))
            self.profile_table.setItem(idx, 2, QTableWidgetItem(profile.host))
            self.profile_table.setItem(idx, 3, QTableWidgetItem(str(profile.port)))
            self.profile_table.setItem(idx, 4, QTableWidgetItem(profile.start_mode))
            self.profile_table.setItem(idx, 5, QTableWidgetItem(self.process_manager.status(profile.id)))

    def collect_profile(self, existing_id: str | None = None) -> LauncherProfile:
        idle = self.idle_shutdown_input.value()
        extra_args = [token for token in self.extra_args_input.text().split(" ") if token]
        return LauncherProfile(
            name=self.name_input.text().strip(),
            role=self.role_input.currentText().strip(),
            llama_server_path=self.server_input.text().strip(),
            model_path=self.model_input.text().strip(),
            projector_path=self.projector_input.text().strip(),
            host=self.host_input.text().strip() or "127.0.0.1",
            port=self.port_input.value(),
            ctx_size=self.ctx_input.value(),
            gpu_layers=self.gpu_layers_input.value(),
            extra_args=extra_args,
            start_mode=self.start_mode_input.currentText(),
            idle_shutdown_minutes=(idle if idle > 0 else None),
            id=existing_id or LauncherProfile(name="tmp").id,
        )

    def add_or_update_profile(self) -> None:
        selected = self.selected_profile()
        profile = self.collect_profile(existing_id=selected.id if selected else None)
        if not profile.name:
            QMessageBox.warning(self, "Invalid profile", "Profile name is required.")
            return
        if selected:
            self.config.profiles = [profile if p.id == selected.id else p for p in self.config.profiles]
        else:
            self.config.profiles.append(profile)
        self.config_store.save(self.config)
        self.refresh_profiles()

    def confirm(self, title: str, text: str) -> bool:
        return QMessageBox.question(self, title, text) == QMessageBox.StandardButton.Yes

    def enforce_venv_for_execution(self) -> bool:
        if in_virtualenv():
            return True
        QMessageBox.critical(self, "Execution blocked", remediation_instructions())
        return False

    def start_selected(self) -> None:
        profile = self.selected_profile()
        if not profile:
            return
        if not self.enforce_venv_for_execution():
            return
        host_check = validate_loopback_host(profile.host)
        if not host_check.ok:
            approved_host = self.confirm(
                "Non-loopback binding",
                f"Host {profile.host} is non-loopback/invalid. Continue anyway?",
            )
            if not approved_host:
                return
        approved = self.confirm("Start Server", f"Start server '{profile.name}' on {profile.host}:{profile.port}?")
        try:
            self.process_manager.start(profile, approved)
            self.refresh_profiles()
        except Exception as exc:
            QMessageBox.critical(self, "Start failed", str(exc))

    def stop_selected(self) -> None:
        profile = self.selected_profile()
        if not profile:
            return
        approved = self.confirm("Stop Server", f"Stop server '{profile.name}'?")
        self.process_manager.stop(profile.id, approved)
        self.refresh_profiles()

    def restart_selected(self) -> None:
        profile = self.selected_profile()
        if not profile:
            return
        approved = self.confirm("Restart Server", f"Restart server '{profile.name}'?")
        self.process_manager.restart(profile, approved)
        self.refresh_profiles()

    def remove_profile(self) -> None:
        profile = self.selected_profile()
        if not profile:
            return
        approved = self.confirm("Remove Profile", f"Remove profile '{profile.name}'?")
        if not approved:
            return
        self.config.profiles = [p for p in self.config.profiles if p.id != profile.id]
        self.config_store.save(self.config)
        self.refresh_profiles()

    def health_selected(self) -> None:
        profile = self.selected_profile()
        if not profile:
            return
        state = self.process_manager.health(profile.id)
        QMessageBox.information(self, "Health", f"{profile.name}: {state}")

    def on_task_master_toggle(self) -> None:
        enabled = self.task_master_toggle.isChecked()
        self.config.task_master_enabled = enabled
        self.config_store.save(self.config)
        if not enabled:
            self.log_output.append("Task Master disabled.")
            return
        result = self.task_master.plan_read_only(self.config)
        self.log_output.append("Task Master read-only planning complete. No actions executed.")
        self.log_output.append(f"Discovered projects: {len(result.discoveries)}")
        for recommendation in result.recommendations:
            self.log_output.append(
                f"Recommend {recommendation['strategy']}: {recommendation['reason']}\n"
                f"Proposed argv: {recommendation['proposed_argv']}"
            )
        if result.model_inventory:
            self.log_output.append(f"Discovered GGUF models: {len(result.model_inventory)}")

    def open_new_window(self) -> None:
        python_exe = sys.executable
        module_name = "llama_project_team_ui.main"
        subprocess.Popen([python_exe, "-m", module_name])

    def refresh_logs(self) -> None:
        for profile in self.config.profiles:
            lines = self.process_manager.collect_logs(profile.id)
            for line in lines:
                self.log_output.append(f"[{profile.name}] {line}")
        self.refresh_profiles()


def launch() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
