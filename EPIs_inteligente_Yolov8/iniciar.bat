@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Ambiente virtual nao encontrado. Criando .venv...
  py -m venv .venv
  if errorlevel 1 python -m venv .venv
)
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Falha ao instalar dependencias. Verifique a mensagem acima.
  pause
  exit /b 1
)
echo.
echo Abrindo EPIs Inteligente em http://127.0.0.1:8000
start "" /min cmd /c "timeout /t 3 /nobreak ^>nul ^& start http://127.0.0.1:8000"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
