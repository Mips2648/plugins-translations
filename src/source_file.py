
import inspect
from pathlib import Path
import re
import sys

from prompt import Prompt

class SourceFile(object):

    def __init__ (self, file: Path):
        self._file = file
        self._prompts: dict[str, Prompt] = {}

    def get_prompts(self):
        return self._prompts

    def __add_prompt(self, text: str, existing_translations: dict[str, Prompt]):
        if text not in self._prompts:
            self._prompts[text] = Prompt(text)
            if text in existing_translations:
                self._prompts[text].setTranslations(existing_translations[text].getTranslations())

    def search_prompts(self, existing_translations: dict[str, Prompt]):
        patern___ = re.compile(r'__\s*\(\s*((?P<delim>["\'])(?P<texte>.*?)(?P=delim))\s*,\s*\S+\s*\)')
        try:
            content = self._file.read_text(encoding="UTF-8")
            # with (open(self.get_absolute_path(), "r")) as f:
            #     content = f.read()
        except Exception as ex:
            info = inspect.currentframe()
            print (ex, "( at line" , info.f_lineno , ")")
            sys.exit(1)

        # Debug ("        Recherche {{..}}\n")
        for txt in re.findall("{{(.*?)}}", content):
            if len(txt) != 0:
                # Verbose ("        " + txt)
                self.__add_prompt(txt, existing_translations)
            else:
                Warning (f"ATTENTION, il y a un texte de longueur 0 dans le fichier <{self._file.as_posix()}>")

        if self._file.suffix == ".php":
            # Debug ('        Recherche __("...",__FILE__)\n')
            for match in patern___.finditer(content):
                texte = match.group('texte')
                delim = match.group('delim')
                regex = r'(^' + delim + r')|([^\\]' + delim + r')'
                # Verbose ("        " + texte)
                if re.search(regex,texte):
                    print("====  Délimineur de début et fin de chaîne trouvé dans le texte !!!")
                    print(f"      Fichier: {self._file.as_uri()}")
                    print(f"      texte  : {texte}")
                else:
                    self.__add_prompt(texte, existing_translations)

    def get_prompts_and_translation(self, language) -> dict[str, str]:
        result = {}
        for prompt in self._prompts.values():
            result[prompt.getText()] = prompt.getTranslation(language)

        return result
