import sys
from pathlib import Path
from unittest.mock import Mock, patch

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "src"))

import telegram_common


def ok_response():
    response = Mock()
    response.raise_for_status.return_value = None
    return response


def test_start_sends_project_image_then_greeting():
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return ok_response()

    with patch.object(telegram_common.requests, "post", side_effect=fake_post):
        telegram_common.process_message(
            {"chat": {"id": 123}, "text": "/start"},
            "test-token", "", Mock(), Mock(), Mock(), Mock(),
        )

    assert calls[0][0].endswith("/sendPhoto")
    assert calls[0][1]["files"]["photo"][0] == "2.png"
    assert calls[1][0].endswith("/sendMessage")


def test_markdown_is_rendered_as_html():
    with patch.object(telegram_common.requests, "post", return_value=ok_response()) as post:
        telegram_common.send_message("test-token", 123, "**Важно** и *пример*")

    data = post.call_args.kwargs["data"]
    assert data["parse_mode"] == "HTML"
    assert data["text"] == "<b>Важно</b> и <i>пример</i>"


def test_long_answer_is_split_into_valid_sized_messages():
    long_text = "**Раздел**\n" + ("слово " * 2500)
    with patch.object(telegram_common.requests, "post", return_value=ok_response()) as post:
        telegram_common.send_message("test-token", 123, long_text)

    assert post.call_count > 1
    for call in post.call_args_list:
        assert len(call.kwargs["data"]["text"]) < 4096


if __name__ == "__main__":
    test_start_sends_project_image_then_greeting()
    test_markdown_is_rendered_as_html()
    test_long_answer_is_split_into_valid_sized_messages()
    print("OK: Telegram start, formatting and long-message splitting")
