#!/usr/bin/env python3
"""Check, and after a broker restart repair, the live LoT of Miguel's notebooks.

    redeploy_lot.py [--check]   one line per Action / Python script: IDENTICAL, DIFFERS or NOT LIVE; exit 1 on any mismatch
    redeploy_lot.py --fix       resend what differs through $SYS/Coreflux/Command, then check again

Why: every broker boot can restore an older ImportCityAlerts (AGENTS.md, "Broker 2.22.0 quirks"). After a restart:

    docker restart o1n-broker && sleep 10 && python3 hackathon/broker/redeploy_lot.py --fix

Only the notebooks in NOTEBOOKS are read. Routes, panels and other people's entities are never sent, and nothing is
removed. A Python script's live source cannot be read back, so it is only checked for presence; --fix resends every
Python cell of a notebook before that notebook's Actions. The command channel strips `//`, `/* */` and `-- ` outside
string literals, so a Python cell with `a // b` in plain code fails to deploy (loudly) through this script.

Talks plain MQTT 3.1.1 through runtime/demo/barriers.py (stdlib only). Login from BROKER_USERNAME / BROKER_PASSWORD,
never printed. Defaults to 127.0.0.1:1883.
"""
import argparse
import json
import pathlib
import re
import secrets
import socket
import struct
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
LOT = HERE.parent / "lot"
NOTEBOOKS = ("barrier_feedback.lotnb", "city_alerts.lotnb", "ops_panel.lotnb")
COMMAND_TOPIC = "$SYS/Coreflux/Command"
OUTPUT_TOPIC = "$SYS/Coreflux/Command/Output"
ACTION_TOPIC = "$SYS/Coreflux/Actions/{}"

DEFINE = re.compile(r'^DEFINE\s+(\w+)\s+"?([\w-]+)"?', re.MULTILINE)
SCRIPT_NAME = re.compile(r"^#\s*Script Name:\s*(\w+)", re.MULTILINE)


# ---- pure parts (tested in services/tests/test_redeploy_lot.py) ----

def split_blocks(text):
    """Split a LoT cell into its DEFINE blocks: [(kind, name, source)], kind upper case."""
    starts = list(DEFINE.finditer(text))
    blocks = []
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        blocks.append((match.group(1).upper(), match.group(2), text[match.start():end].rstrip()))
    return blocks


def extract(cells, notebook):
    """Actions and Python scripts of a notebook, in cell order: [{kind, name, source, notebook}]."""
    entities = []
    for cell in cells:
        if cell.get("kind") != 2:
            continue
        text = cell.get("value", "")
        if cell.get("language") == "python":
            match = SCRIPT_NAME.search(text)
            if match:
                entities.append({"kind": "python", "name": match.group(1), "source": text.rstrip(),
                                 "notebook": notebook})
        elif cell.get("language") == "lot":
            for kind, name, source in split_blocks(text):
                if kind == "ACTION":
                    entities.append({"kind": "action", "name": name, "source": source, "notebook": notebook})
    return entities


def normalise(source):
    """Drop trailing whitespace and blank lines."""
    return "\n".join(line.rstrip() for line in source.splitlines() if line.strip())


def status(entity, live_names, live_source):
    """IDENTICAL, DIFFERS or NOT LIVE. Python is IDENTICAL when present, since its source cannot be read back."""
    if entity["name"] not in live_names:
        return "NOT LIVE"
    if entity["kind"] == "python":
        return "IDENTICAL"
    if live_source is None:
        return "DIFFERS"
    return "IDENTICAL" if normalise(entity["source"]) == normalise(live_source) else "DIFFERS"


def plan_fix(entities, statuses):
    """What to send, in order: for each notebook with a mismatch, all its Python cells, then its mismatched Actions."""
    plan = []
    for notebook in dict.fromkeys(entity["notebook"] for entity in entities):
        own = [entity for entity in entities if entity["notebook"] == notebook]
        if all(statuses[entity["name"]] == "IDENTICAL" for entity in own):
            continue
        plan += [entity for entity in own if entity["kind"] == "python"]
        plan += [entity for entity in own if entity["kind"] == "action" and statuses[entity["name"]] != "IDENTICAL"]
    return plan


def command(entity, request_id):
    """The $SYS/Coreflux/Command payload that deploys one entity. -requestId must be the last token."""
    verb = "-addPython" if entity["kind"] == "python" else "-addAction"
    return f"{verb} {entity['source'].rstrip()} -requestId {request_id}"


def parse_reply(payload, request_id):
    """The Command/Output reply for request_id as a dict, or None for anyone else's reply."""
    try:
        reply = json.loads(payload)
    except ValueError:
        return None
    return reply if isinstance(reply, dict) and reply.get("requestId") == request_id else None


def load_entities():
    entities = []
    for notebook in NOTEBOOKS:
        entities += extract(json.loads((LOT / notebook).read_text()), notebook)
    return entities


# ---- broker I/O ----

class Broker:
    """One MQTT session: commands with replies, and retained reads. Uses the Mqtt internals of barriers.py."""

    def __init__(self):
        sys.path.insert(0, str(HERE.parent / "runtime" / "demo"))
        from barriers import connect
        self.client = connect()
        self._subscribe(OUTPUT_TOPIC)
        self._messages(0.5)  # SUBACK

    def _subscribe(self, topic):
        client = self.client
        client._send(0x82, struct.pack(">H", client._next_id()) + client._str(topic) + b"\x00")

    def _messages(self, timeout):
        """Yield (retained, topic, payload) for each PUBLISH until `timeout` seconds pass."""
        deadline = time.monotonic() + timeout
        while (left := deadline - time.monotonic()) > 0:
            self.client.sock.settimeout(left)
            try:
                header, body = self.client._read()
            except socket.timeout:
                return
            if header & 0xF0 == 0x30:  # we subscribe at QoS 0, so no packet id
                size = struct.unpack(">H", body[:2])[0]
                yield bool(header & 0x01), body[2:2 + size].decode(), body[2 + size:]

    def request(self, payload_without_id, timeout=30):
        """Send a command and return its reply dict (None on timeout)."""
        request_id = "redeploy-" + secrets.token_hex(4)
        self.client._send(0x30, self.client._str(COMMAND_TOPIC) + f"{payload_without_id} -requestId {request_id}".encode())
        return self._wait(request_id, timeout)

    def deploy(self, entity, timeout=30):
        request_id = "redeploy-" + secrets.token_hex(4)
        self.client._send(0x30, self.client._str(COMMAND_TOPIC) + command(entity, request_id).encode())
        return self._wait(request_id, timeout)

    def _wait(self, request_id, timeout):
        for _, topic, payload in self._messages(timeout):
            if topic == OUTPUT_TOPIC and (reply := parse_reply(payload, request_id)):
                return reply
        return None

    def live_names(self):
        reply = self.request("-listEntities")
        if not reply or not reply.get("success"):
            raise SystemExit(f"-listEntities failed: {reply and reply.get('message')}")
        return {entity["name"] for entity in reply["data"].get("entities", [])}

    def retained(self, topic, timeout=3):
        """The retained payload of one exact topic (decoded), or None."""
        self._subscribe(topic)
        for retained, received, payload in self._messages(timeout):
            if retained and received == topic:
                return payload.decode()
        return None

    def close(self):
        self.client.close()


def check(broker, entities, quiet=False):
    names = broker.live_names()
    statuses = {}
    for entity in entities:
        source = broker.retained(ACTION_TOPIC.format(entity["name"])) if entity["kind"] == "action" and entity["name"] in names else None
        statuses[entity["name"]] = status(entity, names, source)
        if not quiet:
            note = "  (presence only)" if entity["kind"] == "python" else ""
            print(f"{statuses[entity['name']]:<10} {entity['kind']:<7} {entity['name']:<22} {entity['notebook']}{note}")
    return statuses


def fix(entities):
    broker = Broker()
    try:
        statuses = check(broker, entities)
        plan = plan_fix(entities, statuses)
        if not plan:
            print("Nothing to fix.")
            return 0
        for entity in plan:
            reply = broker.deploy(entity)
            if reply is None:
                raise SystemExit(f"FAILED  {entity['kind']} {entity['name']}: no reply on {OUTPUT_TOPIC}")
            if not reply.get("success"):
                error = (reply.get("errors") or [{}])[0].get("message", "")
                raise SystemExit(f"FAILED  {entity['kind']} {entity['name']}: {reply.get('message')} {error[:300]}")
            print(f"SENT       {entity['kind']:<7} {entity['name']}")
        # The retained Actions/<Name> source is republished periodically (~7 s); -updateData asks for it now (no reply).
        broker.client._send(0x30, broker.client._str(COMMAND_TOPIC) + b"-updateData")
    finally:
        broker.close()
    print("Checking again...")
    for _ in range(10):
        time.sleep(3)
        broker = Broker()
        try:
            statuses = check(broker, entities, quiet=True)
        finally:
            broker.close()
        if all(value == "IDENTICAL" for value in statuses.values()):
            break
    return report_final(entities)


def report_final(entities):
    broker = Broker()
    try:
        statuses = check(broker, entities)
    finally:
        broker.close()
    return 0 if all(value == "IDENTICAL" for value in statuses.values()) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="compare only (default)")
    mode.add_argument("--fix", action="store_true", help="resend what differs, then check again")
    args = parser.parse_args()
    entities = load_entities()
    if args.fix:
        return fix(entities)
    return report_final(entities)


if __name__ == "__main__":
    sys.exit(main())
