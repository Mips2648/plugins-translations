import json
import os
import hashlib
from pathlib import Path
import pytest

import plugintranslations.translator as translator_module
from plugintranslations.translator import PluginTranslator
from plugintranslations.prompt import Prompt
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
        os.environ['deepl_api_key'] = 'fake-key'

        glossary_file = Path(translator_module.__file__).with_name(f"{FR_FR}_glossary.json")
        glossary_entries = json.loads(glossary_file.read_text(encoding="UTF-8"))
        md5_hash = hashlib.md5(
            json.dumps(glossary_entries, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
        ).hexdigest()

        class FakeGlossary:
            def __init__(self, name: str, dictionaries=None):
                self.name = name
                self.glossary_id = f"id-{name}"
                self.dictionaries = dictionaries or []

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
                return FakeGlossary(name, dictionaries)

        monkeypatch.setattr(translator_module.deepl, 'DeepLClient', FakeClient)

        test_translate = PluginTranslator(current_working_dir)

        client = test_translate.deepl_client

        assert isinstance(client, FakeClient)
        assert client.deleted == ['obsolete-glossary']
        assert len(client.created) == 1
        assert client.created[0][0] == md5_hash
        assert len(client.created[0][1]) == 2
        glossary = getattr(test_translate, '_PluginTranslator__glossary')
        assert glossary.name == md5_hash

    def test_do_translate_batches_missing_translations_by_language(self, current_working_dir, monkeypatch):
        os.environ['deepl_api_key'] = 'fake-key'

        class FakeTextResult:
            def __init__(self, text: str):
                self.text = text

        class FakeClient:
            def __init__(self, auth_key: str):
                self.auth_key = auth_key
                self.calls = []

            def list_multilingual_glossaries(self):
                return []

            def create_multilingual_glossary(self, name, dictionaries):
                return None

            def translate_text(self, texts, **kwargs):
                self.calls.append((list(texts), kwargs['target_lang']))
                return [FakeTextResult(f"{kwargs['target_lang']}::{text}") for text in texts]

        class FakeSourceFile:
            def __init__(self, *texts: str):
                self._prompts = {text: Prompt(text) for text in texts}

            def get_prompts(self):
                return self._prompts

        monkeypatch.setattr(translator_module.deepl, 'DeepLClient', FakeClient)
        monkeypatch.setattr(translator_module.deepl, 'TextResult', FakeTextResult)

        test_translate = PluginTranslator(current_working_dir)
        setattr(test_translate, '_PluginTranslator__files', {
            'plugins/fake_plugin/file1.php': FakeSourceFile('Bonjour', 'Au revoir'),
            'plugins/fake_plugin/file2.php': FakeSourceFile('Merci'),
        })

        test_translate.do_translate()

        client = test_translate.deepl_client

        assert isinstance(client, FakeClient)
        assert len(client.calls) == 3
        assert client.calls == [
            (['Bonjour', 'Au revoir', 'Merci'], 'EN-US'),
            (['Bonjour', 'Au revoir', 'Merci'], 'ES'),
            (['Bonjour', 'Au revoir', 'Merci'], 'DE'),
        ]

        for source_file in getattr(test_translate, '_PluginTranslator__files').values():
            for prompt in source_file.get_prompts().values():
                assert prompt.get_translation(FR_FR) == prompt.get_text()
                assert prompt.get_translation(EN_US) == f"EN-US::{prompt.get_text()}"
                assert prompt.get_translation(ES_ES) == f"ES::{prompt.get_text()}"
                assert prompt.get_translation(DE_DE) == f"DE::{prompt.get_text()}"

        assert getattr(test_translate, '_PluginTranslator__api_call_counter') == 3

    def test_translate_with_deepl_batch_omits_glossary_for_missing_target_language(self, current_working_dir, monkeypatch):
        os.environ['deepl_api_key'] = 'fake-key'
        os.environ[INPUT_TARGET_LANGUAGES] = f'{EN_US},{ES_ES}'

        class FakeTextResult:
            def __init__(self, text: str):
                self.text = text

        class FakeGlossary:
            def __init__(self, name: str, dictionaries=None):
                self.name = name
                self.dictionaries = dictionaries or []

        class FakeClient:
            def __init__(self, auth_key: str):
                self.auth_key = auth_key
                self.calls = []

            def list_multilingual_glossaries(self):
                return []

            def create_multilingual_glossary(self, name, dictionaries):
                return FakeGlossary(name, dictionaries)

            def translate_text(self, texts, **kwargs):
                self.calls.append(kwargs)
                return [FakeTextResult(text) for text in texts]

        monkeypatch.setattr(translator_module.deepl, 'DeepLClient', FakeClient)
        monkeypatch.setattr(translator_module.deepl, 'TextResult', FakeTextResult)

        test_translate = PluginTranslator(current_working_dir)
        _ = test_translate.deepl_client

        test_translate.translate_with_deepl_batch(['Bonjour'], EN_US)
        test_translate.translate_with_deepl_batch(['Bonjour'], ES_ES)

        client = test_translate.deepl_client

        assert isinstance(client, FakeClient)
        assert len(client.calls) == 2
        assert client.calls[0]['glossary'] is not None
        assert client.calls[1]['glossary'] is None
