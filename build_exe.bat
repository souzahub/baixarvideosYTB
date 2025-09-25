@echo off
setlocal

REM Caminho base do projeto (pasta atual)
set BASE=%~dp0
cd /d "%BASE%"

REM Cria e ativa venv local
if not exist .venv (
  py -3 -m venv .venv
)
call .venv\Scripts\activate.bat

REM Atualiza pip e instala dependências
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller

REM Remove build/ e dist/ antigos
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

REM Monta comando do PyInstaller
set EXTRA_DATA=--add-data "intalacao\ffmpeg\bin;intalacao/ffmpeg/bin"

pyinstaller --noconfirm --noconsole ^
  --onefile ^
  %EXTRA_DATA% ^
  --name BaixaYoutube ^
  downloader.py

if errorlevel 1 (
  echo Build falhou.
  exit /b 1
)

REM Copia pasta downloads para ao lado do EXE (se existir)
if not exist dist\downloads mkdir dist\downloads

echo.
echo Build concluido. EXE em: %BASE%dist\BaixaYoutube.exe
endlocal
