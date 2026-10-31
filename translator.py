"""Moteur NMT hors ligne : CTranslate2 (CPU, int8) + SentencePiece, modèles OPUS-MT."""
from __future__ import annotations

import threading

from . import segmenter
from .models import REGISTRY, is_installed, model_dir


class ModelNotInstalled(RuntimeError):
    def __init__(self, pair: str):
        super().__init__(f"model_missing:{pair}")
        self.pair = pair


class _Engine:
    def __init__(self, path, threads: int):
        import ctranslate2
        import sentencepiece as spm
        self.translator = ctranslate2.Translator(
            str(path), device="cpu", compute_type="int8", inter_threads=1, intra_threads=threads
        )
        self.sp_src = spm.SentencePieceProcessor(model_file=str(path / "source.spm"))
        self.sp_tgt = spm.SentencePieceProcessor(model_file=str(path / "target.spm"))

    def run(self, sentences: list[str], beam: int) -> list[str]:
        tokens = [self.sp_src.encode(s, out_type=str) for s in sentences]
        results = self.translator.translate_batch(
            tokens, beam_size=beam, max_batch_size=32, max_decoding_length=256
        )
        return [self.sp_tgt.decode(r.hypotheses[0]) for r in results]


class TranslationService:
    def __init__(self, cfg):
        self.cfg = cfg
        self._engines: dict[str, _Engine] = {}
        self._lock = threading.Lock()

    def reset(self) -> None:
        with self._lock:
            self._engines.clear()

    def available(self, pair: str) -> bool:
        return pair in REGISTRY and is_installed(REGISTRY[pair])

    def _engine(self, pair: str) -> _Engine:
        with self._lock:
            if pair not in self._engines:
                if not self.available(pair):
                    raise ModelNotInstalled(pair)
                self._engines[pair] = _Engine(model_dir(REGISTRY[pair]), self.cfg.cpu_threads)
            return self._engines[pair]

    def translate(self, text: str, src: str, tgt: str) -> str:
        engine = self._engine(f"{src}-{tgt}")
        parts = segmenter.split(segmenter.normalize(text, self.cfg.unwrap_lines))
        sentences = [v for is_text, v in parts if is_text]
        if not sentences:
            return ""
        translated = iter(engine.run(sentences, self.cfg.beam_size))
        return "".join(next(translated) if is_text else v for is_text, v in parts)
