@echo off
title ComptaFlow - Statut
color 0B

cd /d "%~dp0"

echo.
echo  ========================================================
echo               ComptaFlow - Statut
echo  ========================================================
echo.
docker compose ps
echo.
echo  -- Health check API --
curl -s http://localhost:8000/health
echo.
echo.
pause
