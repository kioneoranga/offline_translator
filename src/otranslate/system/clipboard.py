"""Capture du texte sélectionné dans n'importe quelle application (Windows, ctypes pur).

Principe : attendre que l'utilisateur relâche les modificateurs du raccourci (sinon l'appli cible
recevrait Ctrl+Shift+C), simuler Ctrl+C avec SendInput, détecter le changement du presse-papiers via
GetClipboardSequenceNumber, lire le texte puis restaurer l'ancien contenu texte.
"""
from __future__ import annotations

import ctypes
import time
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_SHIFT, VK_CONTROL, VK_MENU, VK_LWIN, VK_RWIN, VK_C = 0x10, 0x11, 0x12, 0x5B, 0x5C, 0x43
_MODIFIERS = (VK_SHIFT, VK_CONTROL, VK_MENU, VK_LWIN, VK_RWIN)

ULONG_PTR = ctypes.c_size_t


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class MOUSEINPUT(ctypes.Structure):  # nécessaire pour que l'union ait la bonne taille (40 octets en x64)
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUT_UNION)]


user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL
user32.CloseClipboard.restype = wintypes.BOOL
user32.EmptyClipboard.restype = wintypes.BOOL
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.GetClipboardData.restype = wintypes.HANDLE
user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
user32.SetClipboardData.restype = wintypes.HANDLE
user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
user32.IsClipboardFormatAvailable.restype = wintypes.BOOL
user32.GetClipboardSequenceNumber.restype = wintypes.DWORD
kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalUnlock.restype = wintypes.BOOL


# ------------------------------------------------------------------ clipboard
def _open(retries: int = 10) -> bool:
    for _ in range(retries):
        if user32.OpenClipboard(None):
            return True
        time.sleep(0.01)
    return False


def get_text() -> str | None:
    if not user32.IsClipboardFormatAvailable(CF_UNICODETEXT) or not _open():
        return None
    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return None
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return None
        try:
            return ctypes.wstring_at(ptr)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def set_text(text: str) -> bool:
    data = (text + "\0").encode("utf-16-le")
    if not _open():
        return False
    try:
        user32.EmptyClipboard()
        handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
        if not handle:
            return False
        ptr = kernel32.GlobalLock(handle)
        ctypes.memmove(ptr, data, len(data))
        kernel32.GlobalUnlock(handle)
        return bool(user32.SetClipboardData(CF_UNICODETEXT, handle))
    finally:
        user32.CloseClipboard()


# ------------------------------------------------------------------ key injection
def _send(events: list[tuple[int, bool]]) -> None:
    arr = (INPUT * len(events))()
    for i, (vk, down) in enumerate(events):
        arr[i].type = INPUT_KEYBOARD
        arr[i].ki = KEYBDINPUT(vk, 0, 0 if down else KEYEVENTF_KEYUP, 0, 0)
    user32.SendInput(len(events), arr, ctypes.sizeof(INPUT))


def _wait_modifiers_released(timeout: float = 0.6) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not any(user32.GetAsyncKeyState(vk) & 0x8000 for vk in _MODIFIERS):
            return
        time.sleep(0.01)
    # l'utilisateur maintient encore une touche : on force le relâchement logique
    _send([(vk, False) for vk in _MODIFIERS if user32.GetAsyncKeyState(vk) & 0x8000])


def capture_selection(timeout: float = 0.6) -> str | None:
    """Texte sélectionné dans la fenêtre au premier plan, ou None."""
    _wait_modifiers_released()
    seq0 = user32.GetClipboardSequenceNumber()
    previous = get_text()
    _send([(VK_CONTROL, True), (VK_C, True), (VK_C, False), (VK_CONTROL, False)])
    deadline = time.monotonic() + timeout
    while user32.GetClipboardSequenceNumber() == seq0:
        if time.monotonic() > deadline:
            return None                      # rien n'a été copié : pas de sélection
        time.sleep(0.015)
    time.sleep(0.02)
    text = get_text()
    if previous is not None:
        set_text(previous)                   # restaure l'ancien contenu (texte uniquement)
    return text
