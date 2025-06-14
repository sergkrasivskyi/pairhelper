import subprocess
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
import sys

class BotReloader(FileSystemEventHandler):
    def __init__(self, script_path):
        self.script_path = script_path
        self.process = None
        self.log_file = None
        self.restart_bot()

    def restart_bot(self):
        if self.process:
            print("🛑 Зупиняємо бота...")
            self.process.kill()
        if self.log_file:
            self.log_file.close()

        print("🔄 Запускаємо бота...\n")

        self.log_file = open("bot.log", "w", encoding="utf-8")  # або "a" для дописування
        self.process = subprocess.Popen(
            [sys.executable, self.script_path],
            stdout=self.log_file,
            stderr=subprocess.STDOUT,
            bufsize=1
        )

    def on_modified(self, event):
        if event.src_path.endswith(".py"):
            print(f"💡 Зміна у файлі: {event.src_path}")
            self.restart_bot()

if __name__ == "__main__":
    script = "main.py"
    if not os.path.exists(script):
        print("❌ Файл main.py не знайдено.")
        sys.exit(1)

    print("👀 Слідкуємо за змінами у Python-файлах...\n")
    event_handler = BotReloader(script)
    observer = Observer()
    observer.schedule(event_handler, path=".", recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("⛔ Зупинено вручну.")
        observer.stop()
        observer.join()
        if event_handler.process:
            event_handler.process.kill()
