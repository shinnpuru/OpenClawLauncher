import os
import platform
import plistlib
import shlex
import subprocess
import sys
from pathlib import Path

from .config import Config


class AutoStartManager:
    LAUNCH_AGENT_LABEL = "io.openclaw.launcher"
    WINDOWS_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
    WINDOWS_VALUE_NAME = "OpenClawLauncher"
    LINUX_DESKTOP_FILE = "openclaw-launcher.desktop"

    @classmethod
    def is_supported(cls) -> bool:
        return platform.system() in {"Darwin", "Windows", "Linux"}

    @classmethod
    def _platform(cls) -> str:
        return platform.system()

    @classmethod
    def _plist_path(cls) -> Path:
        return Path.home() / "Library" / "LaunchAgents" / f"{cls.LAUNCH_AGENT_LABEL}.plist"

    @classmethod
    def _program_arguments(cls) -> list[str]:
        if getattr(sys, "frozen", False):
            return [str(Path(sys.executable).resolve())]

        main_script = Path(__file__).resolve().parent.parent / "main.py"
        return [str(Path(sys.executable).resolve()), str(main_script)]

    @classmethod
    def _command_line(cls) -> str:
        args = cls._program_arguments()
        return " ".join(shlex.quote(part) for part in args)

    @classmethod
    def _build_plist_content(cls) -> dict:
        Config.ensure_dirs()
        return {
            "Label": cls.LAUNCH_AGENT_LABEL,
            "ProgramArguments": cls._program_arguments(),
            "RunAtLoad": True,
            "KeepAlive": False,
            "WorkingDirectory": str(Config.BASE_DIR),
            "StandardOutPath": str(Config.LOGS_DIR / "launcher-autostart.log"),
            "StandardErrorPath": str(Config.LOGS_DIR / "launcher-autostart.log"),
        }

    @classmethod
    def _write_plist(cls) -> Path:
        plist_path = cls._plist_path()
        plist_path.parent.mkdir(parents=True, exist_ok=True)
        with open(plist_path, "wb") as f:
            plistlib.dump(cls._build_plist_content(), f)
        return plist_path

    @classmethod
    def _bootout(cls):
        plist_path = cls._plist_path()
        subprocess.run(
            ["launchctl", "bootout", f"gui/{os.getuid()}", str(plist_path)],
            capture_output=True,
            text=True,
            check=False,
        )

    @classmethod
    def _bootstrap(cls, plist_path: Path):
        result = subprocess.run(
            ["launchctl", "bootstrap", f"gui/{os.getuid()}", str(plist_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "launchctl bootstrap failed")

    @classmethod
    def _set_enabled_macos(cls, enabled: bool):
        plist_path = cls._plist_path()
        if enabled:
            plist_path = cls._write_plist()
            cls._bootout()
            cls._bootstrap(plist_path)
            return

        cls._bootout()
        if plist_path.exists():
            plist_path.unlink()

    @classmethod
    def _is_enabled_macos(cls) -> bool:
        return cls._plist_path().exists()

    @classmethod
    def _set_enabled_windows(cls, enabled: bool):
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.WINDOWS_RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, cls.WINDOWS_VALUE_NAME, 0, winreg.REG_SZ, cls._command_line())
            else:
                try:
                    winreg.DeleteValue(key, cls.WINDOWS_VALUE_NAME)
                except FileNotFoundError:
                    pass

    @classmethod
    def _is_enabled_windows(cls) -> bool:
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.WINDOWS_RUN_KEY, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, cls.WINDOWS_VALUE_NAME)
                return bool(value)
        except FileNotFoundError:
            return False

    @classmethod
    def _linux_autostart_path(cls) -> Path:
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
        config_home = Path(xdg_config_home).expanduser() if xdg_config_home else (Path.home() / ".config")
        return config_home / "autostart" / cls.LINUX_DESKTOP_FILE

    @classmethod
    def _linux_desktop_entry(cls) -> str:
        Config.ensure_dirs()
        return (
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Version=1.0\n"
            "Name=OpenClaw Launcher\n"
            "Comment=Start OpenClaw Launcher on login\n"
            f"Exec={cls._command_line()}\n"
            f"Path={str(Config.BASE_DIR)}\n"
            "Terminal=false\n"
            "X-GNOME-Autostart-enabled=true\n"
        )

    @classmethod
    def _set_enabled_linux(cls, enabled: bool):
        desktop_path = cls._linux_autostart_path()
        if enabled:
            desktop_path.parent.mkdir(parents=True, exist_ok=True)
            desktop_path.write_text(cls._linux_desktop_entry(), encoding="utf-8")
            return

        if desktop_path.exists():
            desktop_path.unlink()

    @classmethod
    def _is_enabled_linux(cls) -> bool:
        return cls._linux_autostart_path().exists()

    @classmethod
    def is_enabled(cls) -> bool:
        if not cls.is_supported():
            return False

        current = cls._platform()
        if current == "Darwin":
            return cls._is_enabled_macos()
        if current == "Windows":
            return cls._is_enabled_windows()
        if current == "Linux":
            return cls._is_enabled_linux()
        return False

    @classmethod
    def set_enabled(cls, enabled: bool):
        if not cls.is_supported():
            raise RuntimeError("Auto-start is not supported on this OS.")

        current = cls._platform()
        if current == "Darwin":
            cls._set_enabled_macos(enabled)
            return
        if current == "Windows":
            cls._set_enabled_windows(enabled)
            return
        if current == "Linux":
            cls._set_enabled_linux(enabled)
            return

        raise RuntimeError("Auto-start is not supported on this OS.")
