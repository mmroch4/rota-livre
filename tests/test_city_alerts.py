"""Tests for the CityAlerts script, loaded from its python cell in lot/city_alerts.lotnb."""
import json
import pathlib
import types

NOTEBOOK = pathlib.Path(__file__).resolve().parents[1] / "lot" / "city_alerts.lotnb"
NOW = "2026-10-24T12:00:00.1234567Z"  # LoT TIMESTAMP "ISO" can carry 7 fractional digits


def load_script(name):
    for cell in json.loads(NOTEBOOK.read_text()):
        if cell["kind"] == 2 and cell["language"] == "python" and f"# Script Name: {name}" in cell["value"]:
            module = types.ModuleType(name)
            exec(compile(cell["value"], f"{NOTEBOOK.name}:{name}", "exec"), module.__dict__)
            return module
    raise LookupError(name)


city = load_script("CityAlerts")


def alert(cmp, description="Obras particulares OEP com tapume", valid_to="2027-01-31T00:00:00.00Z", **extra):
    # Shape of a keyValues entity from the Porto Urban Platform (24/10/2026).
    square = [[-8.6101, 41.1450], [-8.6099, 41.1450], [-8.6099, 41.1452], [-8.6101, 41.1452], [-8.6101, 41.1450]]
    return {
        "id": f"urn:ngsi-ld:Alert:porto:RoadAlerts:{cmp}",
        "type": "Alert",
        "category": "traffic",
        "subCategory": "roadWorks",
        "description": description,
        "validFrom": "2025-04-30T00:00:00.00Z",
        "validTo": valid_to,
        "location": {"type": "Polygon", "coordinates": [square]},
        **extra,
    }


def run(alerts, known=None, now=NOW):
    raw = alerts if isinstance(alerts, str) else json.dumps(alerts)
    return json.loads(city.import_alerts(raw, json.dumps(known) if known is not None else "", now))


def test_maps_an_alert_to_the_barrier_contract():
    batch = run([alert("cmp1")])
    assert batch["ok"] is True and batch["count"] == 1
    b = batch["publish"][0]
    assert b == {
        "id": "city-cmp1",
        "kind": "works",
        "description": "Câmara do Porto: Obras particulares OEP com tapume",
        "lat": 41.14508,  # mean of the ring's vertices (the closing vertex counts twice)
        "lon": -8.61002,
        "reported_at": "2025-04-30T00:00:00.000Z",
        "expires_at": "2027-01-31T00:00:00.000Z",
        "source": "cm-porto",
    }
    assert isinstance(b["lat"], float) and isinstance(b["lon"], float)  # the app ignores non-numeric lat/lon


def test_keeps_only_active_pavement_works():
    batch = run([
        alert("works", "Obras públicas Prorrogação até 29/11/2026"),
        alert("loading", "Cargas e descargas Das 10:00 às 16:00"),
        alert("purpose", "Obras particulares Pedido de alteração de finalidade para cargas e descargas"),
        alert("event", "Eventos e lazer Aos domingos"),
        alert("pump", "Bombagem de betão"),
        alert("ended", valid_to="2026-10-16T11:30:00.00Z"),
        alert("future", validFrom="2026-11-01T00:00:00.00Z"),
        alert("nowhere", location={"type": "Point", "coordinates": []}),
    ])
    assert [b["id"] for b in batch["publish"]] == ["city-works"]


def test_decodes_and_shortens_descriptions():
    text = "Obras públicas No%20tro%C3%A7o%20compreendido " + "x" * 300
    description = run([alert("cmp1", text)])["publish"][0]["description"]
    assert description.startswith("Câmara do Porto: Obras públicas No troço compreendido x")
    assert len(description) <= len("Câmara do Porto: ") + 200 and description.endswith("…")


def test_multipolygon_and_point_locations():
    multi = {"type": "MultiPolygon", "coordinates": [[[[-8.0, 41.0], [-8.0, 41.0]]], [[[-9.0, 42.0], [-9.0, 42.0]]]]}
    point = {"type": "Point", "coordinates": [-8.61, 41.145]}
    batch = run([alert("multi", location=multi), alert("point", location=point)])
    by_id = {b["id"]: b for b in batch["publish"]}
    assert (by_id["city-multi"]["lat"], by_id["city-multi"]["lon"]) == (41.5, -8.5)
    assert (by_id["city-point"]["lat"], by_id["city-point"]["lon"]) == (41.145, -8.61)


def test_unchanged_alerts_are_not_republished():
    first = run([alert("cmp1"), alert("cmp2")])
    again = run([alert("cmp1"), alert("cmp2")], known=first["known"])
    assert again["count"] == 0 and again["publish"] == [] and again["known"] == first["known"]
    changed = run([alert("cmp1", valid_to="2027-06-30T00:00:00Z"), alert("cmp2")], known=first["known"])
    assert [b["id"] for b in changed["publish"]] == ["city-cmp1"]


def test_alert_gone_from_the_source_is_retired_with_expiry_now():
    first = run([alert("cmp1"), alert("cmp2")])
    later = run([alert("cmp2")], known=first["known"], now="2026-10-24T13:00:00Z")
    assert later["count"] == 1
    retired = later["publish"][0]
    assert retired["id"] == "city-cmp1" and retired["expires_at"] == "2026-10-24T13:00:00.000Z"
    assert retired["lat"] == first["known"]["city-cmp1"]["lat"]  # still a valid barrier message for the app
    assert set(later["known"]) == {"city-cmp2"}


def test_failed_fetch_changes_nothing():
    known = run([alert("cmp1")])["known"]
    for raw in ['{"success":false,"statusCode":503}', "not json", ""]:
        batch = run(raw, known=known)
        assert batch["ok"] is False and batch["count"] == 0 and batch["known"] == known
    assert run([alert("cmp1")], known=known, now="garbage")["ok"] is False


def test_pick_and_known_of_return_json_strings():
    batch_json = city.import_alerts(json.dumps([alert("cmp1"), alert("cmp2")]), "", NOW)
    assert json.loads(city.pick(batch_json, 0))["id"] == "city-cmp1"
    assert json.loads(city.pick(batch_json, "1"))["id"] == "city-cmp2"  # LoT may pass the index as text
    assert city.pick(batch_json, 2) == "{}" and city.pick(batch_json, "x") == "{}" and city.pick("", 0) == "{}"
    assert set(json.loads(city.known_of(batch_json))) == {"city-cmp1", "city-cmp2"}
    assert all(isinstance(v, str) for v in (batch_json, city.pick(batch_json, 0), city.known_of("")))


def test_unsafe_source_ids_are_cleaned():
    b = run([alert("cmp/1#+")])["publish"][0]
    assert b["id"] == "city-cmp1"


def test_switch_off_retires_every_imported_barrier_and_on_brings_them_back():
    first = run([alert("cmp1"), alert("cmp2")])
    off = json.loads(city.retire_all(json.dumps(first["known"]), "2026-10-24T13:00:00Z"))
    assert off["ok"] is True and off["count"] == 2 and off["known"] == {}
    assert [b["id"] for b in off["publish"]] == ["city-cmp1", "city-cmp2"]
    assert all(b["expires_at"] == "2026-10-24T13:00:00.000Z" for b in off["publish"])
    assert off["publish"][0]["lat"] == first["known"]["city-cmp1"]["lat"]
    on = run([alert("cmp1"), alert("cmp2")], known=off["known"])  # the fetch after "on"
    assert on["publish"] == first["publish"]  # republished with their real expiry


def test_switch_off_with_nothing_imported_or_a_bad_time():
    for known in ["", "{}", "not json"]:
        batch = json.loads(city.retire_all(known, NOW))
        assert batch == {"ok": True, "count": 0, "publish": [], "known": {}}
    assert json.loads(city.retire_all("{}", "garbage"))["ok"] is False
    assert isinstance(city.retire_all("{}", NOW), str)
