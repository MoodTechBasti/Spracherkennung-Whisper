# 🎙️ Professionelle Spracherkennung mit Whisper

## 📋 Übersicht

Eine hochoptimierte Spracherkennung für Windows mit **Faster-Whisper**, die speziell für Ihren **Intel i5-7200U mit 16GB RAM** konfiguriert wurde.

## ⚡ Hauptfunktionen

### 🎯 **Auto-Paste**
- Text wird **automatisch** dort eingefügt, wo der Cursor gerade ist
- Zusätzlich immer in der Zwischenablage gespeichert
- Funktioniert in allen Programmen (Word, Browser, Editor, etc.)

### 🌙 **Dark Mode Interface**
- Augenschonendes dunkles Design
- Kompaktes Fenster (280x120 Pixel)
- Positioniert sich rechts unten
- 95% Transparenz für dezente Präsenz

### 🎵 **AIMP Integration**
- Automatische Lautstärkereduktion auf **7%** während Aufnahme
- Sanftes Fade-In (1 Sekunde) nach Aufnahme
- Musik läuft unterbrechungsfrei weiter

### ⌨️ **Globale Hotkeys**
- **STRG + Leertaste** - Funktioniert überall (auch in CMD/PowerShell)
- **STRG + SHIFT + R** - Alternative
- **F9** - Fallback-Hotkey

## 🚀 Verwendung

### **FAST MEDIUM** (Empfohlen - Beste Genauigkeit)
```
Doppelklick auf: faster_medium.bat
```
- Genauigkeit: ⭐⭐⭐⭐⭐
- Geschwindigkeit: ~2 Sekunden für 30s Audio
- RAM: ~3GB

### **FAST SMALL** (Schnellste Option)
```
Doppelklick auf: faster_small.bat
```
- Genauigkeit: ⭐⭐⭐⭐
- Geschwindigkeit: ~1 Sekunde für 30s Audio
- RAM: ~1.5GB

## 📦 Installation (einmalig)

```
Doppelklick auf: install_all.bat
```

Installiert alle benötigten Komponenten:
- `faster-whisper` - CPU-optimierte Spracherkennung
- `keyboard` - Globale Hotkeys
- `pyautogui` - Auto-Paste Funktion
- `pycaw` - AIMP Lautstärkekontrolle
- `psutil` - System-Monitoring

## 🔧 Aktuelle Einstellungen

| Einstellung | Wert | Beschreibung |
|------------|------|--------------|
| **Modell** | medium-int8 / small-int8 | INT8-quantisiert für CPU |
| **Sprache** | Deutsch | Multilinguale Modelle |
| **Max. Aufnahme** | 120 Sekunden | 2 Minuten Maximum |
| **AIMP Lautstärke** | 7% | Während Aufnahme |
| **Fade-Dauer** | 1 Sekunde | Sanfter Übergang |
| **Fenster-Position** | Rechts unten | 300px vom Rand |
| **Dark Mode** | Aktiviert | #1e1e1e Hintergrund |
| **Auto-Paste** | Aktiviert | STRG+V automatisch |

## 💻 Workflow

1. **Start**: Doppelklick auf `faster_medium.bat` oder `faster_small.bat`
2. **Aufnahme starten**: STRG + Leertaste
3. **Sprechen**: Bis zu 2 Minuten
4. **Aufnahme beenden**: STRG + Leertaste
5. **Ergebnis**: Text erscheint automatisch wo der Cursor ist

## 📂 Dateien im Projekt

| Datei | Beschreibung |
|-------|--------------|
| `spracherkennung_faster.py` | Hauptprogramm mit allen Features |
| `faster_medium.bat` | Startet MEDIUM Modell (genauer) |
| `faster_small.bat` | Startet SMALL Modell (schneller) |
| `install_all.bat` | Installiert alle Abhängigkeiten |
| `README.md` | Diese Dokumentation |

## 🎨 GUI-Anzeigen

| Anzeige | Bedeutung |
|---------|-----------|
| "Bereit" | Wartet auf Hotkey |
| "● REC" | Nimmt auf (rot) |
| "⚙ Verarbeitung..." | Transkribiert |
| "✅ Text eingefügt" | Erfolgreich eingefügt |

## ⚙️ Anpassungen (in spracherkennung_faster.py)

### AIMP Lautstärke ändern (Zeile 157):
```python
self.reduce_volume_percent = 0.07  # 7% (Standard)
```

### Fade-Geschwindigkeit (Zeile 158-159):
```python
self.fade_duration = 1.0   # 1 Sekunde
self.fade_steps = 20        # Anzahl Schritte
```

### Fenster-Position (Zeile 348-349):
```python
margin_right = 20   # Rand von rechts
margin_bottom = 80  # Rand unten (für Taskbar)
```

## ❓ Fehlerbehebung

### Hotkey funktioniert nicht:
- Als Administrator starten
- Alternative nutzen: F9 oder STRG+SHIFT+R

### Auto-Paste funktioniert nicht:
- Text ist trotzdem in Zwischenablage (STRG+V)
- Prüfen: `pip list | findstr pyautogui`

### AIMP wird nicht erkannt:
- AIMP muss vor der Spracherkennung laufen
- Funktioniert auch ohne AIMP (nur ohne Lautstärkeregelung)

### Erkennt Englisch statt Deutsch:
- Modelle sind korrekt auf Deutsch eingestellt
- Bei Problemen: Deutlicher sprechen

## 🏆 Optimiert für Ihren PC

- **CPU**: Intel i5-7200U (2 Kerne, 4 Threads)
- **RAM**: 16 GB
- **Betriebssystem**: Windows 10/11
- **Optimierungen**: INT8-Quantisierung, CPU-Threading, VAD

## 📱 Desktop-Verknüpfungen

Kopieren Sie `faster_medium.bat` und `faster_small.bat` auf den Desktop für schnellen Zugriff.

---

**Version 2.0** - Mit Dark Mode, Auto-Paste & AIMP Integration
Entwickelt mit Claude Code Assistant 🤖