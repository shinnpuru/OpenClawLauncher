from PySide6.QtCore import QObject, Qt, Signal
from ..core.config import Config


class ThemeManager(QObject):
    theme_mode_changed = Signal(str)

    MODE_LIGHT = "light"
    MODE_DARK = "dark"
    MODE_SYSTEM = "system"
    VALID_MODES = {MODE_LIGHT, MODE_DARK, MODE_SYSTEM}

    def __init__(self):
        super().__init__()
        self._app = None
        self._mode = Config.get_setting("theme_mode", self.MODE_SYSTEM)
        if self._mode not in self.VALID_MODES:
            self._mode = self.MODE_SYSTEM
        self._system_listener_connected = False

    @property
    def current_mode(self):
        return self._mode

    def initialize(self, app):
        self._app = app
        self._update_system_listener()
        self.apply_current_theme()

    def set_mode(self, mode: str):
        if mode not in self.VALID_MODES:
            mode = self.MODE_SYSTEM

        if mode == self._mode:
            return

        self._mode = mode
        Config.set_setting("theme_mode", mode)
        self._update_system_listener()
        self.apply_current_theme()
        self.theme_mode_changed.emit(mode)

    def apply_current_theme(self):
        if self._app is None:
            return

        resolved = self._resolve_effective_theme()
        theme_name = "dark_teal.xml" if resolved == self.MODE_DARK else "light_teal.xml"

        try:
            from qt_material import apply_stylesheet

            apply_stylesheet(self._app, theme=theme_name)
        except Exception:
            pass

    def _resolve_effective_theme(self) -> str:
        if self._mode == self.MODE_LIGHT:
            return self.MODE_LIGHT
        if self._mode == self.MODE_DARK:
            return self.MODE_DARK

        if self._app is None:
            return self.MODE_DARK

        try:
            style_hints = self._app.styleHints()
            if style_hints and hasattr(style_hints, "colorScheme"):
                scheme = style_hints.colorScheme()
                if scheme == Qt.ColorScheme.Dark:
                    return self.MODE_DARK
                if scheme == Qt.ColorScheme.Light:
                    return self.MODE_LIGHT
        except Exception:
            pass

        try:
            window_color = self._app.palette().window().color()
            return self.MODE_DARK if window_color.lightness() < 128 else self.MODE_LIGHT
        except Exception:
            return self.MODE_DARK

    def _update_system_listener(self):
        if self._app is None:
            return

        style_hints = self._app.styleHints()
        if not style_hints or not hasattr(style_hints, "colorSchemeChanged"):
            return

        should_connect = self._mode == self.MODE_SYSTEM

        if should_connect and not self._system_listener_connected:
            style_hints.colorSchemeChanged.connect(self._on_system_color_scheme_changed)
            self._system_listener_connected = True
        elif not should_connect and self._system_listener_connected:
            try:
                style_hints.colorSchemeChanged.disconnect(self._on_system_color_scheme_changed)
            except Exception:
                pass
            self._system_listener_connected = False

    def _on_system_color_scheme_changed(self, *_args):
        if self._mode == self.MODE_SYSTEM:
            self.apply_current_theme()


theme_manager = ThemeManager()