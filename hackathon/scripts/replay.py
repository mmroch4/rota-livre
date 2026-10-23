"""Publishes the contract fixtures (hackathon/fixtures/messages/) so each track can work alone.

Every fixture is one example message of the topic map in hackathon/README.md. The dashboard,
planner, simulator and Actions can be built against these before the real producer exists.

    python hackathon/scripts/replay.py --list                    # topic table of every fixture
    python hackathon/scripts/replay.py                           # publish all fixtures once
    python hackathon/scripts/replay.py --only plans telemetry    # only files whose name matches
    python hackathon/scripts/replay.py --only config --clock     # config, then tick the sim clock
    python hackathon/scripts/replay.py --only hot --edge         # one edge case: cold room at 6.2 °C
    python hackathon/scripts/replay.py --clear                   # wipe every retained fixture topic

--clock stands in for the SimClock Action: it publishes copilot/clock/slot (retained) from
--start to the last price slot, one slot per --tick seconds.
"""

import argparse
import json
import pathlib
import sys
import time

import paho.mqtt.client as mqtt

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "messages"
SLOT_TOPIC = "copilot/clock/slot"
PRICES_FIXTURE = "market.prices"


def load_fixtures(only, edge=True):
    """Returns (file stem, message) pairs in file order, filtered by name substrings.

    Edge-case fixtures (a 404, an infeasible plan, a hot cold room) share a topic with a normal
    fixture, so they are skipped unless asked for; otherwise they would win as the retained value.
    """
    fixtures = []
    for path in sorted(FIXTURES.glob("*.json")):
        message = json.loads(path.read_text())
        if only and not any(word in path.stem for word in only):
            continue
        if message.get("edge") and not edge:
            continue
        fixtures.append((path.stem, message))
    return fixtures


def encode(payload):
    """Strings and numbers go out as plain text; objects and lists as JSON."""
    if isinstance(payload, str):
        return payload
    return json.dumps(payload, ensure_ascii=False)


def connect(args):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(args.user, args.password)
    client.connect(args.host, args.port)
    client.loop_start()
    return client


def publish(client, topic, payload, retain):
    client.publish(topic, payload, qos=1, retain=retain).wait_for_publish(timeout=5)


def tick_clock(client, args):
    prices = next(m for name, m in load_fixtures(None) if name.endswith(PRICES_FIXTURE))
    last = len(prices["payload"]["prices"]) - 1
    times = prices["payload"]["times"]
    for slot in range(args.start, last + 1):
        publish(client, SLOT_TOPIC, str(slot), retain=True)
        print(f"{SLOT_TOPIC} = {slot} ({times[slot]})")
        time.sleep(args.tick)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", default="coreflux")
    parser.add_argument("--only", nargs="+", metavar="WORD", help="only fixtures whose file name contains WORD")
    parser.add_argument("--edge", action="store_true", help="also publish edge-case fixtures (404, infeasible, hot)")
    parser.add_argument("--list", action="store_true", help="print the fixtures and exit")
    parser.add_argument("--clear", action="store_true", help="publish empty retained messages to every fixture topic")
    parser.add_argument("--clock", action="store_true", help="after publishing, tick copilot/clock/slot")
    parser.add_argument("--start", type=int, default=32, help="first slot for --clock (32 = 08:00)")
    parser.add_argument("--tick", type=float, default=1.0, help="seconds per slot for --clock")
    args = parser.parse_args()

    if args.list:
        for name, message in load_fixtures(args.only):
            flags = ("R" if message["retain"] else " ") + ("E" if message.get("edge") else " ")
            print(f"{flags} {message['topic']:<45} {name}")
        print("\nR = retained, E = edge case (only with --edge)")
        return
    fixtures = load_fixtures(args.only, edge=args.edge)
    if not fixtures and not args.clock:
        sys.exit(f"No fixture matches {args.only}")

    client = connect(args)
    try:
        if args.clear:
            topics = {m["topic"] for _, m in load_fixtures(None) if m["retain"]} | {SLOT_TOPIC}
            for topic in sorted(topics):
                publish(client, topic, b"", retain=True)
                print(f"cleared {topic}")
            return
        for name, message in fixtures:
            publish(client, message["topic"], encode(message["payload"]), message["retain"])
            print(f"{'R' if message['retain'] else ' '} {message['topic']:<45} {name}")
        if args.clock:
            tick_clock(client, args)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
