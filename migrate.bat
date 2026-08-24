@echo off
title ComptaFlow - Migrations
color 0B

cd /d "%~dp0"

echo.
echo  ========================================================
echo           ComptaFlow - Migrations Alembic
echo  ========================================================
echo.
echo   [1] Upgrade head (appliquer les migrations)
echo   [2] Autogenerate (creer nouvelle migration)
echo   [3] Historique
echo   [4] Downgrade -1 (revenir en arriere)
echo   [5] Reset complet de la DB  [DANGER]
echo   [0] Quitter
echo.
set /p c="Choix : "

if "%c%"=="1" docker compose exec api alembic upgrade head
if "%c%"=="2" (
    set /p m="Message : "
    docker compose exec api alembic revision --autogenerate -m "%m%"
)
if "%c%"=="3" docker compose exec api alembic history
if "%c%"=="4" docker compose exec api alembic downgrade -1
if "%c%"=="5" (
    set /p ok="Tapez OUI pour effacer la DB : "
    if "%ok%"=="OUI" (
        docker compose down -v
        docker compose up -d
        timeout /t 8 >nul
        docker compose exec api alembic upgrade head
        echo  [OK] DB reinitialisee
    )
)
echo.
pause
