@echo off
echo Stopping PDF Master...
taskkill /f /im pythonw_pdfmaster.exe >nul 2>&1
echo Done.
timeout /t 1 >nul
