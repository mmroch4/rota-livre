"""Tests for the OpsSummary script, loaded from its python cell in lot/ops_panel.lotnb."""
import json
import pathlib
import threading
import types

import pytest

NOTEBOOK = pathlib.Path(__file__).resolve().parents[2] / "lot" / "ops_panel.lotnb"
NOW = "2026-10-24T12:00:00.1234567Z"  # LoT TIMESTAMP "ISO" can carry 7 fractional digits
LATER = "2026-10-25T13:00:00.000Z"


def load_script(name):
    for cell in json.loads(NOTEBOOK.read_text()):
        if cell["kind"] == 2 and cell["language"] == "python" and f"# Script Name: {name}" in cell["value"]:
            module = types.ModuleType(name)
            exec(compile(cell["value"], f"{NOTEBOOK.name}:{name}", "exec"), module.__dict__)
            return module
    raise LookupError(name)


ops = load_script("OpsSummary")


@pytest.fixture(autouse=True)
def fresh_state():
    ops.reset()  # the script keeps its state in module memory, like on the broker


def report(barrier_id, expires_at="2026-10-25T12:00:00Z", **extra):
    return json.dumps({"id": barrier_id, "kind": "parked_car", "description": "Carro no passeio", "lat": 41.145,
                       "lon": -8.61, "reported_at": "2026-10-24T11:00:00Z", "expires_at": expires_at, **extra})


def apply(summary, barrier_id, payload, now=NOW):
    return ops.apply_barrier(summary, barrier_id, payload, now)


def build(*ids):
    summary = ""
    for barrier_id in ids:
        summary = apply(summary, barrier_id, report(barrier_id))
    return summary


def test_counts_active_barriers_per_source():
    summary = json.loads(build("bk2x9abc", "city-cmp1", "city-cmp2", "demo-roadworks"))
    assert summary["active"] == {"app": 1, "city": 2, "demo": 1, "total": 4}
    assert [b["id"] for b in summary["barriers"]] == ["bk2x9abc", "city-cmp1", "city-cmp2", "demo-roadworks"]
    assert summary["barriers"][0] == {
        "id": "bk2x9abc", "source": "app", "kind": "parked_car", "description": "Carro no passeio",
        "expires_at": "2026-10-25T12:00:00.000Z", "gone_count": 0,
    }
    assert summary["updated_at"] == "2026-10-24T12:00:00.123Z"


def test_a_republished_barrier_is_counted_once():
    summary = apply(build("city-cmp1"), "city-cmp1", report("city-cmp1", kind="works"))
    assert json.loads(summary)["active"]["city"] == 1
    assert json.loads(summary)["barriers"][0]["kind"] == "works"


def test_retired_deleted_or_unreadable_barriers_are_dropped():
    summary = build("city-cmp1", "bk2x9abc", "demo-roadworks", "bzz1234")
    summary = apply(summary, "city-cmp1", report("city-cmp1", expires_at=NOW))  # the broker's "off" / retire
    summary = apply(summary, "bk2x9abc", "")  # the reporter deleted it (empty retained)
    summary = apply(summary, "demo-roadworks", "not json")
    summary = apply(summary, "bzz1234", json.dumps({"id": "bzz1234", "lat": "41.1", "lon": -8.6}))  # app ignores it
    assert json.loads(summary)["active"] == {"app": 0, "city": 0, "demo": 0, "total": 0}


def test_ignores_unsafe_ids_and_keeps_a_barrier_without_expiry():
    summary = apply(build("city-cmp1"), "../x", report("../x"))
    summary = apply(summary, "bnoexpiry1", report("bnoexpiry1", expires_at=None))
    assert [b["id"] for b in json.loads(summary)["barriers"]] == ["bnoexpiry1", "city-cmp1"]


def test_refresh_drops_barriers_that_expired_since():
    summary = apply(build("city-cmp1"), "demo-x", report("demo-x", expires_at="2026-10-26T00:00:00Z"))
    refreshed = json.loads(ops.refresh(summary, LATER))
    assert refreshed["active"] == {"app": 0, "city": 0, "demo": 1, "total": 1}
    assert refreshed["updated_at"] == "2026-10-25T13:00:00.000Z"


def test_feedback_counts_join_the_barriers_and_outlive_them():
    summary = build("city-cmp1", "bk2x9abc")
    summary = ops.apply_feedback(summary, "city-cmp1", "2", "2026-10-24T11:59:00Z", NOW)
    summary = ops.apply_feedback(summary, "bk2x9abc", "1", "2026-10-24T11:58:00Z", NOW)
    summary = ops.apply_feedback(summary, "demo-gone", "3", "2026-10-24T11:50:00Z", NOW)  # no active barrier
    parsed = json.loads(summary)
    assert {b["id"]: b["gone_count"] for b in parsed["barriers"]} == {"bk2x9abc": 1, "city-cmp1": 2}
    assert parsed["feedback"] == [
        {"barrier_id": "demo-gone", "gone_count": 3, "last_answered_at": "2026-10-24T11:50:00Z"},
        {"barrier_id": "city-cmp1", "gone_count": 2, "last_answered_at": "2026-10-24T11:59:00Z"},
        {"barrier_id": "bk2x9abc", "gone_count": 1, "last_answered_at": "2026-10-24T11:58:00Z"},
    ]
    summary = apply(summary, "city-cmp1", "")
    assert [f["barrier_id"] for f in json.loads(summary)["feedback"]] == ["demo-gone", "city-cmp1", "bk2x9abc"]


def test_cleared_feedback_topics_remove_the_row():
    summary = ops.apply_feedback("", "zz-test", "1", "2026-10-24T11:59:00Z", NOW)
    assert ops.apply_feedback(summary, "zz-test", "", "", NOW).count("zz-test") == 0


def test_a_broken_summary_starts_over_and_results_are_strings():
    for broken in ("", "not json", "[]", '{"barriers": "x"}'):
        ops.reset()
        result = apply(broken, "demo-a", report("demo-a"))
        assert isinstance(result, str) and json.loads(result)["active"]["demo"] == 1
    assert isinstance(ops.refresh("", NOW), str)


def test_long_descriptions_are_shortened():
    payload = report("bk2x9abc", description="x" * 200)
    description = json.loads(apply("", "bk2x9abc", payload))["barriers"][0]["description"]
    assert len(description) == 80 and description.endswith("…")


def test_after_a_restart_the_state_is_seeded_from_the_retained_summary():
    summary = ops.apply_feedback(build("city-cmp1", "demo-a"), "city-cmp1", "2", "2026-10-24T11:59:00Z", NOW)
    ops.reset()  # broker restart or redeploy
    seeded = json.loads(apply(summary, "bk2x9abc", report("bk2x9abc")))
    assert seeded["active"] == {"app": 1, "city": 1, "demo": 1, "total": 3}
    assert seeded["feedback"][0]["gone_count"] == 2


def test_the_state_wins_over_a_stale_summary():
    build("city-cmp1", "city-cmp2")
    stale = apply("", "city-cmp3", report("city-cmp3"))  # every call may read an older retained summary
    assert json.loads(stale)["active"]["city"] == 3


def test_concurrent_calls_lose_no_update():
    # What the broker does on an import burst: the Action runs once per barrier, in parallel, each with the
    # same old summary. With read-change-publish this counted 6 of 24.
    ids = [f"city-cmp{i}" for i in range(48)]
    threads = [threading.Thread(target=apply, args=("", i, report(i))) for i in ids]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert json.loads(ops.refresh("", NOW))["active"]["city"] == 48
