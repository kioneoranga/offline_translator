"""Registre des modèles CTranslate2 + téléchargeur avec progression (premier lancement uniquement)."""
from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import Callable

from ..paths import MODELS_DIR

HF = "https://huggingface.co"
HF_API = "https://huggingface.co/api/models"


@dataclass(frozen=True)
class ModelSpec:
    pair: str       # "en-fr"
    repo: str       # dépôt Hugging Face contenant un modèle déjà converti CTranslate2
    dirname: str    # sous-dossier de models/


REGISTRY: dict[str, ModelSpec] = {
    "en-fr": ModelSpec("en-fr", "gaudi/opus-mt-en-fr-ctranslate2", "opus-mt-en-fr"),
    "fr-en": ModelSpec("fr-en", "gaudi/opus-mt-fr-en-ctranslate2", "opus-mt-fr-en"),
}
REQUIRED = ("model.bin", "config.json", "source.spm", "target.spm")
OPTIONAL = ("shared_vocabulary.json", "shared_vocabulary.txt", "source_vocabulary.json",
            "target_vocabulary.json", "source_vocabulary.txt", "target_vocabulary.txt")
HEADERS = {"User-Agent": "OfflineTranslator/1.0"}


class DownloadCancelled(Exception):
    pass


def model_dir(spec: ModelSpec):
    return MODELS_DIR / spec.dirname


def missing_files(spec: ModelSpec) -> list[str]:
    miss = [f for f in REQUIRED if not (model_dir(spec) / f).exists()]
    if not any((model_dir(spec) / f).exists() for f in OPTIONAL):   # CTranslate2 exige un vocabulaire
        miss.append("shared_vocabulary.json")
    return miss


def is_installed(spec: ModelSpec) -> bool:
    return not missing_files(spec)


def missing_models() -> list[ModelSpec]:
    return [s for s in REGISTRY.values() if not is_installed(s)]


def _url(spec: ModelSpec, name: str) -> str:
    return f"{HF}/{spec.repo}/resolve/main/{name}"


def _probe(spec: ModelSpec, name: str, required: bool) -> int | None:
    """Taille du fichier distant (0 si inconnue) ; None si absent et facultatif."""
    import requests
    r = requests.head(_url(spec, name), headers=HEADERS, allow_redirects=True, timeout=30)
    if r.status_code == 404:
        if required:
            raise RuntimeError(f"Fichier introuvable sur Hugging Face : {spec.repo}/{name}")
        return None
    r.raise_for_status()
    return int(r.headers.get("Content-Length") or 0)


def download_all(specs: list[ModelSpec], progress: Callable[[int, int, str], None],
                 cancel: threading.Event) -> None:
    """progress(octets_faits, octets_total, fichier_courant).
    Les fichiers sont demandés par leur nom (pas de listing d'API, qui varie selon le stockage du dépôt)."""
    import requests
    plan: list[tuple[ModelSpec, str, int]] = []
    for spec in specs:
        for name in REQUIRED + OPTIONAL:
            size = _probe(spec, name, required=name in REQUIRED)
            if size is not None:
                plan.append((spec, name, size))
    total = sum(size for _, _, size in plan)
    done = 0
    for spec, name, size in plan:
        dest = model_dir(spec) / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and (size == 0 or dest.stat().st_size == size):
            done += size
            progress(done, total, name)
            continue
        tmp = dest.with_name(dest.name + ".part")
        with requests.get(_url(spec, name), headers=HEADERS, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    if cancel.is_set():
                        raise DownloadCancelled()
                    f.write(chunk)
                    done += len(chunk)
                    progress(done, max(total, done), name)
        os.replace(tmp, dest)
    for spec in specs:
        absent = missing_files(spec)
        if absent:
            raise RuntimeError(f"Modèle {spec.pair} incomplet : fichiers manquants {', '.join(absent)}")
