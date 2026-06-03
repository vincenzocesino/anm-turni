@echo off
title ANM Turni — Installazione
echo.
echo  ================================================
echo   ANM Turni - Installazione (una volta sola)
echo  ================================================
echo.

:: Controlla se Python e' installato
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERRORE: Python non trovato sul computer.
    echo.
    echo  Installa Python da: https://www.python.org/downloads/
    echo  Scarica la versione 3.11 o superiore.
    echo  IMPORTANTE: spunta "Add Python to PATH" durante l'installazione.
    echo.
    start https://www.python.org/downloads/
    pause
    exit /b 1
)

echo  Python trovato. Installo le librerie necessarie...
echo.
pip install streamlit pdfplumber pandas openpyxl --quiet

if errorlevel 1 (
    echo.
    echo  ERRORE durante l'installazione delle librerie.
    echo  Contatta Vincenzo al 351 920 9525
    pause
    exit /b 1
)

echo.
echo  ================================================
echo   Installazione completata con successo!
echo   Da oggi usa solo AVVIA.bat per aprire l'app.
echo  ================================================
echo.
pause
