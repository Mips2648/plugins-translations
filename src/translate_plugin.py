import json
import logging
import os
from pathlib import Path

import deepl

from source_file import SourceFile
from consts import (
    ALL_LANGUAGES,
    CORE_ROOT,
    FR_FR,
    INPUT_DEBUG,
    INPUT_DEEPL_API_KEY,
    INPUT_GENERATE_SOURCE_LANGUAGE_TRANSLATIONS,
    INPUT_INCLUDE_EMPTY_TRANSLATION,
    FILE_EXTS,
    INPUT_SOURCE_LANGUAGE,
    INPUT_TARGET_LANGUAGES,
    INPUT_USE_CORE_TRANSLATIONS,
    LANGUAGES_TO_DEEPL,
    LOG_FORMAT,
    PLUGIN_DIRS,
    PLUGIN_INFO_JSON,
    PLUGIN_ROOT,
    TRANSLATIONS_FILES_PATH
    )
from translations import Translations

class TranslatePlugin():

    def __init__(self) -> None:
        self._plugin_root = Path.cwd()/PLUGIN_ROOT
        self._plugin_id: str
        self._plugin_name: str

        self._files: dict[str, SourceFile] = {}
        self._existing_translations = Translations()
        self._source_language: str
        self._target_languages: list[str] = []
        self.__include_empty_translation: bool = False
        self.__use_core_translations: bool = True
        self.__generate_source_language_translations: bool = False

        self._logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

        self._core_root = Path.cwd()/CORE_ROOT
        self._core_translations = Translations()

        self.__translator: deepl.Translator = None
        self.__deepl_api_key: str = None
        self.__api_call_counter = 0

        self.__get_inputs()
        self.__read_info_json()

        self.__glossary: dict[str, deepl.GlossaryInfo] = {l:None for l in self._target_languages}

    def __del__(self):
        if self.__translator is None:
            return

        for language in self._target_languages:
            if self.__glossary[language] is None:
                continue

            self.__translator.delete_glossary(self.__glossary[language])

    def start(self):
        self.get_plugin_translations()

        if self.__use_core_translations:
            self.get_core_translations()

        self.find_prompts_in_all_files()

        self.do_translate()

        self.write_plugin_translations()

        self.__write_info_json()

    def __get_inputs(self):

        self._source_language = self._get_input_in_list(INPUT_SOURCE_LANGUAGE, ALL_LANGUAGES)
        self._target_languages = self._get_list_input(INPUT_TARGET_LANGUAGES, ALL_LANGUAGES)
        self.__deepl_api_key = self._get_input(INPUT_DEEPL_API_KEY)
        self.__include_empty_translation = self._get_boolean_input(INPUT_INCLUDE_EMPTY_TRANSLATION)
        if self._source_language != FR_FR:
            self.__use_core_translations = False
        else:
            self.__use_core_translations = self._get_boolean_input(INPUT_USE_CORE_TRANSLATIONS)
        self.__generate_source_language_translations = self._get_boolean_input(INPUT_GENERATE_SOURCE_LANGUAGE_TRANSLATIONS)
        debug = self._get_boolean_input(INPUT_DEBUG)
        if debug:
            self._logger.setLevel(logging.DEBUG)

        self._logger.info("=== Run plugin translation with following options ===")
        self._logger.info(f"source language: {self._source_language}")
        self._logger.info(f"target languages: {self._target_languages}")
        self._logger.info(f"include empty translation: {self.__include_empty_translation}")
        self._logger.info(f"use core translations: {self.__use_core_translations}")
        self._logger.info(f"generate source language translations: {self.__generate_source_language_translations}")
        self._logger.info(f"debug: {debug}")
        self._logger.info(f"deepl api key present: {self.__deepl_api_key is not None}")
        self._logger.info("=====================================================")

    def _get_input(self, name: str):
        val = os.environ[name].strip() if name in os.environ else ''
        return val if val != '' else None

    def _get_boolean_input(self, name: str):
        val = self._get_input(name)
        trueValue = ['true', 'True', 'TRUE']
        falseValue = ['false', 'False', 'FALSE']
        if val in trueValue:
            return True
        elif val in falseValue:
            return False
        else:
            raise ValueError(f'Input does not meet specifications: {name}.\n Support boolean input list: "true | True | TRUE | false | False | FALSE"')

    def _get_list_input(self, name: str, allowed_values: list):
        val = self._get_input(name)
        list = [s.strip() for s in val.split(',')]
        for s in list:
            if s not in allowed_values:
                raise ValueError(f'Input does not meet specifications: {name}.\n {s} not in list: {allowed_values}')
        return list

    def _get_input_in_list(self, name: str, allowed_values: list):
        val = self._get_input(name)
        if val is None or val not in allowed_values:
            raise ValueError(f'Input does not meet specifications: {name}.\n {val} not in list: {allowed_values}')
        return val

    def __read_info_json(self):
        info_json = self._plugin_root/PLUGIN_INFO_JSON
        if not info_json.is_file():
            raise RuntimeError("Missing info.json file")

        data = json.loads(info_json.read_text(encoding="UTF-8"))
        self._plugin_id = data['id']
        self._plugin_name = data['name']

    def __write_info_json(self):
        info_json = self._plugin_root/PLUGIN_INFO_JSON
        if not info_json.is_file():
            raise RuntimeError("Missing info.json file")

        data = json.loads(info_json.read_text(encoding="UTF-8"))
        data['language'] = sorted(set([self._source_language] + self._target_languages))
        info_json.write_text(json.dumps(data, ensure_ascii=False, indent= '\t'), encoding="UTF-8")

    @property
    def translator(self):
        if self.__translator is not None:
            return self.__translator

        if self.__deepl_api_key is not None:
            self.__translator = deepl.Translator(self.__deepl_api_key)
            self.__create_deepl_glossaries()
        return self.__translator

    def __create_deepl_glossaries(self):
        fileDir = Path(__file__).parent
        glossary = fileDir/f"{self._source_language}_glossary.json"
        if not glossary.exists():
            return

        entries = json.loads(glossary.read_text(encoding="UTF-8"))
        for target_language in self._target_languages:
            if target_language ==  self._source_language or target_language not in entries:
                continue
            self._logger.info(f"Create glossary {self._source_language}=>{target_language}")
            self.__glossary[target_language] = self.__translator.create_glossary('plugin', source_lang=LANGUAGES_TO_DEEPL[self._source_language], target_lang=LANGUAGES_TO_DEEPL[target_language], entries=entries[target_language])

    def find_prompts_in_all_files(self):
        self._logger.info("Find prompts in all plugin files")
        for dir in PLUGIN_DIRS:
            plugin_dir = self._plugin_root/dir
            for root, dirs, files in plugin_dir.walk():
                for dirname in dirs:
                    if root.name == "core" and dirname == 'i18n':
                        dirs.remove(dirname)
                    # for d in excludes:
                    #     if fnmatch.fnmatch(dirname, d):
                    #         dirs.remove(dirname)

                for file in files:
                    if file == 'info.json':
                        continue
                    # for f in excludes:
                    #     if fnmatch.fnmatch(fileName, f):
                    #         continue
                    filename = Path(file)
                    if filename.suffix in FILE_EXTS:
                        absolute_file_path = root/filename
                        jeedom_file_path = absolute_file_path.relative_to(self._plugin_root)
                        jeedom_file_path = (f"plugins/{self._plugin_id}"/jeedom_file_path).as_posix()
                        self._logger.info(f"    {jeedom_file_path}...")
                        self._files[jeedom_file_path] = SourceFile(absolute_file_path, self._logger)
                        self._files[jeedom_file_path].search_prompts()

    def do_translate(self):
        self._logger.info("Find existing translations...")
        for file in self._files.values():
            for prompt in file.get_prompts().values():
                # first get translations from existing translations (plugin & core) if exists
                if prompt.get_text() in self._existing_translations:
                    tr = self._existing_translations.get_translations(prompt.get_text())
                    # self._logger.info(f"find translation for {prompt.get_text()} => {tr}")
                    prompt.set_translations(tr)

                # make sure to store text as a target translation for source language
                prompt.set_translation(self._source_language, prompt.get_text())

                if self.translator is not None:
                    # make call to deepl translator for any missing translations
                    for target_language in self._target_languages:
                        if target_language==self._source_language:
                            continue
                        if not prompt.has_translation(target_language):
                            self._logger.debug(f"call deepl to translate {prompt.get_text()} in {target_language}")
                            self.__api_call_counter += 1
                            result = self.translator.translate_text(prompt.get_text(), source_lang=LANGUAGES_TO_DEEPL[self._source_language], target_lang=LANGUAGES_TO_DEEPL[target_language],
                                                                      preserve_formatting=True, context='home automation', split_sentences=0, glossary=self.__glossary[target_language])
                            prompt.set_translation(target_language, result.text)
                            self._existing_translations.add_translation(target_language, prompt.get_text(), result.text)
        self._logger.info(f"Number of api call done: {self.__api_call_counter}")

    def get_plugin_translations(self):
        self._logger.info("Read plugin translations file...")
        self.get_translations_from_json_files(self._plugin_root/TRANSLATIONS_FILES_PATH)

    def get_core_translations(self):
        if not self._core_root.exists():
            raise RuntimeError(f"Path {self._core_root.as_posix()} does not exists")

        self._logger.info("Read core translations file...")
        self.get_translations_from_json_files(self._core_root/TRANSLATIONS_FILES_PATH)

    def get_translations_from_json_files(self, dir: Path):
        for language in self._target_languages:
            file = dir/f"{language}.json"
            if not file.exists():
                self._logger.info(f"file {file.as_posix()} not found !?")
                continue

            data = json.loads(file.read_text(encoding="UTF-8"))
            for path in data:
                for text in data[path]:
                    self._existing_translations.add_translation(language, text, data[path][text])

    def write_plugin_translations(self):
        self._logger.info("Ecriture du/des fichier(s) de traduction(s)...")

        translation_path = self._plugin_root/TRANSLATIONS_FILES_PATH
        translation_path.mkdir(parents=True, exist_ok=True)

        for target_language in self._target_languages:
            if target_language == self._source_language and not self.__generate_source_language_translations:
                continue

            translation_file = translation_path/f"{target_language}.json"

            language_result = {}
            for path, file in self._files.items():
                prompts = file.get_prompts_and_translation(target_language, self.__include_empty_translation)
                if len(prompts) > 0:
                    language_result[path] = prompts

            if (len(language_result) > 0):
                self._logger.info(f"Will dump {translation_file.as_posix()}")
                translation_file.write_text(json.dumps(language_result, ensure_ascii=False, sort_keys = True, indent= 4).replace('/', r'\/'), encoding="UTF-8")

if __name__ == "__main__":
    TranslatePlugin().start()