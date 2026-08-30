import os
import requests

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
URL = "https://generativelanguage.googleapis.com/v1beta/interactions"

PROMPT = """
Ты — вспомогательный модуль узкого бота по управлению и сочетаемости русского языка.

Проверенной словарной статьи для запроса в локальной базе нет.
Твоя задача — дать ОСТОРОЖНУЮ справочную подсказку по управлению слова.

Правила:
1. Не утверждай, что ты проверил Розенталя, Грамоту или любой другой источник:
   текст источника тебе не передан.
2. Не придумывай раздел «НЕПРАВИЛЬНО». Лучше вообще не использовать его.
3. Если управление зависит от значения слова, раздели значения.
4. Укажи падежные вопросы и предлоги.
5. Дай 2–4 коротких естественных примера.
6. Не объясняй орфографию, этимологию и посторонние темы.
7. В конце ОБЯЗАТЕЛЬНО напиши:
   «⚠ Черновая справка ИИ: точная словарная статья пока не добавлена в локальную базу».
8. Если сомневаешься, так и скажи и не выдумывай модель.

Пиши компактно, по-русски, понятно школьнику.
"""


def _extract_text(data: dict) -> str:
    texts = []
    for step in data.get("steps", []):
        if step.get("type") != "model_output":
            continue
        for block in step.get("content", []):
            if block.get("type") == "text" and block.get("text"):
                texts.append(block["text"])
    if not texts:
        for output in data.get("outputs", []):
            if output.get("type") == "text" and output.get("text"):
                texts.append(output["text"])
    return "\n".join(texts).strip()


def _safe_error_value(value, sensitive_values) -> str:
    text = str(value or "unknown").replace("\r", " ").replace("\n", " ")
    for sensitive in sorted((str(x) for x in sensitive_values if x), key=len, reverse=True):
        text = text.replace(sensitive, "[REDACTED]")
    return text[:1000]


def _log_api_error(response, payload: dict, api_key: str, query: str):
    error = {}
    try:
        body = response.json()
        if isinstance(body, dict) and isinstance(body.get("error"), dict):
            error = body["error"]
    except (ValueError, TypeError):
        pass

    sensitive_values = (api_key, payload.get("input"), query)
    error_status = _safe_error_value(error.get("status"), sensitive_values)
    error_message = _safe_error_value(error.get("message"), sensitive_values)
    payload_fields = ",".join(sorted(payload.keys()))
    prompt_length = len(payload.get("input", ""))
    print(f"GEMINI_HTTP_STATUS={response.status_code}", flush=True)
    print(f"GEMINI_ERROR_STATUS={error_status}", flush=True)
    print(f"GEMINI_ERROR_MESSAGE={error_message}", flush=True)
    print(f"GEMINI_MODEL={MODEL}", flush=True)
    print(f"GEMINI_PAYLOAD_FIELDS={payload_fields}", flush=True)
    print(f"GEMINI_PROMPT_LENGTH={prompt_length}", flush=True)


def ask_gemini(query: str, api_key: str) -> str:
    if not api_key:
        return (
            "В проверенной локальной базе точной статьи пока нет.\n"
            "ИИ-подсказка отключена: не задан GEMINI_API_KEY."
        )

    payload = {
        "model": MODEL,
        "input": PROMPT + "\n\nЗапрос пользователя: " + repr(query),
        "generation_config": {"thinking_level": "low"},
    }

    try:
        response = requests.post(
            URL,
            headers={
                "x-goog-api-key": api_key,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=75,
        )
    except requests.RequestException:
        return (
            "В проверенной локальной базе точной статьи пока нет.\n"
            "Сейчас не удалось связаться с ИИ. Попробуйте позже."
        )

    if response.status_code != 200:
        _log_api_error(response, payload, api_key, query)
        # Не показываем пользователю ключи, URL или технические детали.
        return (
            "В проверенной локальной базе точной статьи пока нет.\n"
            f"ИИ временно недоступен (код {response.status_code})."
        )

    answer = _extract_text(response.json())
    if not answer:
        return (
            "В проверенной локальной базе точной статьи пока нет.\n"
            "ИИ не вернул текстовый ответ."
        )
    return answer
