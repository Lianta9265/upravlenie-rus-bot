from pathlib import Path
import hashlib
import os
import sys
import threading
import requests
from flask import Flask, request, jsonify

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / "src"))

from core import find_entry, render_entry, render_sources, stats
from gemini_client import ask_gemini
from telegram_common import process_message, tg_api

app = Flask(__name__)

TOKEN = os.getenv("BOT_TOKEN", "")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", os.getenv("PUBLIC_URL", "")).rstrip("/")
SECRET = hashlib.sha256(TOKEN.encode("utf-8")).hexdigest()[:32] if TOKEN else ""


def set_webhook():
    if not TOKEN or not EXTERNAL_URL:
        print("Webhook не установлен: нет BOT_TOKEN или внешнего URL.")
        return
    try:
        r = requests.post(
            tg_api(TOKEN, "setWebhook"),
            data={
                "url": EXTERNAL_URL + "/telegram-webhook",
                "secret_token": SECRET,
                "drop_pending_updates": "true",
            },
            timeout=30,
        )
        if r.status_code == 200:
            print("Telegram webhook установлен.")
        else:
            print(f"Telegram webhook не установлен (HTTP {r.status_code}).")
    except requests.RequestException:
        print("Не удалось связаться с Telegram при установке webhook.")


@app.get("/")
def health():
    s = stats()
    return {
        "status": "ok",
        "service": "Управление и сочетаемость",
        "dictionary_entries": s["entries"],
    }


@app.post("/telegram-webhook")
def telegram_webhook():
    if SECRET:
        supplied = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if supplied != SECRET:
            return jsonify({"ok": False}), 403

    update = request.get_json(silent=True) or {}
    message = update.get("message")
    if message:
        # Сразу отвечаем Telegram, обработку делаем в отдельном потоке.
        threading.Thread(
            target=process_message,
            args=(
                message, TOKEN, GEMINI_KEY,
                find_entry, render_entry, render_sources, ask_gemini
            ),
            daemon=True,
        ).start()
    return jsonify({"ok": True})


if os.getenv("RENDER") == "true" or EXTERNAL_URL:
    threading.Thread(target=set_webhook, daemon=True).start()
