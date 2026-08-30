from html import escape
from pathlib import Path
import re
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WELCOME_IMAGE = PROJECT_ROOT / "2.png"
TELEGRAM_CHUNK_SIZE = 3000

def tg_api(token: str, method: str) -> str:
    return f"https://api.telegram.org/bot{token}/{method}"


def _split_text(text: str, limit: int = TELEGRAM_CHUNK_SIZE) -> list[str]:
    """Split text at readable boundaries, safely below Telegram's 4096 limit."""
    chunks = []
    remaining = text.strip()
    while len(remaining) > limit:
        cut = remaining.rfind("\n\n", 0, limit + 1)
        if cut < limit // 3:
            cut = remaining.rfind("\n", 0, limit + 1)
        if cut < limit // 3:
            cut = remaining.rfind(" ", 0, limit + 1)
        if cut < limit // 3:
            cut = limit
        chunks.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks


def _telegram_html(text: str) -> str:
    """Convert the small Markdown subset Gemini uses into safe Telegram HTML."""
    lines = []
    for raw_line in text.splitlines():
        line = escape(raw_line)
        line = re.sub(r"^#{1,6}\s+(.+)$", r"<b>\1</b>", line)
        line = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line)
        line = re.sub(r"__(.+?)__", r"<b>\1</b>", line)
        line = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"<i>\1</i>", line)
        line = re.sub(r"(?<!_)_([^_\n]+?)_(?!_)", r"<i>\1</i>", line)
        line = re.sub(r"`([^`\n]+?)`", r"<code>\1</code>", line)
        lines.append(line)
    return "\n".join(lines)


def send_message(token: str, chat_id, text: str):
    if not text:
        return

    for chunk in _split_text(text):
        try:
            r = requests.post(
                tg_api(token, "sendMessage"),
                data={
                    "chat_id": chat_id,
                    "text": _telegram_html(chunk),
                    "parse_mode": "HTML",
                },
                timeout=30,
            )
            r.raise_for_status()
        except requests.RequestException:
            # ВАЖНО: не печатаем exception, потому что в нём может быть URL с токеном.
            print("Не удалось отправить сообщение в Telegram (без вывода секретных данных).")


def send_welcome_image(token: str, chat_id) -> bool:
    if not WELCOME_IMAGE.is_file():
        print("Приветственная карточка 2.png не найдена.")
        return False
    try:
        with WELCOME_IMAGE.open("rb") as image:
            r = requests.post(
                tg_api(token, "sendPhoto"),
                data={"chat_id": chat_id},
                files={"photo": (WELCOME_IMAGE.name, image, "image/png")},
                timeout=30,
            )
        r.raise_for_status()
        return True
    except (OSError, requests.RequestException):
        print("Не удалось отправить приветственную карточку.")
        return False


def process_message(message: dict, token: str, gemini_key: str, find_entry, render_entry, render_sources, ask_gemini):
    chat_id = message.get("chat", {}).get("id")
    text = (message.get("text") or "").strip()
    if not chat_id:
        return

    low = text.lower()
    if low in {"/start", "старт"}:
        send_welcome_image(token, chat_id)
        send_message(
            token, chat_id,
            "Здравствуйте! Я помогу проверить управление и сочетаемость слов.\n\n"
            "Отправьте слово или фразу — например: «оплатить проезд» или "
            "«заведующая кафедрой».\n\n"
            "Команды: /help · /sources"
        )
        return

    if low in {"/help", "помощь"}:
        send_message(
            token, chat_id,
            "Введите слово, словоформу или целую фразу.\n\n"
            "Сначала я ищу ответ в проверенной локальной словарной базе. "
            "Если статьи пока нет, могу дать отдельно помеченную черновую подсказку ИИ.\n\n"
            "Примеры:\n"
            "• командовать\n"
            "• заведующая кафедрой\n"
            "• как правильно: оплатить проезд или оплатить за проезд?"
        )
        return

    if low in {"/sources", "источники"}:
        send_message(token, chat_id, render_sources())
        return

    if not text:
        send_message(token, chat_id, "Напишите слово или словосочетание текстом.")
        return

    entry = find_entry(text)
    if entry:
        send_message(token, chat_id, render_entry(entry))
    else:
        send_message(token, chat_id, "В локальной базе статьи пока нет. Спрашиваю ИИ…")
        send_message(token, chat_id, ask_gemini(text, gemini_key))
