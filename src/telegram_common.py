import os
import requests

def tg_api(token: str, method: str) -> str:
    return f"https://api.telegram.org/bot{token}/{method}"


def send_message(token: str, chat_id, text: str):
    if not text:
        return
    chunks = []
    while len(text) > 3900:
        cut = text.rfind("\n", 0, 3900)
        if cut < 1000:
            cut = 3900
        chunks.append(text[:cut])
        text = text[cut:].lstrip()
    chunks.append(text)

    for chunk in chunks:
        try:
            r = requests.post(
                tg_api(token, "sendMessage"),
                data={"chat_id": chat_id, "text": chunk},
                timeout=30,
            )
            r.raise_for_status()
        except requests.RequestException:
            # ВАЖНО: не печатаем exception, потому что в нём может быть URL с токеном.
            print("Не удалось отправить сообщение в Telegram (без вывода секретных данных).")


def process_message(message: dict, token: str, gemini_key: str, find_entry, render_entry, render_sources, ask_gemini):
    chat_id = message.get("chat", {}).get("id")
    text = (message.get("text") or "").strip()
    if not chat_id:
        return

    low = text.lower()
    if low in {"/start", "старт"}:
        send_message(
            token, chat_id,
            "Здравствуйте! Я бот по управлению и сочетаемости русского языка.\n\n"
            "Введите слово или словосочетание, например:\n"
            "• заведующий\n• командовать\n• свойственный\n• оплатить\n\n"
            "Команды: /help, /sources"
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
