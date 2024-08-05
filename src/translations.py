from prompt import Prompt


class Translations():

    def __init__(self) -> None:
        self._translation: dict[str, Prompt] = {}

    def add_translation(self, language, text, translation):
        if translation == text:
            # not an actual translation, do not keep it
            return

        if text not in self._translation:
            # new text, save it with current translation
            new_prompt = Prompt(text)
            new_prompt.setTranslation(language, translation)
            self._translation[text] = new_prompt
        else:
            existing_translation = self._translation[text].getTranslation(language)
            if existing_translation == text :
                # not yet translate, save this one
                self._translation[text].setTranslation(language, translation)
            elif existing_translation != translation:
                print(f"2 differents translations in previous files for '{text}': '{existing_translation}' <> '{translation}'")
            else:
                pass #all fine, we found twice the same text and same translation

    def __contains__(self, text):
        return text in self._translation

    def getTranslations(self, text):
        return self._translation[text].getTranslations() if text in self._translation else {}