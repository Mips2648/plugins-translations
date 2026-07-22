import json
import os
import hashlib
from pathlib import Path
import pytest

import plugintranslations.translator as translator_module
from plugintranslations.translator import PluginTranslator
from plugintranslations.consts import (
    EN_US,
    FR_FR,
    ES_ES,
    DE_DE,
    PLUGIN_ROOT,
    INPUT_SOURCE_LANGUAGE,
    INPUT_TARGET_LANGUAGES,
    INPUT_INCLUDE_EMPTY_TRANSLATION,
    INPUT_USE_CORE_TRANSLATIONS,
    INPUT_GENERATE_SOURCE_LANGUAGE_TRANSLATIONS,
    INPUT_DEBUG,
    TRANSLATIONS_FILES_PATH,
)


class TestPluginTranslator():
    # Arrange
    @pytest.fixture(scope="session", autouse=True)
    def current_working_dir(self, tmp_path_factory) -> Path:
        _cwd = tmp_path_factory.mktemp("plugin_root")
        return _cwd

    @pytest.fixture(autouse=True)
    def setup_os_env(self):
        os.environ[INPUT_SOURCE_LANGUAGE] = FR_FR
        os.environ[INPUT_TARGET_LANGUAGES] = f'{EN_US},{ES_ES},{DE_DE}'
        os.environ[INPUT_INCLUDE_EMPTY_TRANSLATION] = 'False'
        os.environ[INPUT_USE_CORE_TRANSLATIONS] = 'False'
        os.environ[INPUT_GENERATE_SOURCE_LANGUAGE_TRANSLATIONS] = 'False'
        os.environ[INPUT_DEBUG] = 'True'

    @pytest.fixture(autouse=True)
    def setup_info_json(self, current_working_dir: Path):
        self.__plugin_root = current_working_dir/PLUGIN_ROOT
        plugin_info_root = current_working_dir/PLUGIN_ROOT/"plugin_info"
        plugin_info_root.mkdir(parents=True, exist_ok=True)
        assert plugin_info_root.exists()

        info_json_content = {}
        info_json_content['language'] = [FR_FR, EN_US, ES_ES, DE_DE]
        info_json_content['id'] = 'fake_plugin'

        info_json_file = plugin_info_root/'info.json'
        info_json_file.write_text(json.dumps(info_json_content, ensure_ascii=False, indent='\t'), encoding="UTF-8")

    def test_init(self, current_working_dir):
        self._test_translate = PluginTranslator(current_working_dir)
        assert self._test_translate is not None
        assert isinstance(self._test_translate, PluginTranslator)

    def test_get_plugin_translations(self, current_working_dir):
        # Arrange
        self._test_translate = PluginTranslator(current_working_dir)

        translation_path = self.__plugin_root/TRANSLATIONS_FILES_PATH
        translation_path.mkdir(parents=True, exist_ok=True)
        translation_file = translation_path/f"{EN_US}.json"
        translation_file.touch()

        # Act
        self._test_translate.get_plugin_translations()
        # Assert
        assert 1

    def test_create_single_multilingual_glossary(self, current_working_dir, monkeypatch):
        os.environ['DEEPL_API_KEY'] = 'fake-key'

        glossary_file = Path(translator_module.__file__).with_name(f"{FR_FR}_glossary.json")
        glossary_text = glossary_file.read_text(encoding="UTF-8")
        md5_hash = hashlib.md5(glossary_text.encode('utf-8')).hexdigest()

        class FakeGlossary:
            def __init__(self, name: str):
                self.name = name
                self.glossary_id = f"id-{name}"
                self.dictionaries = []

        class FakeClient:
            def __init__(self, auth_key: str):
                self.auth_key = auth_key
                self.deleted = []
                self.created = []

            def list_multilingual_glossaries(self):
                return [FakeGlossary('obsolete-glossary')]

            def delete_multilingual_glossary(self, glossary):
                self.deleted.append(glossary.name)

            def create_multilingual_glossary(self, name, dictionaries):
                self.created.append((name, dictionaries))
                return FakeGlossary(name)

        monkeypatch.setattr(translator_module.deepl, 'DeepLClient', FakeClient)

        test_translate = PluginTranslator(current_working_dir)

        client = test_translate.deepl_client

        assert isinstance(client, FakeClient)
        assert client.deleted == ['obsolete-glossary']
        assert len(client.created) == 1
        assert client.created[0][0] == md5_hash
        assert len(client.created[0][1]) == 2
        assert test_translate._PluginTranslator__glossary.name == md5_hash
