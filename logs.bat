@echo off
title ComptaFlow - Logs
color 0B

cd /d "%~dp0"

echo.
echo  Logs temps reel - Ctrl+C pour quitter
echo.
docker compose logs -f --tail=80
