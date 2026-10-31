from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields

from .paths import DATA_DIR

CONFIG_FILE = DATA_DIR / "config.json"


@dataclass
class Config:
    theme: str = "system"                 # system | dark | light
    hotkey_translate: str = "ctrl+shift+d"
    hotkey_open: str = "ctrl+shift+t"
    live_translate: bool = True
    history_enabled: bool = True
    unwrap_lines: bool = True             # recolle les retours à la ligne « PDF »
    beam_size: int = 4
    cpu_threads: int = 0                  # 0 = automatique
    fallback_source: str = "en"           # langue supposée si la détection hésite
    first_run_done: bool = False

    @classmethod
    def load(cls) -> "Config":
        try:
            data = json.loads(CONFIG_FILE.read_text("utf-8"))
        except (OSError, ValueError):
            return cls()
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    def save(self) -> None:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(asdict(self), indent=2), "utf-8")
