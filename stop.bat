@echo off
title ComptaFlow - Arret
color 0E

echo.
echo  ========================================================
echo           ComptaFlow - Arret des services
echo  ========================================================
echo.

cd /d "%~dp0"
docker compose down

if errorlevel 1 (
    color 0C
    echo  [ERREUR] Probleme lors de l'arret
    pause
    exit /b 1
)

color 0A
echo.
echo  [OK] Tous les services arretes
echo.
timeout /t 3
