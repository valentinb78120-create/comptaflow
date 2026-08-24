@echo off
title ComptaFlow - Frontend dev
color 0E

cd /d "%~dp0frontend"

REM Node est parfois absent du PATH juste apres installation
where node >nul 2>&1
if errorlevel 1 set "PATH=%ProgramFiles%\nodejs;%PATH%"

where node >nul 2>&1
if errorlevel 1 (
    color 0C
    echo  [ERREUR] Node.js introuvable. Installe-le : winget install OpenJS.NodeJS.LTS
    pause
    exit /b 1
)

if not exist "node_modules" (
    echo  [INFO] Installation des dependances npm...
    call npm install
)

echo.
echo  Lancement Vite sur http://localhost:5173  (Ctrl+C pour arreter)
echo.
call npm run dev
