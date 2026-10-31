"""Chemins de l'application — tout vit à côté de l'exécutable (mode portable)."""
from __future__ import annotations

import sys
from pathlib import Path


def app_dir() -> Path:
    if getattr(sys, "frozen", False):          # PyInstaller
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]  # racine du projet en dev


APP_DIR = app_dir()
MODELS_DIR = APP_DIR / "models"
DATA_DIR = APP_DIR / "data"


def ensure_dirs() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
