"""Render current launcher widgets using an isolated, credential-free workspace.

Run with the launcher's Python environment:
  python scripts/capture_screenshots.py /path/to/main-checkout
"""
import json
import os
from pathlib import Path
import sys
import tempfile

source = Path(sys.argv[1]).resolve()
output = Path(__file__).resolve().parents[1] / "assets"
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_SCALE_FACTOR"] = "2"
sys.path.insert(0, str(source / "src"))

with tempfile.TemporaryDirectory(prefix="launcher-screenshots-") as directory:
    os.chdir(directory)
    Path("config.json").write_text(json.dumps({
        "language": "zh", "theme_mode": "light", "check_updates": False,
        "launch_sample_on_startup": False, "auto_start_llamacpp": False,
    }))
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from openclaw_launcher.ui.theme_manager import theme_manager
    from openclaw_launcher.ui.main_window import MainWindow

    app = QApplication([])
    theme_manager.initialize(app)
    window = MainWindow()
    window.resize(1200, 850)
    window.show()
    QTest.qWait(350)  # Allow the real sidebar expansion animations to finish.
    output.mkdir(exist_ok=True)
    window.grab().save(str(output / "onboard.png"))

    # A demo instance lets the real forms show their editable, empty state.
    demo = Path("instance/openclaw/.openclaw")
    demo.mkdir(parents=True)
    (demo / "openclaw.json").write_text("{}")
    window.channel_config_panel.refresh()
    window.channel_config_panel.instance_selector.setCurrentIndex(1)
    window.model_switch_panel.refresh_instance_list()
    window.backup_panel.refresh_lists()
    window.plugin_panel.refresh_plugins()
    for panel, filename in [
        ("channels", "channels.png"), ("model_switch", "models.png"),
        ("llamacpp", "llamacpp.png"), ("backups", "backup.png"),
        ("plugins", "plugin.png"), ("dependencies", "env.png"),
        ("env_vars", "variables.png"), ("logs", "log.png"),
        ("advanced", "advanced.png"), ("instances", "instance.png"),
    ]:
        window.switch_to_panel(panel)
        QTest.qWait(100)
        window.grab().save(str(output / filename))
    window.shutdown()
    window.hide()
    print(f"Saved 11 current launcher screenshots to {output}")
