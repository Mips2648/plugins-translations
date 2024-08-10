
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

    def _add_prompt(self, text: str):
        if text not in self._prompts:
            self._prompts[text] = Prompt(text)

    def search_prompts(self):
        pattern = re.compile(r'__\s*\(\s*((?P<delim>["\'])(?P<texte>.*?)(?P=delim))\s*,\s*\S+\s*\)')
        try:
            content = self._file.read_text(encoding="UTF-8")
        except Exception as ex:
            info = inspect.currentframe()
            print (ex, "( at line" , info.f_lineno , ")")
            sys.exit(1)

        for txt in re.findall("{{(.*?)}}", content):
            if len(txt) != 0:
                self._add_prompt(txt)
            else:
                Warning (f"ATTENTION, il y a un texte de longueur 0 dans le fichier <{self._file.as_posix()}>")

        if self._file.suffix == ".php":
            for match in pattern.finditer(content):
                text = match.group('texte')
                delim = match.group('delim')
                regex = r'(^' + delim + r')|([^\\]' + delim + r')'
                if re.search(regex,text):
                    print("====  Délimineur de début et fin de chaîne trouvé dans le texte !!!")
                    print(f"      Fichier: {self._file.as_uri()}")
                    print(f"      texte  : {text}")
                else:
                    self._add_prompt(text)

    def get_prompts_and_translation(self, language) -> dict[str, str]:
        result = {}
        for prompt in self._prompts.values():
            # if prompt.has_translation(language):
            result[prompt.get_text()] = prompt.get_translation(language)

        return result
