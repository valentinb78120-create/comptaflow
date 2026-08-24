@echo off
title ComptaFlow - Redemarrage
color 0E

cd /d "%~dp0"

echo.
echo  ========================================================
echo           ComptaFlow - Redemarrage
echo  ========================================================
echo.

docker compose down
docker compose up -d --build

color 0A
echo.
echo  [OK] Services redemarres
echo    Frontend : http://localhost:5173
echo    API      : http://localhost:8000/docs
echo.
timeout /t 3
