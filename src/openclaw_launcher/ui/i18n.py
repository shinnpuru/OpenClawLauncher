import json
from pathlib import Path
from PySide6.QtCore import QObject, Signal
from ..core.config import Config

class I18nManager(QObject):
    language_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self._translations = {}
        self._available_languages = []
        self._base_dir = Path(__file__).parent / "i18n"
        self._load_languages()
        
        self._current_lang = Config.get_language()
        if self._current_lang not in self._available_languages:
            if "zh" in self._available_languages:
                self._current_lang = "zh"
            elif "en" in self._available_languages:
                self._current_lang = "en"
             
    @property
    def current_lang(self):
        return self._current_lang

    @property
    def available_languages(self):
        return self._available_languages

    def _load_languages(self):
        """Load all json files from the i18n directory."""
        if not self._base_dir.exists():
            print(f"Warning: i18n directory not found at {self._base_dir}")
            return
            
        for file_path in self._base_dir.glob("*.json"):
            lang_code = file_path.stem
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self._translations[lang_code] = json.load(f)
                    self._available_languages.append(lang_code)
            except Exception as e:
                print(f"Error loading translation for {lang_code}: {e}")

    def set_language(self, lang: str):
        if lang in self._available_languages and lang != self._current_lang:
            self._current_lang = lang
            Config.set_language(lang)
            self.language_changed.emit(lang)

    def t(self, key: str, **kwargs) -> str:
        """Get translated string."""
        # Try current language
        lang_data = self._translations.get(self._current_lang, {})
        text = lang_data.get(key)
        
        # Fallback to English if not found
        if text is None:
             lang_data = self._translations.get("en", {})
             text = lang_data.get(key, key) # Fallback to key if even English is missing
        
        if kwargs:
            try:
                return text.format(**kwargs)
            except KeyError:
                return text
        return text

# Global instance
i18n = I18nManager()
