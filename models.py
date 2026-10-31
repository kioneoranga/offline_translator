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
_IGNORE = {".gitattributes", "README.md", "vocab.json", "tokenizer_config.json", "generation_config.json"}


class DownloadCancelled(Exception):
    pass


def model_dir(spec: ModelSpec):
    return MODELS_DIR / spec.dirname


def is_installed(spec: ModelSpec) -> bool:
    return all((model_dir(spec) / f).exists() for f in REQUIRED)


def missing_models() -> list[ModelSpec]:
    return [s for s in REGISTRY.values() if not is_installed(s)]


def _list_files(spec: ModelSpec) -> list[tuple[str, int]]:
    import requests
    r = requests.get(f"{HF_API}/{spec.repo}", params={"blobs": "true"}, timeout=30)
    r.raise_for_status()
    files = []
    for s in r.json().get("siblings", []):
        name = s["rfilename"]
        if "/" not in name and name not in _IGNORE:
            files.append((name, int(s.get("size") or 0)))
    return files


def download_all(specs: list[ModelSpec], progress: Callable[[int, int, str], None],
                 cancel: threading.Event) -> None:
    """progress(octets_faits, octets_total, fichier_courant)"""
    import requests
    plan = [(spec, name, size) for spec in specs for name, size in _list_files(spec)]
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
        with requests.get(f"{HF}/{spec.repo}/resolve/main/{name}", stream=True, timeout=30) as r:
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
        if not is_installed(spec):
            raise RuntimeError(f"Modèle {spec.pair} incomplet après téléchargement.")
