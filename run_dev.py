#!/usr/bin/env python3
# run_dev.py  ─  «гарячий» перезапуск Telegram-бота під час розробки
# 2025 · MIT License

import os, sys, subprocess, time, signal, threading
from pathlib import Path
from typing import Optional

from watchdog.observers import Observer
from watchdog.events     import FileSystemEventHandler, FileSystemEvent

# ────────────────────────────────────────────────────────────────
# Налаштування (можна змінити під свої вподобання)
# ────────────────────────────────────────────────────────────────
SCRIPT_PATH  = Path(sys.argv[1] if len(sys.argv) > 1 else "main.py")
LOG_PATH     = Path("bot.log")

WATCH_EXT    = (".py",)                 # стежимо лише за *.py
IGNORE_DIR   = {"__pycache__"}          # папки, які пропускаємо
DEBOUNCE     = 1.0                      # сек – «згортка» частих подій

# ────────────────────────────────────────────────────────────────
def is_ignored(path: Path) -> bool:
    """Чи пропустити файл/директорію (службові, тимчасові тощо)."""
    if path.is_dir() and path.name in IGNORE_DIR:
        return True
    if any(part in IGNORE_DIR for part in path.parts):
        return True
    if not path.suffix.lower() in WATCH_EXT:
        return True
    return False

# ────────────────────────────────────────────────────────────────
class BotReloader(FileSystemEventHandler):
    """Спостерігає за файлами → рестартує бота при зміні."""
    def __init__(self, script: Path):
        self.script = script
        self.proc: Optional[subprocess.Popen[str]] = None
        self.last_change = 0.0           # для debounce
        self.start_bot()

    # ── запуск / перезапуск ────────────────────────────────────
    def start_bot(self) -> None:
        self.stop_bot()

        print("🔄  Запускаємо бота…")
        LOG_PATH.parent.mkdir(exist_ok=True)

        self.proc = subprocess.Popen(
            [sys.executable, str(self.script)],
            stdout = subprocess.PIPE,
            stderr = subprocess.STDOUT,
            text   = True,
            encoding = "utf-8",
            bufsize  = 1
        )
        self._pipe_output()              # дублюємо stdout у лог

    def stop_bot(self) -> None:
        if self.proc is None:
            return
        print("🛑  Зупиняємо бота…")
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.proc = None

    # ── File-watch callback ────────────────────────────────────
    def on_modified(self, event: FileSystemEvent) -> None:
        path = Path(event.src_path)
        if is_ignored(path):
            return

        now = time.time()
        if now - self.last_change < DEBOUNCE:        # згортка подій
            return
        self.last_change = now

        print(f"💡  Зміна у файлі: {path.relative_to(Path.cwd())}")
        self.start_bot()

    # ── дублюємо stdout бота у консоль + bot.log ───────────────
    def _pipe_output(self) -> None:
        assert self.proc and self.proc.stdout
        log_file = LOG_PATH.open("a", encoding="utf-8")

        def _pump():
            with self.proc.stdout, log_file:
                for line in self.proc.stdout:
                    print(line.rstrip())
                    log_file.write(line)
        threading.Thread(target=_pump, daemon=True).start()

# ────────────────────────────────────────────────────────────────
def main() -> None:
    if not SCRIPT_PATH.exists():
        sys.exit(f"❌  {SCRIPT_PATH} не знайдено")

    print("👀  Слідкуємо за *.py файлами…  (Ctrl-C для виходу)\n")

    observer = Observer()
    handler  = BotReloader(SCRIPT_PATH)
    observer.schedule(handler, path=".", recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n⛔  Зупинено вручну.")
    finally:
        observer.stop()
        observer.join()
        handler.stop_bot()

# ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
