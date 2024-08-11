class Prompt():

    def __init__(self, text) -> None:
        self._text: str = text
        self._translations: dict[str, str] = {}

    def get_text(self):
        return self._text

    def has_translation(self, language: str):
        return language in self._translations and self._translations[language] != ''

    def set_translation(self, language: str, translation: str):
        self._translations[language] = translation

    def get_translation(self, language: str):
        return self._translations[language] if language in self._translations else ''

    def set_translations(self, translations: dict[str, str]):
        self._translations = translations

    def get_translations(self):
        return self._translations
