@echo off
title ComptaFlow - Terminal
color 0B

cd /d "%~dp0"

echo.
echo  ========================================================
echo             ComptaFlow - Terminal interactif
echo  --------------------------------------------------------
echo    Commandes utiles :
echo      docker compose ps                  - statut
echo      docker compose logs -f             - logs temps reel
echo      docker compose exec api bash       - shell API
echo      docker compose exec db psql -U compta -d comptaflow
echo      docker compose exec api alembic upgrade head
echo.
echo    Raccourcis projet :
echo      start.bat / stop.bat / restart.bat
echo      logs.bat / status.bat / migrate.bat / clean.bat
echo  ========================================================
echo.

cmd /k
