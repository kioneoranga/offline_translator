"""Registre des modèles CTranslate2 + téléchargeur avec progression (premier lancement uniquement)."""
from __future__ import annotations

import shutil
import threading
import zipfile
from dataclasses import dataclass
from typing import Callable

from ..paths import MODELS_DIR

RELEASE = "https://github.com/kioneoranga/offline_translator/releases/download/models-v1"
HEADERS = {"User-Agent": "OfflineTranslator/1.0"}


@dataclass(frozen=True)
class ModelSpec:
    pair: str       # "en-fr"
    dirname: str    # sous-dossier de models/ (et nom de l'archive publiée)

    @property
    def url(self) -> str:
        return f"{RELEASE}/{self.dirname}.zip"


REGISTRY: dict[str, ModelSpec] = {
    "en-fr": ModelSpec("en-fr", "opus-mt-en-fr"),
    "fr-en": ModelSpec("fr-en", "opus-mt-fr-en"),
}
REQUIRED = ("model.bin", "config.json", "source.spm", "target.spm")
VOCAB = ("shared_vocabulary.json", "shared_vocabulary.txt", "source_vocabulary.json", "source_vocabulary.txt")


class DownloadCancelled(Exception):
    pass


def model_dir(spec: ModelSpec):
    return MODELS_DIR / spec.dirname


def missing_files(spec: ModelSpec) -> list[str]:
    miss = [f for f in REQUIRED if not (model_dir(spec) / f).exists()]
    if not any((model_dir(spec) / f).exists() for f in VOCAB):      # CTranslate2 exige un vocabulaire
        miss.append("shared_vocabulary.json")
    return miss


def is_installed(spec: ModelSpec) -> bool:
    return not missing_files(spec)


def missing_models() -> list[ModelSpec]:
    return [s for s in REGISTRY.values() if not is_installed(s)]


def download_all(specs: list[ModelSpec], progress: Callable[[int, str], None],
                 cancel: threading.Event) -> None:
    """progress(permille_global, texte). Télécharge chaque archive .zip puis l'extrait dans models/."""
    import requests
    n = len(specs)
    tmpdir = MODELS_DIR / ".download"
    tmpdir.mkdir(parents=True, exist_ok=True)
    for i, spec in enumerate(specs):
        part = tmpdir / f"{spec.dirname}.zip.part"
        with requests.get(spec.url, headers=HEADERS, stream=True, timeout=30) as r:
            if r.status_code == 404:
                raise RuntimeError(f"Modèle introuvable : {spec.url}")
            r.raise_for_status()
            total = int(r.headers.get("Content-Length") or 0)
            done = 0
            with open(part, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    if cancel.is_set():
                        raise DownloadCancelled()
                    f.write(chunk)
                    done += len(chunk)
                    frac = done / total if total else 0.0
                    progress(int((i + 0.9 * frac) * 1000 / n),
                             f"{spec.dirname} — {done / 1e6:.0f} / {total / 1e6:.0f} Mo")
        progress(int((i + 0.9) * 1000 / n), f"Installation de {spec.dirname}…")
        with zipfile.ZipFile(part) as z:
            z.extractall(MODELS_DIR)
        part.unlink()
        absent = missing_files(spec)
        if absent:
            raise RuntimeError(f"Modèle {spec.pair} incomplet : fichiers manquants {', '.join(absent)}")
    shutil.rmtree(tmpdir, ignore_errors=True)
    progress(1000, "Terminé")
