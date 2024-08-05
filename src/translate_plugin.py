import json
from pathlib import Path

from source_file import SourceFile
from consts import CORE_ROOT, LANGUAGES, PLUGIN_DIRS, PLUGIN_INFO_JSON
from translations import Translations

class TranslatePlugin():

    def __init__(self) -> None:
        self._plugin_root = Path.cwd()
        self._plugin_id: str
        self._plugin_name: str

        self._files: dict[str, SourceFile] = {}
        self._existing_translations = Translations()

        self._core_root = Path.cwd()/CORE_ROOT
        self._core_translations = Translations()

        self.__read_info_json()

    def start(self):
        self.get_plugin_translations()
        self.get_core_translations()
        self.find_prompts_in_all_files()
        self.do_translate()

        self.write_translations()

        self.__write_info_json()

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
        data['language'] = LANGUAGES
        info_json.write_text(json.dumps(data, ensure_ascii=False, sort_keys = True, indent= 4), encoding="UTF-8")

    def find_prompts_in_all_files(self):
        print("Find prompts in all plugin files")
        for dir in PLUGIN_DIRS:
            plugin_dir = self._plugin_root/dir
            for root, dirs, files in plugin_dir.walk():
                for dirname in dirs:
                    if root.name == "core" and dirname == 'i18n':
                        dirs.remove(dirname)
                    # for d in excludes:
                    #     if fnmatch.fnmatch(dirname, d):
                    #         dirs.remove(dirname)

                for fileName in files:
                    # for f in excludes:
                    #     if fnmatch.fnmatch(fileName, f):
                    #         continue
                    if fileName[-4:] == ".php" or fileName[-3:] == ".js":
                    #   or fileName[-5:] == ".json"
                    #   or fileName[-5:] == ".html"):
                        absolute_file_path = root/fileName
                        jeedom_file_path = absolute_file_path.relative_to(self._plugin_root)
                        jeedom_file_path = (f"plugins/{self._plugin_id}"/jeedom_file_path).as_posix()
                        print(f"    {jeedom_file_path}...")
                        self._files[jeedom_file_path] = SourceFile(absolute_file_path)
                        self._files[jeedom_file_path].search_prompts()

    def do_translate(self):
        print("Find existing translations...")
        for file in self._files.values():
            for prompt in file.get_prompts().values():
                if prompt.getText() in self._existing_translations:
                    tr = self._existing_translations.getTranslations(prompt.getText())
                    print(f"find translation for {prompt.getText()} => {tr}")
                    prompt.setTranslations(tr)


    def get_plugin_translations(self):
        print("Read plugin translations file...")

        self.get_translations_from_json_files(self._plugin_root)

    def get_core_translations(self):
        print("Read core translations file...")
        if not self._core_root.exists():
            raise ValueError(f"Path {self._core_root.as_posix()} does not exists")

        self.get_translations_from_json_files(self._core_root)

    def get_translations_from_json_files(self, root: Path):

        for language in LANGUAGES:
            file = root/f"core/i18n/{language}.json"
            if not file.exists():
                print(f"file {file.as_posix()} not found !?")
                continue

            data = json.loads(file.read_text(encoding="UTF-8"))
            for path in data:
                for text in data[path]:
                    self._existing_translations.add_translation(language, text, data[path][text])

    def write_translations(self):
        print("Ecriture du/des fichier(s) de traduction(s)...")
        for language in LANGUAGES:
            print(f"    Language: {language}...")

            translation_path = self._plugin_root/"core/i18n"
            translation_path.mkdir(parents=True, exist_ok=True)
            translation_file = translation_path/f"{language}.json"

            result = {}
            for path, file in self._files.items():
                result[path] = file.get_prompts_and_translation(language)

            print(f"Will dump {translation_file.as_posix()}")
            translation_file.write_text(json.dumps(result, ensure_ascii=False, sort_keys = True, indent= 4).replace('/', r'\/'), encoding="UTF-8")

if __name__ == "__main__":
    TranslatePlugin().start()