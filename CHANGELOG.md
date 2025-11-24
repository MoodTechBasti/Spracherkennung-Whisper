# Changelog

Alle wichtigen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/).

## [2.0.0] - 2025-01-24

### Hinzugefügt
- **Dark Mode Interface** mit augenschonendem Design (#1e1e1e Hintergrund)
- **Auto-Paste Funktionalität** - Text wird automatisch dort eingefügt, wo der Cursor ist
- **AIMP Integration** mit intelligenter Lautstärkeregelung:
  - Automatische Reduktion auf 7% während Aufnahme
  - Sanftes Fade-In (1 Sekunde) nach Aufnahme
  - Musik läuft unterbrechungsfrei weiter
- **Globale Hotkeys** mit `keyboard` library:
  - STRG + Leertaste (funktioniert überall, auch in CMD/PowerShell)
  - STRG + SHIFT + R als Alternative
  - F9 als Fallback
- **Comprehensive Logging System**:
  - Rotating File Handler (max 5MB pro Datei)
  - Console und File Logging
  - Thread-sichere Exception Handling
- **Performance Optimierungen**:
  - INT8-Quantisierung für CPU-Modelle
  - Garbage Collection für besseres Memory-Management
  - Thread-Synchronisation für Stabilität
  - VAD (Voice Activity Detection) Filter
- **UI Verbesserungen**:
  - Kompaktes Fenster (280x120 Pixel)
  - Positionierung rechts unten mit Taskbar-Kompensation
  - 95% Transparenz für dezente Präsenz
  - Live Recording-Indikator mit "● REC" Anzeige
  - Performance-Label mit Verarbeitungszeit
- **Multi-Model Support**:
  - tiny-int8, base-int8, small-int8, medium-int8
  - Fallback-Mechanismus bei Modell-Ladefehlern
- **Robuste Fehlerbehandlung**:
  - Globaler Exception Handler
  - Thread Exception Handler
  - Detailliertes Fehler-Logging mit Stack Traces

### Geändert
- **Multilinguale Modelle** statt English-only (.en entfernt)
- Spracheinstellung auf Deutsch (`language="de"`)
- Maximale Aufnahmedauer auf 120 Sekunden erhöht
- CPU-Thread-Anzahl auf 2 optimiert (für i5-7200U)
- Verbesserte Textbereinigung mit Füllwörter-Entfernung
- Statusanzeigen mit Unicode-Icons (🎤, ✅, ❌, ⚙)

### Technische Details
- **System-Anforderungen**:
  - CPU: Intel i5-7200U (2 Kerne, 4 Threads)
  - RAM: 16 GB
  - OS: Windows 10/11
  - Python: 3.8+
- **Audio-Einstellungen**:
  - Sample Rate: 16 kHz
  - Channels: Mono
  - Format: paInt16
  - Chunk Size: 1024
- **Dependencies**:
  - faster-whisper 1.0.3
  - pyaudio 0.2.14
  - keyboard 0.13.5
  - pyautogui 0.9.54
  - pycaw für Windows Audio API
  - psutil für System-Monitoring

### Behoben
- Stream-Schließungs-Fehler beim Shutdown
- Double-Trigger bei Hotkey-Events (suppress=True)
- Speicherlecks durch besseres Thread-Management
- AIMP-Erkennung präzisiert (nur aimp.exe, nicht andere Prozesse)
- Fenster-Positionierung für verschiedene Bildschirmauflösungen

## [1.0.0] - Initial Release

### Hinzugefügt
- Grundlegende Spracherkennung mit Faster-Whisper
- Simple GUI mit tkinter
- Hotkey-Support mit pynput
- Zwischenablage-Integration
- Basic Audio-Aufnahme und -Verarbeitung

---

**Legende:**
- `Hinzugefügt` für neue Features
- `Geändert` für Änderungen an bestehenden Features
- `Entfernt` für entfernte Features
- `Behoben` für Bugfixes
- `Sicherheit` für Security-relevante Änderungen
