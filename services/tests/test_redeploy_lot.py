"""Tests for the pure parts of broker/redeploy_lot.py (no broker needed)."""
import importlib.util
import json
import pathlib
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("redeploy_lot", ROOT / "broker" / "redeploy_lot.py")
redeploy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(redeploy)

ACTION = 'DEFINE ACTION Ping\nON TOPIC "zz/in" DO\n    PUBLISH TOPIC "zz/out" WITH PAYLOAD\n'


def cell(language, value, kind=2):
    return {"kind": kind, "language": language, "value": value}


def test_real_notebooks_yield_only_actions_and_python():
    names = [(entity["kind"], entity["name"]) for entity in redeploy.load_entities()]
    assert names == [
        ("action", "StoreBarrierFeedback"),
        ("action", "ImportCityAlerts"), ("action", "SwitchCityAlerts"), ("python", "CityAlerts"),
        ("python", "OpsSummary"),
        ("action", "OpsSummaryOnBarrier"), ("action", "OpsSummaryOnFeedback"), ("action", "OpsSummaryRefresh"),
        ("python", "TelegramNotify"), ("action", "NotifyNewBarrier"), ("action", "NotifyGoneThreshold"),
    ]


def test_only_my_notebooks_are_read():
    assert redeploy.NOTEBOOKS == ("barrier_feedback.lotnb", "city_alerts.lotnb", "ops_panel.lotnb",
                                 "telegram_notify.lotnb")


def test_routes_panels_and_markdown_are_skipped():
    cells = [
        cell("markdown", "# DEFINE ACTION NotCode", kind=1),
        cell("lot", 'DEFINE ROUTE Api WITH TYPE REST_API\n    ADD REST_API_CONFIG\n'),
        cell("lot", 'DEFINE PANEL "Ops"\n    WITH TITLE "x"\n'),
        cell("shellscript", "echo DEFINE ACTION Nope"),
    ]
    assert redeploy.extract(cells, "x.lotnb") == []


def test_a_lot_cell_with_several_blocks_is_split():
    text = 'DEFINE MODEL Thing WITH TOPIC "a"\n    ADD STRING "x"\n\n' + ACTION + "\nDEFINE ACTION Pong\nON EVERY 5 SECONDS DO\n    PUBLISH TOPIC \"b\" WITH 1\n"
    entities = redeploy.extract([cell("lot", text)], "x.lotnb")
    assert [entity["name"] for entity in entities] == ["Ping", "Pong"]
    assert entities[0]["source"] == ACTION.rstrip()
    assert entities[1]["source"].startswith("DEFINE ACTION Pong") and entities[1]["source"].endswith("WITH 1")


def test_python_name_comes_from_the_script_name_comment():
    entities = redeploy.extract([cell("python", "# Script Name: Calc\ndef f():\n    return '1'\n")], "x.lotnb")
    assert entities == [{"kind": "python", "name": "Calc", "source": "# Script Name: Calc\ndef f():\n    return '1'",
                         "notebook": "x.lotnb"}]


def test_normalise_ignores_trailing_whitespace_and_blank_lines():
    assert redeploy.normalise("A  \n\n    B\t\n\n") == redeploy.normalise("A\n    B")
    assert redeploy.normalise("A\n    B") != redeploy.normalise("A\n  B")  # indentation matters in LoT


def test_status():
    action = {"kind": "action", "name": "Ping", "source": ACTION, "notebook": "x"}
    python = {"kind": "python", "name": "Calc", "source": "", "notebook": "x"}
    assert redeploy.status(action, {"Ping"}, ACTION.rstrip() + "\n\n") == "IDENTICAL"
    assert redeploy.status(action, {"Ping"}, ACTION.replace("zz/out", "zz/old")) == "DIFFERS"
    assert redeploy.status(action, {"Ping"}, None) == "DIFFERS"  # listed, but no retained source
    assert redeploy.status(action, set(), ACTION) == "NOT LIVE"
    assert redeploy.status(python, {"Calc"}, None) == "IDENTICAL"
    assert redeploy.status(python, set(), None) == "NOT LIVE"


def test_plan_fix_sends_the_notebooks_python_first_then_only_its_mismatched_actions():
    entities = [
        {"kind": "action", "name": "A1", "notebook": "a"},
        {"kind": "action", "name": "A2", "notebook": "a"},
        {"kind": "python", "name": "PyA", "notebook": "a"},
        {"kind": "action", "name": "B1", "notebook": "b"},
        {"kind": "python", "name": "PyB", "notebook": "b"},
    ]
    statuses = {"A1": "IDENTICAL", "A2": "DIFFERS", "PyA": "IDENTICAL", "B1": "IDENTICAL", "PyB": "IDENTICAL"}
    assert [entity["name"] for entity in redeploy.plan_fix(entities, statuses)] == ["PyA", "A2"]
    statuses.update(PyB="NOT LIVE")
    assert [entity["name"] for entity in redeploy.plan_fix(entities, statuses)] == ["PyA", "A2", "PyB"]
    assert redeploy.plan_fix(entities, dict.fromkeys(statuses, "IDENTICAL")) == []


def test_command_payload_is_plain_text_with_request_id_last():
    action = {"kind": "action", "name": "Ping", "source": ACTION, "notebook": "x"}
    python = {"kind": "python", "name": "Calc", "source": "# Script Name: Calc\ndef f():\n    return '1'\n",
              "notebook": "x"}
    assert redeploy.command(action, "r1") == "-addAction " + ACTION.rstrip() + " -requestId r1"
    assert redeploy.command(python, "r2").startswith("-addPython # Script Name: Calc\n")
    assert redeploy.command(python, "r2").endswith("return '1' -requestId r2")


def test_parse_reply_keeps_only_our_request():
    mine = json.dumps({"success": True, "requestId": "r1", "message": "ok"}).encode()
    assert redeploy.parse_reply(mine, "r1")["success"] is True
    assert redeploy.parse_reply(mine, "r2") is None
    assert redeploy.parse_reply(b"not json", "r1") is None
    assert redeploy.parse_reply(b"[1]", "r1") is None


NOW = datetime(2026, 10, 24, 13, 30, 0, tzinfo=timezone.utc)


def summary(updated_at):
    return json.dumps({"updated_at": updated_at, "active": {"app": 1, "city": 0, "demo": 0, "total": 1}})


def test_parse_time_accepts_z_and_seven_fractional_digits():
    assert redeploy.parse_time("2026-10-24T13:29:50.1234567Z") == datetime(2026, 10, 24, 13, 29, 50, 123456,
                                                                           tzinfo=timezone.utc)
    assert redeploy.parse_time("2026-10-24T13:29:50.1Z").microsecond == 100000
    assert redeploy.parse_time("2026-10-24T13:29:50Z") == datetime(2026, 10, 24, 13, 29, 50, tzinfo=timezone.utc)
    assert redeploy.parse_time("2026-10-24T13:29:50") is None  # no zone: refuse rather than guess
    assert redeploy.parse_time("yesterday") is None
    assert redeploy.parse_time("") is None and redeploy.parse_time(None) is None


def test_summary_status_fresh_up_to_45_seconds():
    assert redeploy.summary_status(summary("2026-10-24T13:29:45.0000000Z"), NOW) == ("FRESH", 15.0)
    assert redeploy.summary_status(summary("2026-10-24T13:29:15Z"), NOW) == ("FRESH", 45.0)
    assert redeploy.summary_status(summary("2026-10-24T13:29:14.9Z"), NOW)[0] == "STALE"
    assert redeploy.summary_status(summary("2026-10-24T12:00:00Z"), NOW) == ("STALE", 5400.0)


def test_summary_status_missing():
    assert redeploy.summary_status(None, NOW) == ("MISSING", None)
    assert redeploy.summary_status("", NOW) == ("MISSING", None)
    assert redeploy.summary_status("not json", NOW) == ("MISSING", None)
    assert redeploy.summary_status("[1]", NOW) == ("MISSING", None)
    assert redeploy.summary_status(json.dumps({"active": {}}), NOW) == ("MISSING", None)
