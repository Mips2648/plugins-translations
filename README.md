# Mips's plugin-translations GitHub action

A GitHub action to automatically generate translation files for your plugins and optionally automatically translated texts if all languages you want.

## How it works

The idea is to trigger a new workflow with this Github action on each push to a branch on your repository (dev or beta branch, as you prefer).
This workflow will:

- build a list of existing translations based on existing json translation files (i18n) that exist in your plugin, if any;
- enrich this list with existing translation in jeedom Core (in order to get a good base);
- parse your source files (`.php`, `.json` and `.js`) located in sub-directories `core`, `desktop` and `plugin_info` (and sub-directories of these of course);
- translate all texts found with the help of previous existing translations found (from plugin & Jeedom core);
- optional: call [deepl api](https://www.deepl.com) to translate automatically remaining texts. Please create a free account on <https://www.deepl.com> for this, it's free for 500.000 chars by month which should be more than enough for 50 new plugins or more by month;
- generate new translations files (i18n) for selected target languages;
- adapt info.json file with list of target languages if needed;
- Automatically create a branch called `translations` and push changes on it (or adapt files if branch exists already);
- create a pull request that you need to approve to commit the changes on the base branch (from where the workflow ran). So you can run it without risk, workflow will not changes anything without your final review!

> Tip
>
> Do not forget to quickly review the PR before pushing new changes in your branch otherwise the action will redo all the woks already done but not yet reviewed because the branch `translations` is not used as a source for translations. It is not an issue as such, it will works without problem but it will consume twice deepl (free) credits for the same translations.

## Quick start

### Permissions settings

First, you must grant Github actions write permission and allow to create pull requests. To do this, go to your repository *settings*, *Actions* tab and then *General*.

![actions_general](actions_general.png)

On the bottom of the page you will see corresponding permissions settings:

![permissions](permissions.png)

Do not forget to save changes.

### Basic workflow

Create a ´.github/workflows/translations.yml´ file in your repository and put the following content:

```YAML
name: translate

on:
  workflow_dispatch:
  push:
    branches:
      - beta

jobs:
  auto-translate:
    runs-on: ubuntu-latest
    steps:
      - uses: Mips2648/plugins-translations@main
```

Save it and commit in your beta branch.

It will immediately run and generate translations file for your plugin for following language: de_DE, en_US & es_ES, push changes, if any, in a new branch `translations` of your repository and create a pull request that you can review and eventually validate. It couldn't be easier ;-)

## Optional input parameters

If you use a compatible editor like vscode, when editing the workflow you should be able to get auto-completion for options.
As any github action, you should use the `with:` keyword for optional input parameter as follow:

```YAML
name: translate

on:
  workflow_dispatch:
  push:
    branches:
      - beta

jobs:
  auto-translate:
    runs-on: ubuntu-latest
    steps:
      - uses: Mips2648/plugins-translations@main
        with:
          deepl_api_key: ${{ secrets.DEEPL_API_KEY }}
          include_empty_translation: false
          target_languages: "en_US,es_ES,de_DE,it_IT,pt_PT"
```

All inputs are **optional**. If not set, defaults values will be used.

| Name | Description | type | Default |
| --- | --- | --- | --- |
| `source_language` | Source language for translations, must be one of the following value: `fr_FR`, `en_US`, `es_ES`, `de_DE`, `it_IT`, `pt_PT` *(incompatible with use_core_translations)* | `string` | `fr_FR` |
| `target_languages` | Target languages for translations, must be a list of comma separated languages without spaces (allowed languages are: `fr_FR`, `en_US`, `es_ES`, `de_DE`, `it_IT`, `pt_PT`) | `string` | `en_US,es_ES,de_DE` |
| `deepl_api_key` | [deepl API KEY](https://www.deepl.com) for automatic translation; If provided, missing translations will be automatically translated using deepl API. Please create a free account on <https://www.deepl.com> | `string` | '' |
| `include_empty_translation` | Include prompts without translation language files | `boolean` | `true` |
| `use_core_translations` | Tool will use translations from Jeedom core for missing plugin translations (before calling deepl api if available) *(only if source_language is fr_FR)* | `boolean` | `true` |
| `generate_source_language_translations` | The translation file corresponding to the source language will be generated (which is useless) | `boolean` | `false` |
| `debug` | Set log level to debug | `boolean` | `false` |

### source_language

Currently not compatible with core translations but should be ok regarding existing plugin translations and automatic translation with help of *deepl api*

### deepl_api_key

If provided, all your prompts will be translated!

> Warning
>
> Do not put your key in clear in the workflow but save it as actions secrets.

Go to you repository *Settings*, then *Secrets and variables* tab and finally *Actions*.
Click on *New repository secret*, choose a name (e.g. DEEPL_API_KEY but could be anything) and store the API key you will find in your deepl account.

![secrets](secrets.png)

Then to use it in the wokflow you can use following syntax `${{ secrets.DEEPL_API_KEY }}`, where `DEEPL_API_KEY` is the name of the secret.

Example:

```YAML
        with:
          deepl_api_key: ${{ secrets.DEEPL_API_KEY }}
```

### include_empty_translation

This is preferable to have this params deactivated but if you want to be able to manually translate, then you need this.
This param is useless if you provide a valid *deepl API key* because all your translations will be completed (unless you reach the limit)

### use_core_translations

It is relevant to use core translations by default for coherence in user interface but if you don't trust or don't like them, you can deactivate this feature.

If you select a *source_language* different than `fr_FR`, this setting will be forced to false.

### generate_source_language_translations

Why would you use this feature? It is completely useless :-)

If set to `true`, the file `fr_FR.json`, e.g., will be generated if source language is `fr_FR` but it is useless because the translation always equals the key.

### debug

Because issues happen.

## Glossaries

Some words needs to be have a given translations. e.g. *commande* in french could mean *order* or *command*, *type* in french could mean *kind* or *type* or even *guy* and in the context of Jeedom and home automation, we should force specific translation to avoid weird result.
To achieve this, we have the concept of glossaries which will contain these specific edge cases. You don't have to manage anything within your workflow for that, this Github action is taking care for you.

But it might happen that you face a case not yet foreseen, so please find below the procedure to add new word in the glossary.

In the `src` folder you will find one json file by source language corresponding to the glossary for that language. The naming convention is `[lang]_glossary.json`; e.g. `fr_FR_glossary.json`.
This file must contain one key by target language and in each, one key by "word" => "translation".
The words must be in the singular form, lower case and preferably in alphabetical order to easily spot them.

Example for *fr_FR* glossary:

```JSON
{
    "en_US": {
        "commande": "command",
        "type": "type",
        "pièce": "room"
    }
}
```

I've almost no knowledge in others languages than FR and EN, so the only glossary that I could start is the one for *fr_FR* to *en_US*.
So, please, if you know typical mistakes that automatic translations tools do when translating to DE, ES, IT or PT, do not hesitate to submit a pull-request.
