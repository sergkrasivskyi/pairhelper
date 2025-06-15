#!/usr/bin/env python3
# run_dev.py ─ автоматичний перезапуск Telegram-бота під час розробки
# © 2025  MIT License

import subprocess
import sys
import os
import time
import signal
from pathlib import Path
from typing import Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

# ────────────────────────────────────────────────
# Налаштування
# ────────────────────────────────────────────────
SCRIPT_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "main.py")
LOG_PATH    = Path("bot.log")
DEBOUNCE_MS = 200          # перезапуск не частіше, ніж раз на 0.2 сек

WATCHED_EXT = (".py",)     # можна додати ".env" тощо


# ────────────────────────────────────────────────
# Допоміжні функції
# ────────────────────────────────────────────────
def is_ignored(path: Path) -> bool:
    """Пропускати приховані файли, __pycache__, тимчасові правки редакторів."""
    name = path.name
    if name.startswith(".") or name.endswith(("~", ".swp", ".tmp")):
        return True
    if "__pycache__" in path.parts:
        return True
    return False


# ────────────────────────────────────────────────
# Клас-релоадер
# ────────────────────────────────────────────────
class BotReloader(FileSystemEventHandler):
    def __init__(self, script: Path):
        self.script: Path = script
        self.proc:  Optional[subprocess.Popen] = None
        self.last_event = 0.0               # час останнього перезапуску (для debounce)
        self.start_bot()

    # ── Запуск / перезапуск
    def start_bot(self) -> None:
        self.stop_bot()                     # зупинимо, якщо вже є
        print("🔄  Запускаємо бота…")
        LOG_PATH.parent.mkdir(exist_ok=True)
        self.proc = subprocess.Popen(
            [sys.executable, str(self.script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding="utf-8"
        )
        # Дублікуємо output у термінал + log-файл
        self._pipe_output()

    def stop_bot(self) -> None:
        if not self.proc:
            return
        print("🛑  Зупиняємо бота…")
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.proc = None

    # ── Обробка події файлової системи
    def on_modified(self, event: FileSystemEvent) -> None:
        path = Path(event.src_path)
        if is_ignored(path) or path.suffix not in WATCHED_EXT:
            return
        now = time.time()
        if (now - self.last_event) * 1000 < DEBOUNCE_MS:      # debounce
            return
        self.last_event = now
        print(f"💡  Зміна у файлі: {path}")
        self.start_bot()

    # ── Читаємо stdout бота і дублюємо
    def _pipe_output(self) -> None:
        assert self.proc and self.proc.stdout
        log_file = LOG_PATH.open("w", encoding="utf-8")
        def _pump():
            with self.proc.stdout, log_file:
                for line in self.proc.stdout:
                    print(line.rstrip())
                    log_file.write(line)
        import threading; threading.Thread(target=_pump, daemon=True).start()


# ────────────────────────────────────────────────
# Точка входу
# ────────────────────────────────────────────────
def main() -> None:
    if not SCRIPT_PATH.exists():
        sys.exit(f"❌  {SCRIPT_PATH} не знайдено")

    print("👀  Слідкуємо за *.py файлами…  (Ctrl-C для виходу)\n")

    observer = Observer()
    handler  = BotReloader(SCRIPT_PATH)
    observer.schedule(handler, path=".", recursive=True)
    observer.start()

    # ⌨️ Ctrl-C — красиво завершуємо
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⛔  Зупинено вручну.")
    finally:
        observer.stop()
        observer.join()
        handler.stop_bot()


if __name__ == "__main__":
    main()
