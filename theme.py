"""Intégration thème Windows : mode sombre système + barre de titre sombre (DWM)."""
from __future__ import annotations

import ctypes


def system_is_dark() -> bool:
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
            return winreg.QueryValueEx(k, "AppsUseLightTheme")[0] == 0
    except Exception:  # noqa: BLE001 — hors Windows ou clé absente
        return True


def set_titlebar_dark(hwnd: int, dark: bool) -> None:
    try:
        value = ctypes.c_int(1 if dark else 0)
        # 20 = DWMWA_USE_IMMERSIVE_DARK_MODE (Windows 10 2004+ / 11)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(ctypes.c_void_p(hwnd), 20, ctypes.byref(value), 4)
    except Exception:  # noqa: BLE001
        pass
