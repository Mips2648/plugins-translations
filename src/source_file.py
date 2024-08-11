
from logging import Logger
from pathlib import Path
import re

from prompt import Prompt

class SourceFile(object):

    def __init__ (self, file: Path, logger: Logger):
        self._file = file
        self._logger = logger
        self._prompts: dict[str, Prompt] = {}

    def get_prompts(self):
        return self._prompts

    def _add_prompt(self, text: str):
        if text not in self._prompts:
            self._prompts[text] = Prompt(text)

    def search_prompts(self):
        content = self._file.read_text(encoding="UTF-8")
        for txt in re.findall("{{(.*?)}}", content):
            if len(txt) != 0:
                self._add_prompt(txt)
            else:
                self._logger.warning(f"There is an empty text in <{self._file.as_posix()}>")

        if self._file.suffix == ".php":
            pattern = re.compile(r'__\s*\(\s*((?P<delim>["\'])(?P<text>.*?)(?P=separator))\s*,\s*\S+\s*\)')
            for match in pattern.finditer(content):
                text = match.group('text')
                separator = match.group('separator')
                regex = r'(^' + separator + r')|([^\\]' + separator + r')'
                if re.search(regex,text):
                    self._logger.warning("====  String separator found in text !!!")
                    self._logger.warning(f"      Fichier: {self._file.as_uri()}")
                    self._logger.warning(f"      texte  : {text}")
                else:
                    self._add_prompt(text)

    def get_prompts_and_translation(self, language: str, include_empty_translation: bool = False) -> dict[str, str]:
        result = {}
        for prompt in self._prompts.values():
            if include_empty_translation or prompt.has_translation(language):
                result[prompt.get_text()] = prompt.get_translation(language)

        return result
