"""Tests for the TelegramNotify script, loaded from its python cell in lot/telegram_notify.lotnb."""
import json
import pathlib
import types

NOTEBOOK = pathlib.Path(__file__).resolve().parents[1] / "lot" / "telegram_notify.lotnb"
NOW = "2026-10-24T12:00:00.1234567Z"  # LoT TIMESTAMP "ISO" can carry 7 fractional digits
CHAT = "-1001234567890"


def load_script(name):
    for cell in json.loads(NOTEBOOK.read_text()):
        if cell["kind"] == 2 and cell["language"] == "python" and f"# Script Name: {name}" in cell["value"]:
            module = types.ModuleType(name)
            exec(compile(cell["value"], f"{NOTEBOOK.name}:{name}", "exec"), module.__dict__)
            return module
    raise LookupError(name)


tg = load_script("TelegramNotify")


def report(expires_at="2026-10-25T12:00:00Z", **extra):
    body = {"id": "bmgx1abcd", "kind": "parked_car", "description": "Carro em cima do passeio", "lat": 41.145,
            "lon": -8.61, "reported_at": "2026-10-24T11:00:00Z", "expires_at": expires_at}
    body.update(extra)
    return json.dumps(body)


def test_new_app_report_builds_a_send_message_body():
    message = json.loads(tg.new_barrier("bmgx1abcd", report(), CHAT, NOW))
    assert message["chat_id"] == CHAT
    assert message["text"].splitlines() == [
        "🚧 Novo obstáculo reportado",
        "Carro no passeio",
        "“Carro em cima do passeio”",
        "📍 https://www.google.com/maps?q=41.145000,-8.610000",
        "Rota acessível: https://accessible-routes.benlubetzky.workers.dev",
    ]
    assert "bmgx1abcd" not in message["text"]  # the channel is public: no internal ids


def test_quotes_and_newlines_in_the_description_stay_valid_json():
    message = json.loads(tg.new_barrier("bmgx1abcd", report(description='a "b"\n\n c'), CHAT, NOW))
    assert "“a \"b\" c”" in message["text"]


def test_empty_description_and_unknown_kind():
    lines = json.loads(tg.new_barrier("bmgx1abcd", report(description="", kind="alien"), CHAT, NOW))["text"]
    assert lines.splitlines()[1:3] == ["Outro", "📍 https://www.google.com/maps?q=41.145000,-8.610000"]


def test_skips_city_demo_and_odd_ids():
    for barrier_id in ("city-123", "demo-1", "b", "B123456", "b12/x"):
        assert tg.new_barrier(barrier_id, report(), CHAT, NOW) == "skip"


def test_skips_deleted_unreadable_and_expired_reports():
    assert tg.new_barrier("bmgx1abcd", "", CHAT, NOW) == "skip"
    assert tg.new_barrier("bmgx1abcd", "not json", CHAT, NOW) == "skip"
    assert tg.new_barrier("bmgx1abcd", report(lat="41.1"), CHAT, NOW) == "skip"
    assert tg.new_barrier("bmgx1abcd", report(expires_at="2026-10-24T12:00:00Z"), CHAT, NOW) == "skip"


def test_skips_without_a_valid_chat_id():
    for chat in ("", "null", "abc"):
        assert tg.new_barrier("bmgx1abcd", report(), chat, NOW) == "skip"
    assert json.loads(tg.new_barrier("bmgx1abcd", report(), "@rota_livre_ops", NOW))["chat_id"] == "@rota_livre_ops"


def test_gone_threshold_sends_only_at_three():
    assert tg.gone_threshold("bmgx1abcd", "2", report(), CHAT) == "skip"
    assert tg.gone_threshold("bmgx1abcd", "4", report(), CHAT) == "skip"
    lines = json.loads(tg.gone_threshold("bmgx1abcd", "3", report(), CHAT))["text"].splitlines()
    assert lines[0] == "⚠️ 3 pessoas dizem que este obstáculo já não está"
    assert lines[1] == "Carro no passeio"
    assert lines[-2:] == ["id: bmgx1abcd", "Rever e, se for o caso, retirá-lo."]


def test_gone_threshold_works_without_the_barrier_and_for_city_ids():
    lines = json.loads(tg.gone_threshold("city-42", "3", "", CHAT))["text"].splitlines()
    assert lines == ["⚠️ 3 pessoas dizem que este obstáculo já não está", "id: city-42",
                     "Rever e, se for o caso, retirá-lo."]


def test_gone_threshold_skips_bad_input():
    assert tg.gone_threshold("bmgx1abcd", "", report(), CHAT) == "skip"
    assert tg.gone_threshold("a/b", "3", report(), CHAT) == "skip"
    assert tg.gone_threshold("bmgx1abcd", "3", report(), "") == "skip"
