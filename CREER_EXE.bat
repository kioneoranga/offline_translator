@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Creation de l'executable (double-clic, rien d'autre a taper) ===

where py >nul 2>nul && (set PY=py -3) || (set PY=python)
%PY% --version >nul 2>nul || (
  echo Python est introuvable. Installez Python 3.12 depuis python.org en cochant "Add python.exe to PATH", puis relancez ce fichier.
  pause & exit /b 1
)

if not exist .venv ( %PY% -m venv .venv || goto :err )
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip || goto :err
pip install -r requirements.txt pyinstaller || goto :err
pyinstaller --noconfirm --clean OfflineTranslator.spec || goto :err

if not exist dist\OfflineTranslator\models mkdir dist\OfflineTranslator\models
if not exist dist\OfflineTranslator\data mkdir dist\OfflineTranslator\data
for /d %%D in (models\*) do xcopy /E /I /Y "%%D" "dist\OfflineTranslator\models\%%~nxD" >nul
if exist data\dictionary.db copy /Y data\dictionary.db dist\OfflineTranslator\data >nul

echo.
echo === TERMINE ===
echo Votre application : dist\OfflineTranslator\OfflineTranslator.exe
explorer dist\OfflineTranslator
pause
exit /b 0

:err
echo.
echo Une erreur est survenue. Copiez le message ci-dessus et envoyez-le moi.
pause
exit /b 1
