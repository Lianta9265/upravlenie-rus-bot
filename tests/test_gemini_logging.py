import io
import sys
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "src"))

import gemini_client


class ErrorResponse:
    status_code = 400

    def json(self):
        return {
            "error": {
                "status": "INVALID_ARGUMENT",
                "message": (
                    "Rejected secret-test-key for private-test-query and "
                    + gemini_client.PROMPT
                ),
            }
        }


def test_http_error_is_logged_without_secrets_or_behavior_changes():
    captured_request = {}

    def fake_post(url, **kwargs):
        captured_request["url"] = url
        captured_request.update(kwargs)
        return ErrorResponse()

    output = io.StringIO()
    with patch.object(gemini_client.requests, "post", side_effect=fake_post):
        with redirect_stdout(output):
            result = gemini_client.ask_gemini("private-test-query", "secret-test-key")

    log = output.getvalue()
    assert "GEMINI_HTTP_STATUS=400" in log
    assert "GEMINI_ERROR_STATUS=INVALID_ARGUMENT" in log
    assert "GEMINI_ERROR_MESSAGE=" in log
    assert f"GEMINI_MODEL={gemini_client.MODEL}" in log
    assert "GEMINI_PAYLOAD_FIELDS=generation_config,input,model" in log
    assert "GEMINI_PROMPT_LENGTH=" in log
    assert "secret-test-key" not in log
    assert "private-test-query" not in log
    assert gemini_client.PROMPT not in log

    assert captured_request["url"] == gemini_client.URL
    assert captured_request["json"]["model"] == gemini_client.MODEL
    assert captured_request["json"]["generation_config"] == {"thinking_level": "low"}
    assert set(captured_request["json"]) == {"model", "input", "generation_config"}
    assert result == (
        "В проверенной локальной базе точной статьи пока нет.\n"
        "ИИ временно недоступен (код 400)."
    )


if __name__ == "__main__":
    test_http_error_is_logged_without_secrets_or_behavior_changes()
    print("OK: Gemini error logging is safe and behavior is unchanged")
