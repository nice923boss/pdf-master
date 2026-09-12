@echo off
cd /d "%~dp0"

set "PY_HOME="
for /f "delims=" %%i in ('py -3.12 -c "import sys,os;print(os.path.dirname(sys.executable))" 2^>nul') do set "PY_HOME=%%i"
if not defined PY_HOME (
    for /f "delims=" %%i in ('python -c "import sys,os;print(os.path.dirname(sys.executable))" 2^>nul') do set "PY_HOME=%%i"
)

if not defined PY_HOME (
    echo [x] 找不到 Python，請先安裝 Python 3.12 並加入 PATH。
    pause
    exit /b 1
)

if not exist "%PY_HOME%\pythonw.exe" (
    echo [x] 此路徑沒有 pythonw.exe：%PY_HOME%
    pause
    exit /b 1
)

echo [i] Python 路徑：%PY_HOME%
copy /y "%PY_HOME%\pythonw.exe" "pythonw_pdfmaster.exe"
copy /y "%PY_HOME%\python312.dll" "python312.dll"
copy /y "%PY_HOME%\python3.dll" "python3.dll"
echo [v] 已建立三個本機執行檔。
pause
