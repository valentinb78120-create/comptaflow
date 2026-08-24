@echo off
title ComptaFlow - Nettoyage
color 0C

cd /d "%~dp0"

echo.
echo  [!] ATTENTION : suppression containers + volumes + images
echo      La DB et les uploads seront PERDUS
echo.
set /p ok="Tapez OUI pour confirmer : "
if not "%ok%"=="OUI" exit /b 0

docker compose down -v
for /f "tokens=*" %%i in ('docker images "comptaflow*" -q 2^>nul') do docker rmi -f %%i
docker system prune -f

color 0A
echo.
echo  [OK] Nettoyage termine
echo.
pause
