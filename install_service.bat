@echo off
setlocal
set BASE=%~dp0
cd /d "%BASE%"

set TASK_NAME=BaixaYoutubeServer
set PORT=5000

REM Cria um atalho via schtasks que inicia no logon
schtasks /Query /TN %TASK_NAME% >nul 2>&1
if %errorlevel%==0 (
  echo Tarefa ja existe: %TASK_NAME%
  goto :eof
)

if exist BaixaYoutube.exe (
  set CMD="%BASE%run_server.bat"
) else (
  set CMD="%BASE%run_server.bat"
)

schtasks /Create /SC ONLOGON /RL HIGHEST /TN %TASK_NAME% /TR %CMD%
if %errorlevel% neq 0 (
  echo Falha ao criar tarefa agendada. Tente como Administrador.
  exit /b 1
)

echo Tarefa criada: %TASK_NAME%
endlocal
