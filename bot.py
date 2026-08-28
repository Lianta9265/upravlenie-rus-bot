from pathlib import Path
import os
import sys
import time
import requests

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / "src"))

from core import find_entry, render_entry, render_sources, stats
from gemini_client import ask_gemini
from telegram_common import process_message, tg_api


def load_env_file():
    p = BASE / ".env"
    if not p.exists():
        return
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def main():
    load_env_file()
    token = os.getenv("BOT_TOKEN", "")
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if not token:
        raise RuntimeError("Не задан BOT_TOKEN. Добавьте его в .env.")

    # Polling и webhook одновременно работать не могут.
    # При локальном запуске отключаем ранее установленный webhook.
    try:
        requests.post(tg_api(token, "deleteWebhook"), timeout=20)
    except requests.RequestException:
        pass

    s = stats()
    print(f"Бот запущен. Проверенных словарных статей: {s['entries']}.")
    print("Для остановки нажмите Ctrl+C.")
    offset = None

    while True:
        try:
            params = {"timeout": 30}
            if offset is not None:
                params["offset"] = offset
            r = requests.get(tg_api(token, "getUpdates"), params=params, timeout=40)
            r.raise_for_status()
            data = r.json()

            for update in data.get("result", []):
                offset = update["update_id"] + 1
                message = update.get("message")
                if message:
                    process_message(
                        message, token, gemini_key,
                        find_entry, render_entry, render_sources, ask_gemini
                    )

        except KeyboardInterrupt:
            print("\nБот остановлен.")
            break
        except requests.RequestException:
            # Не печатаем exception: его текст может содержать BOT_TOKEN в URL.
            print("Нет связи с Telegram. Повтор через 5 секунд.")
            time.sleep(5)
        except Exception as e:
            # Здесь не должно быть URL с токеном.
            print("Ошибка обработки:", type(e).__name__)
            time.sleep(3)


if __name__ == "__main__":
    main()
