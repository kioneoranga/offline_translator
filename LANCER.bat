@echo off
cd /d "%~dp0"
if not exist .venv ( echo Lancez d'abord CREER_EXE.bat ou suivez le README. & pause & exit /b 1 )
call .venv\Scripts\activate.bat
start "" pythonw run.py
