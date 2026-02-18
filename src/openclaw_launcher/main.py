import sys
import os

# Ensure src/ is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Ensure working directory is correct for both dev and PyInstaller bundles.
if hasattr(sys, "_MEIPASS"):
    os.chdir(sys._MEIPASS)
else:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from openclaw_launcher.ui.main_window import MainWindow
from openclaw_launcher.ui.theme_manager import theme_manager


def _resolve_logo_path() -> str | None:
    candidates = []
    if hasattr(sys, "_MEIPASS"):
        candidates.append(os.path.join(sys._MEIPASS, "logo.png"))

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    candidates.append(os.path.join(project_root, "logo.png"))

    candidates.append(os.path.join(os.getcwd(), "logo.png"))

    for path in candidates:
        if os.path.exists(path):
            return path
    return None

def main():
    app = QApplication(sys.argv)
    theme_manager.initialize(app)

    logo_path = _resolve_logo_path()
    if logo_path:
        icon = QIcon(logo_path)
        if not icon.isNull():
            app.setWindowIcon(icon)
        
    window = MainWindow()
    if logo_path:
        icon = QIcon(logo_path)
        if not icon.isNull():
            window.setWindowIcon(icon)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
