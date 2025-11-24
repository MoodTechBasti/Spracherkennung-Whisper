@echo off
REM ===================================================
REM FAST SMALL - Schnellste Option
REM Desktop-Verknüpfung für Spracherkennung
REM ===================================================

REM Wechsle zum Programmverzeichnis
cd /d "C:\Users\User\Desktop\Spracherkennung"

REM Minimiere das CMD-Fenster
if not DEFINED IS_MINIMIZED set IS_MINIMIZED=1 && start "" /min "%~dpnx0" %* && exit

REM Starte die Spracherkennung
echo.
echo ===================================================
echo FAST SMALL - Schnellste Spracherkennung
echo.
echo Features:
echo - Dark Mode Interface
echo - Auto-Paste (Text automatisch einfügen)
echo - AIMP auf 7%% während Aufnahme
echo - Globale Hotkeys: STRG+Leertaste
echo.
echo Modell: SMALL (Schnellste Verarbeitung)
echo ===================================================
echo.
python spracherkennung_faster.py --model small-int8

REM Falls Python nicht gefunden wird
if errorlevel 1 (
    echo.
    echo FEHLER: Python nicht gefunden!
    echo Bitte Python installieren oder PATH prüfen
    pause
)