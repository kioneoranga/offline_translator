# Traducteur hors ligne EN ⇄ FR (Windows)

Python 3.11/3.12 · PySide6 · CTranslate2 (OPUS-MT) · SQLite. Aucun appel réseau après le premier téléchargement des modèles.

## Lancer en développement
    python -m venv .venv && .venv\Scripts\activate
    pip install -r requirements.txt
    python run.py            # premier lancement : téléchargement des modèles (~300 Mo)

## Raccourcis (modifiables dans ⚙)
- `Ctrl+Shift+D` : traduit le texte sélectionné dans n'importe quelle application (popup près du curseur)
- `Ctrl+Shift+T` : ouvre la fenêtre principale

## Dictionnaire (optionnel)
    python tools/build_dictionary.py kaikki-English.jsonl kaikki-French.jsonl -o data/dictionary.db

## Modèles sans internet / meilleure qualité
Copier un dossier de modèle CTranslate2 (model.bin, config.json, source.spm, target.spm, vocabulaire) dans
`models/opus-mt-en-fr` et `models/opus-mt-fr-en`, ou `python tools/convert_models.py [--big]`.

## Packaging
    Double-cliquer sur CREER_EXE.bat   (ou .\build.ps1)  -> dist\OfflineTranslator\OfflineTranslator.exe

## Tests
    python -m unittest discover tests
