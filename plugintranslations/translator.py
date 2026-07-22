import json
import logging
import os
from pathlib import Path
import hashlib

import deepl
from deepl.api_data import (
    MultilingualGlossaryDictionaryEntries,
    MultilingualGlossaryInfo,
)

from .throttle import Throttle

from .version import VERSION
from .source_file import SourceFile
from .consts import (
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
    LANGUAGES_TO_DEEPL_GLOSSARY,
    LOG_FORMAT,
    PLUGIN_DIRS,
    PLUGIN_INFO_JSON,
    PLUGIN_ROOT,
    TRANSLATIONS_FILES_PATH
)
from .translations import Translations


class PluginTranslator():

    def __init__(self, cwd: Path = Path.cwd()) -> None:
        self.__plugin_root = cwd/PLUGIN_ROOT

        self.__files: dict[str, SourceFile] = {}
        self.__existing_translations = Translations()
        self.__source_language: str
        self.__target_languages: list[str] = []
        self.__include_empty_translation: bool = False
        self.__use_core_translations: bool = True
        self.__generate_source_language_translations: bool = False

        self.__logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
        logging.getLogger('deepl').setLevel(logging.WARNING)

        self.__core_root = cwd/CORE_ROOT

        self.__deepl_client: deepl.DeepLClient | None = None
        self.__deepl_api_key: str | None = None
        self.__api_call_counter = 0

        self.__info_json_file: Path = self.__plugin_root/PLUGIN_INFO_JSON
        self.__info_json_content: dict | None = None

        self.__get_inputs()
        self.__read_info_json()

        self.__glossary: MultilingualGlossaryInfo | None = None

        self.__logger.info(f"Translate plugin module version {VERSION} initialized with deepl version {deepl.__version__}")

    def __del__(self):
        if self.__deepl_client is None:
            return

    @property
    def deepl_client(self):
        if self.__deepl_client is not None:
            return self.__deepl_client

        if self.__deepl_api_key is not None:
            self.__deepl_client = deepl.DeepLClient(self.__deepl_api_key)
            self.__create_deepl_glossaries(self.__deepl_client)
        return self.__deepl_client

    @property
    def plugin_id(self) -> str:
        return self.__info_json_content['id'] if self.__info_json_content is not None else 'unknown'

    def start(self):
        self.get_plugin_translations()

        if self.__use_core_translations:
            self.get_core_translations()

        self.find_prompts_in_all_files()

        self.do_translate()
        self.translate_info_json()

        self.write_plugin_translations()

        self.__write_info_json()

    def __get_inputs(self):

        self.__source_language = self._get_input_in_list(INPUT_SOURCE_LANGUAGE, ALL_LANGUAGES)
        self.__target_languages = self._get_list_input(INPUT_TARGET_LANGUAGES, ALL_LANGUAGES)
        self.__deepl_api_key = self._get_input(INPUT_DEEPL_API_KEY)
        self.__include_empty_translation = self._get_boolean_input(INPUT_INCLUDE_EMPTY_TRANSLATION)
        if self.__source_language != FR_FR:
            self.__use_core_translations = False
        else:
            self.__use_core_translations = self._get_boolean_input(INPUT_USE_CORE_TRANSLATIONS)
        self.__generate_source_language_translations = self._get_boolean_input(INPUT_GENERATE_SOURCE_LANGUAGE_TRANSLATIONS)
        debug = self._get_boolean_input(INPUT_DEBUG)
        if debug:
            self.__logger.setLevel(logging.DEBUG)

        self.__logger.info("=== Run plugin translation with following options ===")
        self.__logger.info(f"source language: {self.__source_language}")
        self.__logger.info(f"target languages: {self.__target_languages}")
        self.__logger.info(f"include empty translation: {self.__include_empty_translation}")
        self.__logger.info(f"use core translations: {self.__use_core_translations}")
        self.__logger.info(f"generate source language translations: {self.__generate_source_language_translations}")
        self.__logger.info(f"debug: {debug}")
        self.__logger.info(f"deepl api key present: {self.__deepl_api_key is not None}")
        self.__logger.info("=====================================================")

    def _get_input(self, name: str):
        val = os.environ[name].strip() if name in os.environ else ''
        return val if val != '' else None

    def _get_boolean_input(self, name: str):
        val = self._get_input(name)
        true_values = ['true', 'True', 'TRUE']
        false_values = ['false', 'False', 'FALSE']
        if val in true_values:
            return True
        elif val in false_values:
            return False
        else:
            raise ValueError(f'Input does not meet specifications: {name}.\n Support boolean input list: "true | True | TRUE | false | False | FALSE"')

    def _get_list_input(self, name: str, allowed_values: list):
        val = self._get_input(name)
        if val is None:
            raise ValueError(f'Input does not meet specifications: {name}.\n {name} is required')
        values = [s.strip() for s in val.split(',')]
        for s in values:
            if s not in allowed_values:
                raise ValueError(f'Input does not meet specifications: {name}.\n {s} not in list: {allowed_values}')
        return values

    def _get_input_in_list(self, name: str, allowed_values: list):
        val = self._get_input(name)
        if val is None or val not in allowed_values:
            raise ValueError(f'Input does not meet specifications: {name}.\n {val} not in list: {allowed_values}')
        return val

    def __read_info_json(self):
        if not self.__info_json_file.is_file():
            raise RuntimeError("Missing info.json file")
        try:
            self.__info_json_content = json.loads(self.__info_json_file.read_text(encoding="UTF-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise RuntimeError(f"Invalid info.json file: {e}") from e

    def __write_info_json(self):
        if self.__info_json_content is None:
            self.__logger.warning("No info.json content to write, skipping...")
            return
        self.__info_json_content['language'] = sorted(set([self.__source_language] + self.__target_languages))
        self.__info_json_file.write_text(json.dumps(self.__info_json_content, ensure_ascii=False, indent='\t'), encoding="UTF-8")

    def __create_deepl_glossaries(self, deepl_client: deepl.DeepLClient):
        file_dir = Path(__file__).parent
        glossary_file = file_dir/f"{self.__source_language}_glossary.json"
        if not glossary_file.exists():
            return

        str_entries = glossary_file.read_text(encoding="UTF-8")
        entries = json.loads(str_entries)
        md5_hash = hashlib.md5(json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()
        glossary_dictionaries = []

        for target_language, target_entries in entries.items():
            if target_language == self.__source_language:
                continue
            if target_language not in LANGUAGES_TO_DEEPL_GLOSSARY:
                self.__logger.warning(f"Glossary target language {target_language} is not supported by DeepL glossary API, skipping")
                continue
            glossary_dictionaries.append(
                MultilingualGlossaryDictionaryEntries(
                    LANGUAGES_TO_DEEPL_GLOSSARY[self.__source_language],
                    LANGUAGES_TO_DEEPL_GLOSSARY[target_language],
                    target_entries,
                )
            )

        if len(glossary_dictionaries) == 0:
            self.__logger.warning("No glossary dictionaries found, skipping glossary creation")
            return

        self.__logger.info(f"Check glossary {md5_hash}")

        for deepl_glossary in deepl_client.list_multilingual_glossaries():
            if deepl_glossary.name == md5_hash and self.__glossary is None:
                self.__logger.info("Already exists")
                self.__glossary = deepl_glossary
                return
            else:
                self.__logger.info(f"Delete existing old glossary {deepl_glossary.name}")
                deepl_client.delete_multilingual_glossary(deepl_glossary)

        if self.__glossary is None:
            self.__logger.info(f"Create new glossary {md5_hash}")
            self.__glossary = deepl_client.create_multilingual_glossary(md5_hash, glossary_dictionaries)

    def find_prompts_in_all_files(self):
        self.__logger.info("Find prompts in all plugin files")
        for dir in PLUGIN_DIRS:
            plugin_dir = self.__plugin_root/dir
            if not plugin_dir.exists():
                self.__logger.info(f"Directory {plugin_dir.as_posix()} not found, skipping...")
                continue

            for root, dirs, files in plugin_dir.walk():
                dirs[:] = [d for d in dirs if not (root.name == "core" and d == 'i18n')]

                for file in files:
                    if file == 'info.json':
                        continue
                    filename = Path(file)
                    if filename.suffix in FILE_EXTS:
                        absolute_file_path = root/filename
                        jeedom_file_path = absolute_file_path.relative_to(self.__plugin_root)
                        jeedom_file_path = (f"plugins/{self.plugin_id}"/jeedom_file_path).as_posix()
                        self.__logger.info(f"    {jeedom_file_path}...")
                        self.__files[jeedom_file_path] = SourceFile(absolute_file_path, self.__logger)
                        self.__files[jeedom_file_path].search_prompts()

    def do_translate(self):
        self.__logger.info("Find existing translations...")
        for file in self.__files.values():
            for prompt in file.get_prompts().values():
                # first get translations from existing translations (plugin & core) if exists
                if prompt.get_text() in self.__existing_translations:
                    tr = self.__existing_translations.get_translations(prompt.get_text())
                    prompt.set_translations(tr)

                # make sure to store text as a target translation for source language
                prompt.set_translation(self.__source_language, prompt.get_text())

                if self.deepl_client is not None:
                    # make call to deepl translator for any missing translations
                    for target_language in self.__target_languages:
                        if target_language == self.__source_language:
                            continue
                        if not prompt.has_translation(target_language):
                            tr = self.translate_with_deepl(prompt.get_text(), target_language)
                            prompt.set_translation(target_language, tr)
                            self.__existing_translations.add_translation(target_language, prompt.get_text(), tr)
        self.__logger.info(f"Number of api call done: {self.__api_call_counter}")

    def translate_info_json(self):
        if self.deepl_client is None:
            return
        if self.__info_json_content is None:
            return

        if 'description' not in self.__info_json_content:
            self.__logger.warning("You should add a 'Description' in info.json, see https://doc.jeedom.com/fr_FR/dev/structure_info_json")
            return
        descriptions = self.__info_json_content['description']
        if not isinstance(descriptions, dict):
            descriptions = {self.__source_language: descriptions}

        allowed_languages = set([self.__source_language] + self.__target_languages)
        descriptions = {
            language: description
            for language, description in descriptions.items()
            if language in allowed_languages
        }

        if self.__source_language not in descriptions:
            self.__logger.warning(f"You should have a 'Description' in info.json that matches your source language: {self.__source_language}")
            return
        source_desc = descriptions[self.__source_language]

        for target_language in self.__target_languages:
            if target_language in descriptions and descriptions[target_language] != '':
                self.__logger.info(f"Description for {target_language} already translated, skipping")
                continue
            self.__logger.info(f"Translating info.json description to {target_language}")
            descriptions[target_language] = self.translate_with_deepl(source_desc, target_language)

        self.__info_json_content['description'] = descriptions

    @Throttle(seconds=0.5)
    def translate_with_deepl(self, text: str, target_language: str) -> str:
        if self.__deepl_client is None:
            return ''

        self.__logger.debug(f"call deepl to translate {text} in {target_language}")
        self.__api_call_counter += 1
        result = self.__deepl_client.translate_text(
            text,
            source_lang=LANGUAGES_TO_DEEPL[self.__source_language],
            target_lang=LANGUAGES_TO_DEEPL[target_language],
            preserve_formatting=True,
            context='home automation',
            glossary=self.__glossary,
            model_type='prefer_quality_optimized'
        )
        if not isinstance(result, deepl.TextResult):
            self.__logger.error(f"Unexpected result type: {type(result)}")
            return ''

        return result.text

    def get_plugin_translations(self):
        self.__logger.info("Read plugin translations file...")
        self._get_translations_from_json_files(self.__plugin_root/TRANSLATIONS_FILES_PATH)

    def get_core_translations(self):
        if not self.__core_root.exists():
            raise RuntimeError(f"Path {self.__core_root.as_posix()} does not exist")

        self.__logger.info("Read core translations file...")
        self._get_translations_from_json_files(self.__core_root/TRANSLATIONS_FILES_PATH)

    def _get_translations_from_json_files(self, dir: Path):
        for language in self.__target_languages:
            file = dir/f"{language}.json"
            if not file.exists():
                self.__logger.info(f"file {file.as_posix()} not found !?")
                continue
            try:
                data = json.loads(file.read_text(encoding="UTF-8"))
                for path in data:
                    for text in data[path]:
                        self.__existing_translations.add_translation(language, text, data[path][text])
            except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
                self.__logger.error(f"Error while reading {file.as_posix()}: {e}")

    def write_plugin_translations(self):
        self.__logger.info("Write translations files...")

        translation_path = self.__plugin_root/TRANSLATIONS_FILES_PATH
        translation_path.mkdir(parents=True, exist_ok=True)

        for target_language in self.__target_languages:
            if target_language == self.__source_language and not self.__generate_source_language_translations:
                continue

            translation_file = translation_path/f"{target_language}.json"

            language_result = {}
            for path, file in self.__files.items():
                prompts = file.get_prompts_and_translation(target_language, self.__include_empty_translation)
                if len(prompts) > 0:
                    language_result[path] = prompts

            if (len(language_result) > 0):
                self.__logger.info(f"Writing {translation_file.as_posix()}")
                translation_file.write_text(json.dumps(language_result, ensure_ascii=False, sort_keys=True, indent=4).replace('/', r'\/'), encoding="UTF-8")
            else:
                self.__logger.info(f"No translations for {target_language}, skipping file")
