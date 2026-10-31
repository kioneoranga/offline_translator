"""Raccourcis globaux via RegisterHotKey (API Win32) dans un thread dédié avec boucle de messages.
Pas de hook clavier bas niveau : fiable, léger, et peu suspect pour les antivirus."""
from __future__ import annotations

import ctypes
import threading
from ctypes import wintypes
from typing import Callable

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, MOD_NOREPEAT = 0x1, 0x2, 0x4, 0x8, 0x4000
WM_HOTKEY, WM_QUIT, WM_USER, PM_NOREMOVE = 0x0312, 0x0012, 0x0400, 0

user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
user32.RegisterHotKey.restype = wintypes.BOOL
user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.GetMessageW.restype = ctypes.c_int
user32.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT,
                                wintypes.UINT, wintypes.UINT]
user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.VkKeyScanW.argtypes = [wintypes.WCHAR]
user32.VkKeyScanW.restype = ctypes.c_short

_MODS = {"alt": MOD_ALT, "ctrl": MOD_CONTROL, "control": MOD_CONTROL, "shift": MOD_SHIFT,
         "win": MOD_WIN, "meta": MOD_WIN}
_NAMED = {"space": 0x20, "enter": 0x0D, "return": 0x0D, "tab": 0x09, "esc": 0x1B, "escape": 0x1B,
          "insert": 0x2D, "delete": 0x2E, "home": 0x24, "end": 0x23, "pgup": 0x21, "pgdown": 0x22,
          "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28}


def parse_hotkey(spec: str) -> tuple[int, int]:
    """'ctrl+shift+d' -> (modificateurs, code de touche virtuelle)"""
    parts = [p.strip().lower() for p in spec.split("+") if p.strip()]
    if len(parts) < 2:
        raise ValueError(f"Raccourci invalide : {spec!r} (au moins un modificateur + une touche)")
    mods = 0
    for p in parts[:-1]:
        mods |= _MODS[p]
    key = parts[-1]
    if key in _NAMED:
        vk = _NAMED[key]
    elif key.startswith("f") and key[1:].isdigit() and 1 <= int(key[1:]) <= 24:
        vk = 0x70 + int(key[1:]) - 1
    elif len(key) == 1 and key.isalnum():
        vk = ord(key.upper())
    elif len(key) == 1:
        vk = user32.VkKeyScanW(key) & 0xFF
    else:
        raise ValueError(f"Touche inconnue : {key!r}")
    return mods, vk


class HotkeyManager:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._tid = 0
        self.failed: list[str] = []

    def start(self, bindings: list[tuple[str, Callable[[], None]]]) -> list[str]:
        """Enregistre [(raccourci, callback)]. Retourne les raccourcis refusés (déjà pris, invalides)."""
        self.stop()
        ready = threading.Event()
        self._thread = threading.Thread(target=self._run, args=(bindings, ready), daemon=True, name="hotkeys")
        self._thread.start()
        ready.wait(2)
        return list(self.failed)

    def stop(self) -> None:
        if self._thread and self._thread.is_alive():
            user32.PostThreadMessageW(self._tid, WM_QUIT, 0, 0)
            self._thread.join(timeout=2)
        self._thread = None

    def _run(self, bindings, ready: threading.Event) -> None:
        self._tid = kernel32.GetCurrentThreadId()
        msg = wintypes.MSG()
        user32.PeekMessageW(ctypes.byref(msg), None, WM_USER, WM_USER, PM_NOREMOVE)  # crée la file de messages
        callbacks: dict[int, Callable[[], None]] = {}
        self.failed = []
        for i, (spec, cb) in enumerate(bindings, start=1):
            try:
                mods, vk = parse_hotkey(spec)
                ok = user32.RegisterHotKey(None, i, mods | MOD_NOREPEAT, vk)
            except (ValueError, KeyError):
                ok = False
            if ok:
                callbacks[i] = cb
            else:
                self.failed.append(spec)
        ready.set()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == WM_HOTKEY and msg.wParam in callbacks:
                try:
                    callbacks[msg.wParam]()
                except Exception:  # noqa: BLE001 — ne jamais tuer la boucle
                    pass
        for i in callbacks:
            user32.UnregisterHotKey(None, i)
