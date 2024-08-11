EN_US = "en_US"
FR_FR = "fr_FR"
ES_ES = "es_ES"
DE_DE = "de_DE"

DEFAULT_TARGET_LANGUAGES = [
    EN_US,
    ES_ES,
    DE_DE
]

ALL_LANGUAGES = [
    FR_FR,
    EN_US,
    ES_ES,
    DE_DE
]

LANGUAGES_TO_DEEPL = {
    FR_FR: 'FR',
    EN_US: 'EN-US',
    ES_ES: 'ES',
    DE_DE: 'DE'
}

PLUGIN_DIRS = ['core', 'desktop', 'plugin_info']
FILE_EXTS = ['.php', '.js', '.json']

PLUGIN_INFO_JSON = 'plugin_info/info.json'

PLUGIN_ROOT = 'plugin'
CORE_ROOT = 'jeedom_core'

INPUT_SOURCE_LANGUAGE = 'source_language'
INPUT_DEEPL_API_KEY = 'deepl_api_key'
INPUT_INCLUDE_EMPTY_TRANSLATION = 'include_empty_translation'
INPUT_USE_CORE_TRANSLATIONS = 'use_core_translations'
INPUT_GENERATE_SOURCE_LANGUAGE_TRANSLATIONS = 'generate_source_language_translations'