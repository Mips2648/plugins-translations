from prompt import Prompt


class Translations():

    def __init__(self) -> None:
        self._translation: dict[str, Prompt] = {}

    def add_translation(self, language, text, new_translation):
        if new_translation == text:
            # not an actual translation, do not keep it
            return

        if text not in self._translation:
            # new text, save it with current translation
            new_prompt = Prompt(text)
            new_prompt.setTranslation(language, new_translation)
            self._translation[text] = new_prompt
        elif not self._translation[text].hasTranslation():
            # not yet translate, save this one
            self._translation[text].setTranslation(language, new_translation)
        elif self._translation[text].getTranslation(language) != new_translation:
            print(f"2 differents translations for '{text}', keeping first one: '{self._translation[text].getTranslation(language)}' <> '{new_translation}'")
        else:
            pass #all fine, we found twice the same text and same translation

    def __contains__(self, text):
        return text in self._translation

    def getTranslations(self, text):
        return self._translation[text].getTranslations() if text in self._translation else {}