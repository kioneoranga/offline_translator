# Build Windows : .\build.ps1   (Python 3.11 ou 3.12 requis)
$ErrorActionPreference = "Stop"
if (-not (Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\pip install -r requirements.txt pyinstaller
.\.venv\Scripts\pyinstaller --noconfirm --clean OfflineTranslator.spec

$out = "dist\OfflineTranslator"
New-Item -ItemType Directory -Force "$out\models", "$out\data" | Out-Null
# Livraison 100 % hors ligne : on embarque les modèles déjà présents dans models\
Get-ChildItem models -Directory -ErrorAction SilentlyContinue | Copy-Item -Destination "$out\models" -Recurse -Force
if (Test-Path data\dictionary.db) { Copy-Item data\dictionary.db "$out\data" -Force }
Write-Host "OK -> $out\OfflineTranslator.exe"
