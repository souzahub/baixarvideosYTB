@echo off
setlocal
set TASK_NAME=BaixaYoutubeServer
set PORT=5000
set RULE_NAME=BaixaYoutube_HTTP_%PORT%

schtasks /Query /TN %TASK_NAME% >nul 2>&1
if %errorlevel%==0 (
  schtasks /Delete /TN %TASK_NAME% /F
  echo Tarefa removida: %TASK_NAME%
) else (
  echo Tarefa nao encontrada: %TASK_NAME%
)

netsh advfirewall firewall delete rule name="%RULE_NAME%" >nul 2>&1

endlocal
}
