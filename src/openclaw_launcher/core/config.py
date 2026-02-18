import os
import json
from pathlib import Path

class Config:
    """
    Configuration manager for the OpenClaw Launcher.
    Stores and retrieves paths and settings.
    """
    APP_NAME = "OpenClaw Launcher"
    BASE_DIR = Path(os.getcwd()) # Relative to launcher runtime as requested
    INSTANCES_DIR = BASE_DIR / "instance"
    LOGS_DIR = BASE_DIR / "logs"
    print(f"Base Dir: {BASE_DIR}")
    CONFIG_FILE = BASE_DIR / "config.json"
    
    @classmethod
    def get_language(cls) -> str:
        """Get the current language setting."""
        return cls.get_setting("language", "zh")

    @classmethod
    def set_language(cls, lang: str):
        """Save the language setting."""
        cls.set_setting("language", lang)

    @classmethod
    def get_setting(cls, key: str, default=None):
        """Get a setting value."""
        if cls.CONFIG_FILE.exists():
            try:
                with open(cls.CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get(key, default)
            except Exception:
                pass
        return default

    @classmethod
    def set_setting(cls, key: str, value):
        """Save a setting value."""
        data = {}
        if cls.CONFIG_FILE.exists():
            try:
                with open(cls.CONFIG_FILE, 'r') as f:
                    data = json.load(f)
            except Exception:
                pass
        
        data[key] = value
        
        # Ensure base dir exists
        cls.BASE_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(cls.CONFIG_FILE, 'w') as f:
            json.dump(data, f, indent=4)

    @classmethod
    def ensure_dirs(cls):
        """Ensure necessary directories exist."""
        cls.INSTANCES_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_instance_path(cls, instance_name: str) -> Path:
        """Get the path for specific instance."""
        return cls.INSTANCES_DIR / instance_name

    @classmethod
    def get_log_file(cls, instance_name: str) -> Path:
        """Get the log file path for a specific instance."""
        return cls.LOGS_DIR / f"{instance_name}.log"
