# -*- mode: python ; coding: utf-8 -*-
# Build : pyinstaller --noconfirm --clean OfflineTranslator.spec
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []
for pkg in ("ctranslate2", "sentencepiece"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ["run.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + ["otranslate.system.clipboard", "otranslate.system.hotkeys"],
    excludes=["tkinter", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtQml",
              "PySide6.QtQuick", "PySide6.Qt3DCore", "PySide6.QtMultimedia", "PySide6.QtCharts",
              "PySide6.QtDataVisualization", "PySide6.QtPdf", "PySide6.QtSql", "PySide6.QtTest"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="OfflineTranslator",
          console=False, upx=False)          # icon="assets/app.ico" si vous en ajoutez une
coll = COLLECT(exe, a.binaries, a.datas, name="OfflineTranslator", upx=False)
