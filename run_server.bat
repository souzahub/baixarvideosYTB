@echo off
setlocal
set BASE=%~dp0
cd /d "%BASE%"

set PORT=5000
set RULE_NAME=BaixaYoutube_HTTP_%PORT%
REM Defina 1 para desabilitar verificacao SSL (ultimo recurso)
set USE_INSECURE_SSL=0

REM Abre regra de firewall para a porta se não existir
netsh advfirewall firewall show rule name="%RULE_NAME%" >nul 2>&1
if errorlevel 1 (
  echo Criando regra de firewall para porta %PORT%...
  netsh advfirewall firewall add rule name="%RULE_NAME%" dir=in action=allow protocol=TCP localport=%PORT% >nul
) else (
  echo Regra de firewall ja existe: %RULE_NAME%
)

REM Executa via Python local ou EXE se existir
if exist BaixaYoutube.exe (
  set HOST=0.0.0.0
  set PORT=%PORT%
  if "%USE_INSECURE_SSL%"=="1" set DISABLE_CERT_VERIFY=1
  BaixaYoutube.exe
) else (
  if exist .venv\Scripts\python.exe (
    call .venv\Scripts\activate.bat
    set HOST=0.0.0.0
    set PORT=%PORT%
    if "%USE_INSECURE_SSL%"=="1" set DISABLE_CERT_VERIFY=1
    python downloader.py
  ) else (
    set HOST=0.0.0.0
    set PORT=%PORT%
    if "%USE_INSECURE_SSL%"=="1" set DISABLE_CERT_VERIFY=1
    py -3 downloader.py
  )
)

endlocal
