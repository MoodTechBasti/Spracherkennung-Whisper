@echo off
REM ===================================================
REM FAST MEDIUM - Beste Genauigkeit
REM Desktop-Verknüpfung für Spracherkennung
REM ===================================================

REM Wechsle zum Programmverzeichnis
cd /d "C:\Users\User\Desktop\Spracherkennung"

REM Minimiere das CMD-Fenster
if not DEFINED IS_MINIMIZED set IS_MINIMIZED=1 && start "" /min "%~dpnx0" %* && exit

REM Starte die Spracherkennung
echo.
echo ===================================================
echo FAST MEDIUM - Professionelle Spracherkennung
echo.
echo Features:
echo - Dark Mode Interface
echo - Auto-Paste (Text automatisch einfügen)
echo - AIMP auf 7%% während Aufnahme
echo - Globale Hotkeys: STRG+Leertaste
echo.
echo Modell: MEDIUM (Beste Genauigkeit)
echo ===================================================
echo.
python spracherkennung_faster.py --model medium-int8

REM Falls Python nicht gefunden wird
if errorlevel 1 (
    echo.
    echo FEHLER: Python nicht gefunden!
    echo Bitte Python installieren oder PATH prüfen
    pause
)