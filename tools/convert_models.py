"""Plan B / montée en qualité : convertit soi-même les modèles OPUS-MT en CTranslate2 (int8).

  pip install transformers torch sentencepiece ctranslate2
  python tools/convert_models.py            # modèles standard (~75 Mo chacun)
  python tools/convert_models.py --big      # opus-mt-tc-big : meilleure qualité, ~300 Mo chacun

Les sorties vont dans models/opus-mt-en-fr et models/opus-mt-fr-en (mêmes noms que le téléchargeur).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--big", action="store_true")
    args = ap.parse_args()
    for pair in ("en-fr", "fr-en"):
        src = f"Helsinki-NLP/opus-mt-tc-big-{pair}" if args.big else f"Helsinki-NLP/opus-mt-{pair}"
        out = ROOT / "models" / f"opus-mt-{pair}"
        cmd = ["ct2-transformers-converter", "--model", src, "--output_dir", str(out),
               "--quantization", "int8", "--copy_files", "source.spm", "target.spm", "--force"]
        print(">", " ".join(cmd))
        if subprocess.call(cmd) != 0:
            sys.exit(f"Échec de la conversion de {src}")


if __name__ == "__main__":
    main()
