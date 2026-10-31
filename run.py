"""Point d'entrée (dev et PyInstaller)."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "src"))

from otranslate.app import main  # noqa: E402

if __name__ == "__main__":
    main()
