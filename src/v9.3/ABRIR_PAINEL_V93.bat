@echo off
cd /d "%~dp0"
if exist PAINEL_V93.html (start "" "PAINEL_V93.html") else (echo Execute INICIAR_V93 primeiro.)
pause
