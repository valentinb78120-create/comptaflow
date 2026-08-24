@echo off
title ComptaFlow - Demarrage
color 0B

echo.
echo  ========================================================
echo            ComptaFlow - Lancement
echo     OCR Factures - Cabinets comptables FR
echo  ========================================================
echo.

cd /d "%~dp0"

REM --- Verification Docker ---
docker --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo  [ERREUR] Docker Desktop non installe ou non demarre.
    echo  Ouvre Docker Desktop et attends qu'il soit "Running", puis relance.
    echo.
    pause
    exit /b 1
)

REM --- Verification que le moteur Docker repond ---
docker info >nul 2>&1
if errorlevel 1 (
    color 0C
    echo  [ERREUR] Le moteur Docker ne repond pas.
    echo  Lance Docker Desktop et attends l'icone verte "Running".
    echo.
    pause
    exit /b 1
)

REM --- Creation .env si absent ---
if not exist "backend\.env" (
    if exist "backend\.env.example" (
        copy "backend\.env.example" "backend\.env" >nul
        echo  [INFO] .env cree depuis .env.example
        echo  [!] Edite backend\.env pour ajouter MISTRAL_API_KEY
        timeout /t 3 >nul
    )
)

echo  [1/4] Build + demarrage des containers Docker (db, redis, api, worker)...
docker compose up -d --build db redis api worker
if errorlevel 1 (
    color 0C
    echo  [ERREUR] Echec du demarrage Docker
    pause
    exit /b 1
)

echo.
echo  [2/4] Attente PostgreSQL (8s)...
timeout /t 8 >nul

echo.
echo  [3/4] Application des migrations Alembic...
docker compose exec -T api alembic upgrade head

echo.
echo  [4/4] Demarrage du frontend (fenetre separee)...
start "ComptaFlow Frontend" "%~dp0dev_frontend.bat"

echo.
color 0A
echo  ========================================================
echo                    DEMARRE
echo  --------------------------------------------------------
echo     Frontend   : http://localhost:5173
echo     API + Docs : http://localhost:8000/docs
echo     PostgreSQL : localhost:5432
echo     Redis      : localhost:6379
echo  ========================================================
echo.
timeout /t 2 >nul
start http://localhost:5173
start http://localhost:8000/docs

echo  Ouverture du navigateur...
echo  Les services tournent en arriere-plan. Pour arreter : stop.bat
echo.
timeout /t 5
