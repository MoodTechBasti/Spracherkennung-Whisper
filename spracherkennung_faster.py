#!/usr/bin/env python3
"""
Spracherkennung mit Faster-Whisper (CPU-optimiert)
Bessere Performance auf Intel i5-7200U mit 16GB RAM
"""

import sys
import pyaudio
import wave
import threading
import time
import pyperclip
import tkinter as tk
from tkinter import ttk
import os
import re
import argparse
import subprocess
import gc  # Garbage Collection für besseres Memory-Management
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Auto-Paste Funktionalität
try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
    pyautogui.PAUSE = 0.1  # Schnellere Reaktion
except ImportError:
    PYAUTOGUI_AVAILABLE = False

# Versuche bessere Hotkey-Bibliothek für globale Hotkeys
try:
    import keyboard as kb  # keyboard library für bessere globale Hotkeys
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
    # Fallback auf pynput
    from pynput import keyboard
    from pynput.keyboard import Key, Listener

# AIMP Lautstärke-Kontrolle
try:
    from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
    PYCAW_AVAILABLE = True
except ImportError:
    PYCAW_AVAILABLE = False
    print("⚠️ pycaw nicht installiert (für AIMP-Kontrolle). Optional: pip install pycaw")

# Faster-Whisper für bessere CPU Performance
try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False
    print("⚠️ Faster-Whisper nicht installiert. Installieren mit:")
    print("   pip install faster-whisper")

# Logging-Konfiguration
def setup_logging():
    """Richtet das Logging-System ein (Datei + Console)"""
    log_dir = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(log_dir, "spracherkennung.log")

    # Logger erstellen
    logger = logging.getLogger("Spracherkennung")
    logger.setLevel(logging.DEBUG)

    # Format für Log-Einträge
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(threadName)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Handler für Log-Datei (mit Rotation: max 5MB pro Datei, max 5 Dateien)
    try:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"⚠️ Fehler beim Erstellen der Log-Datei: {e}")

    # Handler für Console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.info("=" * 70)
    logger.info("Spracherkennung gestartet")
    logger.info(f"Log-Datei: {log_file}")
    logger.info("=" * 70)

    return logger

# Logger global verfügbar machen
logger = setup_logging()

def flush_logger():
    """Stellt sicher, dass alle Log-Einträge sofort geschrieben werden"""
    for handler in logger.handlers:
        handler.flush()

def handle_exception(exc_type, exc_value, exc_traceback):
    """Globaler Exception Handler - erfasst alle unkontrollierten Fehler"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.critical("=" * 70, exc_info=(exc_type, exc_value, exc_traceback))
    logger.critical(f"UNKONTROLLIERTER FEHLER: {exc_type.__name__}: {exc_value}")
    logger.critical("=" * 70)
    flush_logger()

# Installiere globalen Exception Handler
sys.excepthook = handle_exception

def handle_thread_exception(args):
    """Handler für Exceptions in Threads"""
    logger.critical("=" * 70)
    logger.critical(f"FEHLER IN THREAD '{args.thread.name}':")
    logger.critical(f"{args.exc_type.__name__}: {args.exc_value}")
    logger.critical("=" * 70, exc_info=(args.exc_type, args.exc_value, args.exc_traceback))
    flush_logger()

# Installiere Thread Exception Handler
threading.excepthook = handle_thread_exception

class OptimizedSpeechToTextApp:
    def __init__(self, model_size="small-int8"):
        self.is_recording = False
        self.audio_frames = []
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.model = None
        self.model_size = model_size
        self.root = None

        # Thread-Synchronisation für Stabilität
        self.recording_lock = threading.Lock()
        self.processing_lock = threading.Lock()
        self.is_processing = False

        # Thread-Referenzen für besseres Management
        self.recording_thread = None
        self.processing_thread = None

        # AIMP Kontrolle
        self.aimp_original_volume = None
        self.aimp_volume_interface = None
        self.reduce_volume_percent = 0.07  # Reduziere auf 7% während Aufnahme (noch leiser!)
        self.fade_duration = 1.0  # Fade-In Dauer in Sekunden
        self.fade_steps = 20  # Anzahl der Schritte für sanftes Fade

        # Audio settings
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.max_recording_time = 120  # 2 Minuten

        # Füllwörter zum Entfernen
        self.filler_words = [
            "ähm", "äh", "hm", "also", "sozusagen", "quasi", "gewissermaßen",
            "eigentlich", "praktisch", "halt", "irgendwie", "wohl", "mal"
        ]

        self.load_model()
        self.setup_gui()
        self.setup_hotkey()
        self.find_aimp()

    def load_model(self):
        """Lädt das Faster-Whisper Modell (CPU-optimiert)"""
        if not FASTER_WHISPER_AVAILABLE:
            logger.error("❌ Faster-Whisper nicht verfügbar")
            return

        model_info = {
            "tiny-int8": "Sehr schnell, INT8 quantisiert, ~39M",
            "base-int8": "Schnell, INT8 quantisiert, ~74M",
            "small-int8": "Ausgewogen, INT8 quantisiert, ~244M",
            "medium-int8": "Genauer, INT8 quantisiert, ~769M",
            "tiny": "Sehr schnell, ~39M Parameter",
            "base": "Schnell, ~74M Parameter",
            "small": "Ausgewogen, ~244M Parameter",
            "medium": "Genauer, ~769M Parameter",
            "large-v2": "Beste Genauigkeit, ~1550M Parameter"
        }

        # Model name mapping für faster-whisper (MULTILINGUAL!)
        model_mapping = {
            "tiny-int8": "tiny",      # Geändert: ohne .en für Deutsch!
            "base-int8": "base",      # Geändert: ohne .en für Deutsch!
            "small-int8": "small",    # Geändert: ohne .en für Deutsch!
            "medium-int8": "medium",  # Geändert: ohne .en für Deutsch!
            "tiny": "tiny",
            "base": "base",
            "small": "small",
            "medium": "medium",
            "large-v2": "large-v2"
        }

        logger.info(f"🔄 Lade Faster-Whisper {self.model_size} Modell...")
        if self.model_size in model_info:
            logger.info(f"   Info: {model_info[self.model_size]}")

        try:
            import psutil
            ram_gb = psutil.virtual_memory().total / (1024**3)
            available_gb = psutil.virtual_memory().available / (1024**3)
            logger.info(f"   System: {ram_gb:.1f}GB RAM total, {available_gb:.1f}GB verfügbar")
        except Exception as e:
            logger.debug(f"Fehler beim Abrufen von RAM-Informationen: {e}")

        try:
            actual_model = model_mapping.get(self.model_size, self.model_size)

            # INT8 Quantisierung für bessere CPU Performance
            # Für CPU: int8 bei quantisierten Modellen, sonst int8 (stabiler als float32)
            if "int8" in self.model_size:
                compute_type = "int8"
            else:
                # Auch bei nicht-quantisierten Modellen int8 verwenden für CPU-Stabilität
                compute_type = "int8"
                logger.info(f"   Hinweis: Verwende int8 für CPU-Stabilität (statt float16/float32)")

            self.model = WhisperModel(
                actual_model,
                device="cpu",
                compute_type=compute_type,
                num_workers=1,  # 1 Worker für stabile CPU-Nutzung
                cpu_threads=2   # 2 Threads für i5-7200U (verhindert Thrashing)
            )
            logger.info(f"✅ Modell {self.model_size} geladen (Compute: {compute_type})")

        except Exception as e:
            logger.error(f"❌ Fehler beim Laden des Modells: {e}", exc_info=True)
            logger.info("   Versuche kleineres Modell...")
            self.model_size = "tiny-int8"
            try:
                self.model = WhisperModel("tiny", device="cpu", compute_type="int8")
                logger.info(f"✅ Fallback auf {self.model_size} Modell erfolgreich")
            except Exception as e2:
                logger.critical(f"❌ Auch Fallback fehlgeschlagen: {e2}", exc_info=True)
                logger.error("   Mögliche Lösungen:")
                logger.error("   1. Stelle sicher, dass Faster-Whisper installiert ist")
                logger.error("   2. Prüfe die Internetverbindung (Models werden heruntergeladen)")
                logger.error("   3. Prüfe freien Speicherplatz auf der Festplatte")
                self.model = None

    def setup_gui(self):
        """Erstellt die Benutzeroberfläche im Dark Mode"""
        self.root = tk.Tk()
        self.root.title("Spracherkennung")

        # Fenster-Größe
        window_width = 280
        window_height = 120
        self.root.geometry(f"{window_width}x{window_height}")
        self.root.resizable(False, False)

        logger.info(f"GUI-Fenster erstellt: {window_width}x{window_height}")

        # Dark Mode Farben
        bg_color = "#1e1e1e"
        fg_color = "#e0e0e0"
        accent_color = "#4a9eff"
        progress_bg = "#2d2d2d"

        # Dark Mode für Hauptfenster
        self.root.configure(bg=bg_color)

        # Kompaktes Layout mit Dark Mode
        # Status-Label (kombiniert mit Model-Info)
        status_text = "STRG+Space" if KEYBOARD_AVAILABLE else "STRG+Space / F9"
        self.status_label = tk.Label(
            self.root,
            text=f"Bereit • {self.model_size} • {status_text}",
            font=("Segoe UI", 9),
            bg=bg_color,
            fg=fg_color
        )
        self.status_label.pack(pady=(10, 5))

        # Fortschrittsbalken - Custom Style für Dark Mode
        style = ttk.Style()
        style.theme_use('default')
        style.configure(
            "dark.Horizontal.TProgressbar",
            background=accent_color,
            troughcolor=progress_bg,
            bordercolor=progress_bg,
            lightcolor=accent_color,
            darkcolor=accent_color,
            borderwidth=0,
            troughrelief='flat'
        )

        self.progress = ttk.Progressbar(
            self.root,
            orient="horizontal",
            length=240,
            mode="determinate",
            style="dark.Horizontal.TProgressbar"
        )
        self.progress.pack(pady=8)

        # Aufnahme-Indikator (wird beim Aufnehmen sichtbar)
        self.recording_label = tk.Label(
            self.root,
            text="",
            font=("Segoe UI", 8),
            bg=bg_color,
            fg="#ff6b6b"
        )
        self.recording_label.pack(pady=2)

        # Performance/Info Label
        self.perf_label = tk.Label(
            self.root,
            text="Auto-Paste aktiv" if PYAUTOGUI_AVAILABLE else "Nur Zwischenablage",
            font=("Segoe UI", 8),
            bg=bg_color,
            fg="#808080"
        )
        self.perf_label.pack(pady=2)

        # Immer im Vordergrund aber dezent
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.95)  # Leicht transparent

        # Position rechts unten (Fenster ist 280x120)
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        logger.info(f"Bildschirm-Auflösung: {screen_width}x{screen_height}")

        # Berechne Position für rechts unten
        # Wichtig: Größerer Rand weil Taskbar Platz nimmt
        margin_right = 20  # Rand von rechts
        margin_bottom = 80  # Größerer Rand unten für Taskbar

        x = screen_width - window_width - margin_right
        y = screen_height - window_height - margin_bottom

        # Stelle sicher, dass das Fenster nicht negativ positioniert ist
        x = max(0, x)
        y = max(0, y)

        logger.info(f"Bildschirm: {screen_width}x{screen_height}, Fenster: {window_width}x{window_height}")
        logger.info(f"Fenster-Position berechnet: x={x}, y={y}")
        logger.info(f"  (rechts: {margin_right}px, unten: {margin_bottom}px Rand)")

        # Setze Fenster-Größe und Position
        geometry_str = f"{window_width}x{window_height}+{x}+{y}"
        self.root.geometry(geometry_str)
        logger.info(f"Fenster-Geometry gesetzt: {geometry_str}")

        # Stelle sicher dass Fenster sichtbar ist
        self.root.lift()
        self.root.focus()
        logger.info("Fenster nach vorne geholt und fokussiert")
        flush_logger()

    def find_aimp(self):
        """Findet AIMP-Prozess und bereitet Lautstärke-Kontrolle vor"""
        if not PYCAW_AVAILABLE:
            logger.debug("pycaw nicht verfügbar - AIMP Kontrolle deaktiviert")
            return

        try:
            sessions = AudioUtilities.GetAllSessions()
            for session in sessions:
                if session.Process:
                    process_name = session.Process.name().lower()
                    # Präzise AIMP-Erkennung (nur aimp.exe oder aimp32.exe)
                    if process_name in ["aimp.exe", "aimp32.exe", "aimp64.exe"]:
                        self.aimp_volume_interface = session._ctl.QueryInterface(ISimpleAudioVolume)
                        logger.info("✅ AIMP gefunden - Lautstärke-Kontrolle aktiviert")
                        return True
            logger.info("ℹ️ AIMP nicht gefunden - läuft nicht oder nicht aktiv")
        except Exception as e:
            logger.warning(f"⚠️ Fehler beim Suchen nach AIMP: {e}")
        return False

    def reduce_aimp_volume(self):
        """Reduziert AIMP Lautstärke während Aufnahme"""
        logger.debug(f"reduce_aimp_volume() aufgerufen - aimp_volume_interface={self.aimp_volume_interface}")
        if self.aimp_volume_interface:
            try:
                # Aktuelle Lautstärke speichern
                self.aimp_original_volume = self.aimp_volume_interface.GetMasterVolume()
                logger.info(f"Aktuelle AIMP-Lautstärke: {self.aimp_original_volume*100:.1f}%")

                # Auf 7% reduzieren
                self.aimp_volume_interface.SetMasterVolume(self.reduce_volume_percent, None)
                logger.info(f"🔉 AIMP Lautstärke reduziert: {self.aimp_original_volume*100:.0f}% → {self.reduce_volume_percent*100:.0f}%")
                flush_logger()
            except Exception as e:
                logger.warning(f"Fehler beim Reduzieren der AIMP-Lautstärke: {e}", exc_info=True)
                flush_logger()
        else:
            logger.debug("⚠️ AIMP nicht verfügbar - Lautstärkereduktion übersprungen")

    def restore_aimp_volume(self):
        """Stellt AIMP Lautstärke sanft wieder her (Fade-In)"""
        logger.debug(f"restore_aimp_volume() aufgerufen - aimp_volume_interface={self.aimp_volume_interface}, original_volume={self.aimp_original_volume}")
        if self.aimp_volume_interface and self.aimp_original_volume is not None:
            try:
                # Starte Fade-In in separatem Thread für nicht-blockierende Ausführung
                logger.info(f"Starte AIMP Lautstärke Fade-In: {self.reduce_volume_percent*100:.0f}% → {self.aimp_original_volume*100:.0f}%")
                flush_logger()
                fade_thread = threading.Thread(target=self._fade_in_volume, name="AImp-FadeThread")
                fade_thread.start()
            except Exception as e:
                logger.warning(f"Fehler beim Starten des Fade-In Threads: {e}", exc_info=True)
                flush_logger()
                # Fallback: Direkt wiederherstellen
                try:
                    logger.info(f"Fallback: Stelle AIMP-Lautstärke direkt wieder her auf {self.aimp_original_volume*100:.0f}%")
                    self.aimp_volume_interface.SetMasterVolume(self.aimp_original_volume, None)
                    self.aimp_original_volume = None
                    flush_logger()
                except Exception as e2:
                    logger.warning(f"Auch Fallback fehlgeschlagen: {e2}")
                    flush_logger()
        else:
            logger.debug(f"Kann AIMP nicht restaurieren: interface={self.aimp_volume_interface}, volume={self.aimp_original_volume}")

    def _fade_in_volume(self):
        """Führt das sanfte Fade-In aus"""
        logger.debug(f"_fade_in_volume() gestartet in Thread {threading.current_thread().name}")

        if not self.aimp_volume_interface or self.aimp_original_volume is None:
            logger.warning("_fade_in_volume() konnte nicht ausgeführt werden - interface oder volume ist None")
            flush_logger()
            return

        try:
            current_volume = self.reduce_volume_percent
            target_volume = self.aimp_original_volume
            step_size = (target_volume - current_volume) / self.fade_steps
            step_duration = self.fade_duration / self.fade_steps

            logger.info(f"🔊 AIMP Lautstärke-Fade-In: {current_volume*100:.0f}% → {target_volume*100:.0f}% ({self.fade_steps} Schritte à {step_duration*1000:.0f}ms)")
            flush_logger()

            # Sanftes Fade-In
            for i in range(self.fade_steps):
                current_volume += step_size
                try:
                    self.aimp_volume_interface.SetMasterVolume(current_volume, None)
                    logger.debug(f"  Fade-Schritt {i+1}/{self.fade_steps}: {current_volume*100:.1f}%")
                except Exception as e:
                    logger.warning(f"Fehler bei Fade-Schritt {i+1}: {e}")
                    break
                time.sleep(step_duration)

            # Stelle sicher, dass exakte Ziellautstärke erreicht wird
            try:
                self.aimp_volume_interface.SetMasterVolume(target_volume, None)
                logger.info(f"✅ AIMP Lautstärke wiederhergestellt: {target_volume*100:.0f}%")
                flush_logger()
            except Exception as e:
                logger.warning(f"Fehler beim Setzen der finalen Lautstärke: {e}")
                flush_logger()

            self.aimp_original_volume = None

        except Exception as e:
            logger.critical(f"Fehler beim AIMP Fade-In: {e}", exc_info=True)
            flush_logger()

    def show_notification(self, message, is_error=False):
        """Zeigt eine Status-Benachrichtigung an (Dark Mode)"""
        if is_error:
            self.status_label.config(text=message, fg="#ff6b6b")  # Rot für Fehler
        else:
            self.status_label.config(text=message, fg="#e0e0e0")  # Hell für normal

        # Update Recording Indicator
        if "Aufnahme läuft" in message:
            self.recording_label.config(text="● REC")
        elif "Verarbeite" in message:
            self.recording_label.config(text="⚙ Verarbeitung...")
        else:
            self.recording_label.config(text="")

        self.root.update()

    def update_progress(self, value):
        """Aktualisiert den Fortschrittsbalken"""
        self.progress['value'] = value
        self.root.update()

    def start_recording(self):
        """Startet die Audioaufnahme"""
        logger.info("start_recording() aufgerufen")
        with self.recording_lock:
            if self.is_recording:
                logger.debug("Recording ist bereits aktiv - return")
                return

            # Prüfe ob noch eine Verarbeitung läuft (unter Lock)
            with self.processing_lock:
                if self.is_processing:
                    logger.warning("Verarbeitung läuft noch - Recording wird nicht gestartet")
                    self.show_notification("⚠️ Bitte warten, Verarbeitung läuft...", True)
                    return

            self.is_recording = True
            self.audio_frames = []
            logger.info("Recording-Flag gesetzt, audio_frames geleert")

        # AIMP Lautstärke reduzieren
        logger.info("Rufe reduce_aimp_volume() auf...")
        self.reduce_aimp_volume()
        flush_logger()

        try:
            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk
            )

            self.show_notification("🎤 Aufnahme läuft...")
            self.update_progress(0)

            # Aufnahme im separaten Thread
            self.recording_thread = threading.Thread(target=self.record_audio, daemon=True)
            self.recording_thread.start()

        except Exception as e:
            self.show_notification(f"❌ Aufnahmefehler: {e}", True)
            with self.recording_lock:
                self.is_recording = False
            # AIMP Lautstärke wiederherstellen bei Fehler
            self.restore_aimp_volume()

    def record_audio(self):
        """Aufnahme-Loop"""
        start_time = time.time()
        logger.info(f"Aufnahme gestartet (Thread: {threading.current_thread().name})")
        flush_logger()

        try:
            while self.is_recording:
                try:
                    data = self.stream.read(self.chunk, exception_on_overflow=False)
                    self.audio_frames.append(data)

                    # Fortschritt aktualisieren
                    elapsed = time.time() - start_time
                    progress = min(100, (elapsed / self.max_recording_time) * 100)
                    self.update_progress(progress)

                    # Maximale Aufnahmedauer prüfen
                    if elapsed >= self.max_recording_time:
                        logger.info(f"Maximale Aufnahmedauer ({self.max_recording_time}s) erreicht")
                        flush_logger()
                        self.stop_recording()
                        break

                except Exception as e:
                    logger.critical(f"EXCEPTION BEIM AUDIO-LESEN: {type(e).__name__}: {e}", exc_info=True)
                    flush_logger()
                    break
        except Exception as e:
            logger.critical(f"KRITISCHER FEHLER IN RECORD_AUDIO: {type(e).__name__}: {e}", exc_info=True)
            flush_logger()
        finally:
            elapsed = time.time() - start_time
            frame_count = len(self.audio_frames)
            logger.info(f"Aufnahme beendet: {elapsed:.2f}s, {frame_count} Frames aufgezeichnet")
            flush_logger()

    def stop_recording(self):
        """Stoppt die Audioaufnahme und startet Transkription"""
        logger.info("stop_recording() aufgerufen")
        with self.recording_lock:
            if not self.is_recording:
                logger.debug("Recording war nicht aktiv - return")
                return
            self.is_recording = False
            logger.info("Recording-Flag auf False gesetzt")

        self.show_notification("🔄 Verarbeite Aufnahme...")

        # AIMP Lautstärke wiederherstellen
        logger.info("Rufe restore_aimp_volume() auf...")
        self.restore_aimp_volume()
        flush_logger()

        # Stream sicher schließen
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
        except Exception as e:
            print(f"⚠️ Fehler beim Schließen des Streams: {e}")

        # Audio speichern und transkribieren
        self.processing_thread = threading.Thread(target=self.process_audio, daemon=True)
        self.processing_thread.start()

    def save_audio(self):
        """Speichert die Aufnahme als temporäre Datei"""
        temp_file = "temp_recording.wav"

        try:
            wf = wave.open(temp_file, 'wb')
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.format))
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(self.audio_frames))
            wf.close()
            return temp_file
        except Exception as e:
            print(f"Fehler beim Speichern: {e}")
            return None

    def clean_text(self, text):
        """Bereinigt den Text (Rechtschreibung + Füllwörter)"""
        if not text:
            return ""

        # Grundlegende Bereinigung
        text = re.sub(r'\s+', ' ', text)  # Mehrfache Leerzeichen
        text = text.strip()

        # Satzanfang groß schreiben
        if text and len(text) > 0:
            text = text[0].upper() + text[1:] if len(text) > 1 else text[0].upper()

        # Füllwörter entfernen
        words = text.split()
        cleaned_words = []

        for word in words:
            # Wort ohne Satzzeichen prüfen (nur Punkt, Komma, Ausrufezeichen, Fragezeichen entfernen)
            clean_word = re.sub(r'[.,!?;:\-]', '', word.lower())
            if clean_word and clean_word not in self.filler_words:
                cleaned_words.append(word)

        cleaned_text = ' '.join(cleaned_words)

        # Satzzeichen korrigieren
        if cleaned_text and not cleaned_text.endswith(('.', '!', '?')):
            cleaned_text += '.'

        return cleaned_text

    def process_audio(self):
        """Verarbeitet die Audioaufnahme mit Faster-Whisper"""
        with self.processing_lock:
            if self.is_processing:
                self.show_notification("⚠️ Verarbeitung läuft bereits", True)
                return
            self.is_processing = True

        temp_file = None
        logger.info(f"Audio-Verarbeitung gestartet (Thread: {threading.current_thread().name})")

        try:
            temp_file = self.save_audio()

            if not temp_file or not os.path.exists(temp_file):
                logger.error("Audio konnte nicht gespeichert werden")
                self.show_notification("❌ Aufnahme fehlgeschlagen", True)
                return

            # Prüfe Dateigröße
            file_size = os.path.getsize(temp_file)
            logger.info(f"Temp-Datei erstellt: {temp_file} ({file_size} bytes)")

            if file_size < 1000:
                logger.warning(f"Audio-Datei sehr klein ({file_size} bytes) - Aufnahme möglicherweise leer")
                self.show_notification("⚠️ Aufnahme zu kurz/leer", True)
                return

            if not self.model:
                logger.error("Whisper-Modell ist nicht geladen")
                flush_logger()
                self.show_notification("❌ Modell nicht geladen", True)
                return

            # Zeitmessung starten
            start_time = time.time()

            # Transkription mit Faster-Whisper
            logger.info(f"Starte Transkription mit Modell: {self.model_size}")
            flush_logger()
            self.show_notification("📝 Transkribiere (CPU-optimiert)...")

            # Robusteres Transcribe mit Exception Handling
            try:
                # Speicher vor Transkription prüfen
                import psutil
                process = psutil.Process()
                mem_info = process.memory_info()
                logger.info(f"Speicher vor Transkription: RSS={mem_info.rss/1024**2:.1f}MB, VMS={mem_info.vms/1024**2:.1f}MB")
                flush_logger()

                logger.debug("Rufe transcribe() auf...")
                flush_logger()
                segments, info = self.model.transcribe(
                    temp_file,
                    language="de",
                    beam_size=5,
                    best_of=5,
                    temperature=0.0,
                    vad_filter=True,  # Voice Activity Detection
                    vad_parameters=dict(
                        min_silence_duration_ms=500
                    )
                )
                logger.info(f"Transkription erfolgreich - Sprachinformation: {info}")
                flush_logger()
            except Exception as e:
                logger.critical(f"⚠️ EXCEPTION WÄHREND TRANSCRIBE(): {type(e).__name__}: {e}", exc_info=True)
                flush_logger()

                # Zusätzliche Debug-Info
                try:
                    import psutil
                    process = psutil.Process()
                    mem_info = process.memory_info()
                    logger.error(f"Speicher zum Zeitpunkt des Fehlers: RSS={mem_info.rss/1024**2:.1f}MB, VMS={mem_info.vms/1024**2:.1f}MB")
                    logger.error(f"CPU-Prozent: {process.cpu_percent(interval=0.1)}%")
                    flush_logger()
                except:
                    pass

                self.show_notification(f"❌ Transkription fehlgeschlagen", True)
                return

            # Text aus Segmenten zusammenfügen (mit Fehlerbehandlung)
            original_text = ""
            try:
                segment_texts = []
                logger.debug(f"Beginne Segment-Verarbeitung...")
                flush_logger()

                for segment in segments:
                    if hasattr(segment, 'text') and segment.text.strip():
                        segment_texts.append(segment.text.strip())
                        logger.debug(f"Segment: {segment.text}")
                original_text = " ".join(segment_texts).strip()
                logger.info(f"✅ {len(segment_texts)} Segmente verarbeitet")
                flush_logger()
            except Exception as e:
                logger.critical(f"EXCEPTION BEI SEGMENT-VERARBEITUNG: {type(e).__name__}: {e}", exc_info=True)
                flush_logger()
                self.show_notification("❌ Fehler bei der Segmentverarbeitung", True)
                return

            # Zeitmessung stoppen
            processing_time = time.time() - start_time
            self.perf_label.config(text=f"Verarbeitung: {processing_time:.1f}s")
            logger.info(f"Transkription abgeschlossen in {processing_time:.2f}s")

            if not original_text:
                logger.warning("Keine Sprache erkannt - Text ist leer")
                self.show_notification("❌ Keine Sprache erkannt", True)
                return

            # Text bereinigen
            self.show_notification("✨ Bereinige Text...")
            logger.info(f"Originales transkribiertes Ergebnis ({len(original_text)} Zeichen): {original_text[:100]}...")
            cleaned_text = self.clean_text(original_text)
            logger.info(f"Bereinigter Text ({len(cleaned_text)} Zeichen): {cleaned_text[:100]}...")

            # In Zwischenablage kopieren (immer)
            try:
                pyperclip.copy(cleaned_text)
                logger.info("✅ Text in Zwischenablage kopiert")
            except Exception as e:
                logger.error(f"Fehler beim Kopieren in Zwischenablage: {e}", exc_info=True)
                self.show_notification("❌ Fehler beim Kopieren", True)
                return

            # Auto-Paste wenn möglich
            if PYAUTOGUI_AVAILABLE:
                try:
                    # Kleiner Delay damit Fenster wieder Fokus bekommt
                    time.sleep(0.2)

                    # Versuche Text automatisch einzufügen wo der Cursor ist
                    # Methode 1: Mit keyboard library (wenn verfügbar)
                    if KEYBOARD_AVAILABLE:
                        logger.info("Verwende keyboard library für Auto-Paste")
                        kb.press_and_release('ctrl+v')
                        logger.info("✅ Auto-Paste erfolgreich (keyboard library)")
                        self.show_notification("✅ Text eingefügt & in Zwischenablage")
                    else:
                        # Methode 2: Mit pyautogui
                        logger.info("Verwende pyautogui für Auto-Paste")
                        pyautogui.hotkey('ctrl', 'v')
                        logger.info("✅ Auto-Paste erfolgreich (pyautogui)")
                        self.show_notification("✅ Text eingefügt & in Zwischenablage")

                    # Performance Info
                    self.perf_label.config(text=f"Auto-Paste • {processing_time:.1f}s")

                except Exception as e:
                    # Fallback: Nur Zwischenablage
                    logger.warning(f"Auto-Paste Fehler: {e}", exc_info=True)
                    self.show_notification("✅ Text in Zwischenablage (Auto-Paste fehlgeschlagen)")
            else:
                # Nur Zwischenablage
                logger.info("pyautogui nicht verfügbar - nur Zwischenablage")
                self.show_notification("✅ Text in Zwischenablage kopiert")

            self.update_progress(0)

            # Kurze Erfolgsmeldung anzeigen
            success_thread = threading.Thread(target=self.show_success_message, daemon=True)
            success_thread.start()

        except Exception as e:
            logger.critical(f"❌ KRITISCHER FEHLER BEI AUDIO-VERARBEITUNG: {type(e).__name__}: {e}", exc_info=True)
            flush_logger()
            self.show_notification(f"❌ Verarbeitungsfehler: {str(e)[:50]}", True)
        finally:
            logger.debug("Starte Cleanup nach Audio-Verarbeitung")
            flush_logger()

            # Processing-Flag zurücksetzen
            with self.processing_lock:
                self.is_processing = False

            # Temporäre Datei löschen
            try:
                if temp_file and os.path.exists(temp_file):
                    os.remove(temp_file)
                    logger.debug(f"Temp-Datei gelöscht: {temp_file}")
            except Exception as e:
                logger.warning(f"Fehler beim Löschen der Temp-Datei: {e}")

            # Garbage Collection für besseres Memory-Management
            try:
                gc.collect()
                logger.debug("Garbage Collection ausgeführt")
            except Exception as e:
                logger.warning(f"Fehler bei Garbage Collection: {e}")

            logger.info("Cleanup abgeschlossen")
            flush_logger()

    def show_success_message(self):
        """Zeigt eine kurze Erfolgsmeldung an"""
        time.sleep(2)
        status_text = "STRG+Space" if KEYBOARD_AVAILABLE else "STRG+Space / F9"
        self.show_notification(f"Bereit • {self.model_size} • {status_text}")
        self.perf_label.config(text="Auto-Paste aktiv" if PYAUTOGUI_AVAILABLE else "Nur Zwischenablage")

    def on_hotkey(self):
        """Hotkey-Handler"""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def setup_hotkey(self):
        """Richtet den Hotkey-Listener ein (mit besserem globalen Support)"""
        if KEYBOARD_AVAILABLE:
            # Verwende keyboard library für bessere globale Hotkeys
            try:
                # Registriere globalen Hotkey (suppress=True verhindert Double-Trigger)
                kb.add_hotkey('ctrl+space', self.on_hotkey, suppress=True)
                logger.info("✅ Globaler Hotkey registriert (STRG+Leertaste)")
                logger.info("   Funktioniert auch in CMD/PowerShell!")

                # Alternativ-Hotkey für Notfälle
                kb.add_hotkey('ctrl+shift+r', self.on_hotkey, suppress=True)
                logger.info("   Alternativ: STRG+SHIFT+R")

                self.listener = None  # Kein pynput listener nötig
                return
            except Exception as e:
                logger.warning(f"Fehler bei keyboard library Hotkey-Registrierung: {e}")
                logger.info("   Falle zurück auf pynput...")

        # Fallback auf pynput (original Code)
        logger.info("📌 Verwende pynput für Hotkeys")
        logger.info("   Hinweis: Bei CMD/PowerShell-Problemen:")
        logger.info("   - Klicken Sie einmal auf das Spracherkennungs-Fenster")
        logger.info("   - Oder nutzen Sie F9 als Alternative")

        def for_canonical(f):
            return lambda k: f(self.listener.canonical(k))

        # Haupthotkey STRG+Leertaste
        hotkey = keyboard.HotKey(
            keyboard.HotKey.parse('<ctrl>+<space>'),
            self.on_hotkey
        )

        def on_press(key):
            hotkey.press(self.listener.canonical(key))

            # Zusätzlich F9 als Alternative
            try:
                if key == keyboard.Key.f9:
                    self.on_hotkey()
            except:
                pass

        def on_release(key):
            hotkey.release(self.listener.canonical(key))

        self.listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.listener.start()

    def run(self):
        """Startet die Anwendung"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.shutdown()

    def shutdown(self):
        """Beendet die Anwendung sauber"""
        logger.info("🛑 Beende Anwendung...")

        # Recording stoppen
        with self.recording_lock:
            self.is_recording = False
        logger.debug("Recording-Flag gesetzt")

        # Processing stoppen
        with self.processing_lock:
            self.is_processing = False
        logger.debug("Processing-Flag gesetzt")

        # AIMP Lautstärke sicherheitshalber wiederherstellen (ohne Fade, direkt)
        if self.aimp_volume_interface and self.aimp_original_volume is not None:
            try:
                self.aimp_volume_interface.SetMasterVolume(self.aimp_original_volume, None)
                logger.info(f"🔊 AIMP Lautstärke direkt wiederhergestellt: {self.aimp_original_volume*100:.0f}%")
            except Exception as e:
                logger.warning(f"Fehler beim Wiederherstellen der AIMP-Lautstärke: {e}")

        # Audio-Stream sicher schließen
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            logger.debug("Audio-Stream geschlossen")
        except Exception as e:
            logger.warning(f"Fehler beim Schließen des Streams: {e}")

        # PyAudio terminieren
        try:
            if self.audio:
                self.audio.terminate()
                self.audio = None
            logger.debug("PyAudio terminiert")
        except Exception as e:
            logger.warning(f"Fehler beim Terminieren von PyAudio: {e}")

        # Hotkey cleanup
        if KEYBOARD_AVAILABLE:
            try:
                kb.unhook_all()
                logger.info("✅ Globale Hotkeys entfernt")
            except Exception as e:
                logger.warning(f"Fehler beim Entfernen der Hotkeys: {e}")
        elif hasattr(self, 'listener') and self.listener:
            try:
                self.listener.stop()
                logger.info("✅ Hotkey-Listener gestoppt")
            except Exception as e:
                logger.warning(f"Fehler beim Stoppen des Listeners: {e}")

        # Modell freigeben
        try:
            self.model = None
            gc.collect()
            logger.info("✅ Ressourcen freigegeben")
        except Exception as e:
            logger.warning(f"Fehler beim Freigeben von Ressourcen: {e}")

        # GUI beenden
        try:
            if self.root:
                self.root.quit()
            logger.info("✅ GUI beendet")
        except Exception as e:
            logger.warning(f"Fehler beim Beenden der GUI: {e}")

        logger.info("=" * 70)
        logger.info("Anwendung beendet")
        logger.info("=" * 70)

def main():
    parser = argparse.ArgumentParser(description='CPU-optimierte Spracherkennung mit Faster-Whisper')
    parser.add_argument('--model', '-m', type=str, default='small-int8',
                       choices=['tiny-int8', 'base-int8', 'small-int8', 'medium-int8',
                               'tiny', 'base', 'small', 'medium', 'large-v2'],
                       help='Faster-Whisper Modellgröße (Standard: small-int8)')
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("  Spracherkennung mit Faster-Whisper (CPU-optimiert)")
    logger.info("  Optimiert für i5-7200U / 16GB RAM")
    logger.info(f"  Modell: {args.model}")
    logger.info("=" * 60)

    if not FASTER_WHISPER_AVAILABLE:
        logger.critical("❌ Faster-Whisper muss installiert werden:")
        logger.error("pip install faster-whisper")
        logger.error("Dies bietet deutlich bessere CPU-Performance!")
        return

    # Abhängigkeiten prüfen
    try:
        import pyaudio
        import pyperclip
        import pynput
        logger.info("✅ Alle Abhängigkeiten verfügbar")
    except ImportError as e:
        logger.critical(f"❌ Fehlende Abhängigkeit: {e}")
        logger.error("Installieren mit:")
        logger.error("pip install pyaudio faster-whisper pyperclip pynput keyboard psutil")
        return

    try:
        logger.info("Initialisiere Anwendung...")
        app = OptimizedSpeechToTextApp(model_size=args.model)
        logger.info("✅ Anwendung erfolgreich initialisiert")

        logger.info("Starte GUI...")
        app.run()
    except Exception as e:
        logger.critical(f"❌ Kritischer Fehler in main(): {e}", exc_info=True)
    finally:
        logger.info("Führe Shutdown durch...")
        app.shutdown()

if __name__ == "__main__":
    main()