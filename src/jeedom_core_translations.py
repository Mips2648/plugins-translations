import json
from pathlib import Path

from consts import LANGUAGES
from translations import Translations

class JeedomCoreTranslations:

    def __init__(self) -> None:
        self._core_root = Path.cwd()/'jeedom_core'
        self._all_translations: Translations

    def parse(self):
        if not self._core_root.exists():
            raise ValueError(f"Path {self._core_root.as_posix()} does not exists")

        for language in LANGUAGES:
            file = Path(self._core_root/f"{language}.json")
            if not file.exists():
                print(f"file {file.as_posix()} not found !?")
                continue

            data = json.loads(file.read_text(encoding="UTF-8"))
            for path in data:
                for text in data[path]:
                    self._all_translations.add_translation(language, text, data[path][text])

    def getTranslations(self):
        return self._all_translations

if __name__ == "__main__":
    JeedomCoreTranslations().parse()