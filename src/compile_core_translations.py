import argparse
import json
from pathlib import Path

from consts import LANGUAGES

class CompileCoreTranslations:

    def __init__(self) -> None:
        parser = argparse.ArgumentParser(description='Daemon for Jeedom plugin')
        parser.add_argument("--source", help="Path to source folder containing i18n json files", type=str)
        parser.add_argument("--destination", help="Path to destination folder to write compile i18n json files", type=str)
        args = parser.parse_args()

        self._source_path = args.source
        self._dest_path = args.destination

        self._all_translations = {}


    def start(self):
        self._get_all_translations()

    def _init_language(self, language):
        self._all_translations[language] = {}

    def _get_all_translations(self):
        source = Path(self._source_path)
        if not source.exists():
            raise ValueError(f"Path {source.as_posix()} does not exists")

        for language in LANGUAGES:
            self._init_language(language)

            file = Path(source/f"{language}.json")
            if not file.exists():
                print(f"file {file.as_posix()} not found !?")
                continue

            data = json.loads(file.read_text(encoding="UTF-8"))
            for path in data:
                for text in data[path]:
                    self._add_translation(language, text, data[path][text])

            self._write_file(language)

    def _add_translation(self, language, text, translation):
        if translation == text:
            # not an actual translation, do not keep it
            return

        if text not in self._all_translations[language]:
            self._all_translations[language][text] = translation
        else:
            existing_translation = self._all_translations[language][text]
            if existing_translation == text :
                # not actual translation yet, save it; could not happen in theory
                existing_translation = self._all_translations[language][text]
            elif existing_translation != translation:
                print(f"2 differents translations for '{text}', keep first: '{existing_translation}' <> '{translation}'")
            else:
                pass #all fine, we found twice the same text and same translation

    def _write_file(self, language):
        destination = Path(self._dest_path)

        translation_file = destination/f"{language}.json"
        print(f"Will dump {translation_file.as_posix()}")
        translation_file.write_text(json.dumps(self._all_translations[language], ensure_ascii=False, sort_keys = True, indent= 4), encoding="UTF-8")


if __name__ == "__main__":
    CompileCoreTranslations().start()