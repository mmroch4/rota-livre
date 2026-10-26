#!/usr/bin/env python3
"""Seed, list or clear the demo barriers on the local Coreflux broker.

    barriers.py seed [--with-control]   publish the demo barriers (retained, QoS 1)
    barriers.py list                    print every retained barrier on access/barriers/+
    barriers.py clear                   remove the demo-* barriers, nothing else

Talks plain MQTT 3.1.1 over TCP with the standard library only (no paho, no install).
Login comes from BROKER_USERNAME / BROKER_PASSWORD; it is never printed. Defaults to 127.0.0.1:1883.
"""
import argparse
import json
import os
import secrets
import socket
import struct
import sys
import time
from datetime import datetime, timedelta, timezone

TOPIC_PREFIX = os.environ.get("TOPIC_PREFIX", "access") + "/barriers"
ID_PREFIX = "demo-"
TTL = timedelta(hours=24)

# São Bento -> Batalha, wheelchair profile (6 %): 1.302 km without barriers.
# Lengths are for the route with that barrier alone; both together give 1.856 km.
DEMO_BARRIERS = [
    {"id": "demo-roadworks", "kind": "works", "lat": 41.14384, "lon": -8.60766,
     "description": "Obras no passeio: passagem cortada."},       # 1.302 -> 1.721 km
    {"id": "demo-parked-car", "kind": "parked_car", "lat": 41.14494, "lon": -8.61080,
     "description": "Carro estacionado a bloquear o passeio."},   # 1.302 -> 1.437 km
]
# Off the route: showing it must not change the route (1.302 km).
CONTROL_BARRIER = {"id": "demo-control", "kind": "damaged_pavement", "lat": 41.1468, "lon": -8.6085,
                   "description": "Pavimento danificado, longe do percurso."}


class Mqtt:
    """Just enough MQTT 3.1.1: connect, publish at QoS 1, subscribe and collect retained messages."""

    def __init__(self, host, port, username, password):
        self.sock = socket.create_connection((host, port), timeout=5)
        self.packet_id = 0
        client_id = "demo-barriers-" + secrets.token_hex(4)
        flags = 0x02  # clean session
        payload = self._str(client_id)
        if username is not None:
            flags |= 0x80
            payload += self._str(username)
            if password is not None:
                flags |= 0x40
                payload += self._str(password)
        self._send(0x10, self._str("MQTT") + bytes([4, flags]) + struct.pack(">H", 30) + payload)
        kind, body = self._read()
        if kind != 0x20 or len(body) != 2 or body[1] != 0:
            code = body[1] if len(body) == 2 else "?"
            raise SystemExit(f"Broker refused the connection (CONNACK code {code}; 4/5 = bad login).")

    @staticmethod
    def _str(text):
        data = text.encode()
        return struct.pack(">H", len(data)) + data

    def _send(self, header, body):
        length, remaining = bytearray(), len(body)
        while True:
            byte, remaining = remaining % 128, remaining // 128
            length.append(byte | (0x80 if remaining else 0))
            if not remaining:
                break
        self.sock.sendall(bytes([header]) + bytes(length) + body)

    def _recv(self, count):
        data = b""
        while len(data) < count:
            chunk = self.sock.recv(count - len(data))
            if not chunk:
                raise SystemExit("Broker closed the connection.")
            data += chunk
        return data

    def _read(self):
        """Read one packet; returns (header byte, body). Raises socket.timeout when idle."""
        header = self._recv(1)[0]
        length, shift = 0, 0
        while True:
            byte = self._recv(1)[0]
            length |= (byte & 0x7F) << shift
            shift += 7
            if not byte & 0x80:
                break
        return header, self._recv(length)

    def _next_id(self):
        self.packet_id = self.packet_id % 65535 + 1
        return self.packet_id

    def publish(self, topic, payload, retain=True):
        packet_id = self._next_id()
        body = self._str(topic) + struct.pack(">H", packet_id) + payload
        self._send(0x32 | (1 if retain else 0), body)  # PUBLISH, QoS 1
        while True:
            kind, ack = self._read()
            if kind == 0x40 and ack[:2] == struct.pack(">H", packet_id):
                return

    def collect(self, topic_filter, idle=1.5):
        """Subscribe at QoS 0 and return {topic: payload} until the broker is quiet for `idle` seconds."""
        packet_id = self._next_id()
        self._send(0x82, struct.pack(">H", packet_id) + self._str(topic_filter) + b"\x00")
        messages = {}
        self.sock.settimeout(idle)
        try:
            while True:
                kind, body = self._read()
                if kind & 0xF0 == 0x30:  # PUBLISH (QoS 0, so no packet id)
                    size = struct.unpack(">H", body[:2])[0]
                    messages[body[2:2 + size].decode()] = body[2 + size:]
        except socket.timeout:
            return messages

    def close(self):
        try:
            self._send(0xE0, b"")
        except OSError:
            pass
        self.sock.close()


def connect():
    host = os.environ.get("BROKER_HOST", "127.0.0.1")
    port = int(os.environ.get("BROKER_PORT", "1883"))
    return Mqtt(host, port, os.environ.get("BROKER_USERNAME"), os.environ.get("BROKER_PASSWORD"))


def iso(moment):
    return moment.isoformat(timespec="seconds").replace("+00:00", "Z")


def seed(with_control):
    now = datetime.now(timezone.utc)
    barriers = DEMO_BARRIERS + ([CONTROL_BARRIER] if with_control else [])
    client = connect()
    for barrier in barriers:
        message = {
            "id": barrier["id"], "kind": barrier["kind"], "description": barrier["description"],
            "lat": barrier["lat"], "lon": barrier["lon"],
            "reported_at": iso(now), "expires_at": iso(now + TTL),
        }
        client.publish(f"{TOPIC_PREFIX}/{barrier['id']}", json.dumps(message, ensure_ascii=False).encode())
        print(f"seeded {barrier['id']} ({barrier['kind']}) at {barrier['lat']},{barrier['lon']}")
    client.close()
    print(f"Expires {iso(now + TTL)}. Seeding again just refreshes the same ids.")


def retained(client):
    """Retained barriers as {id: payload text}; only direct children of the barriers topic."""
    found = client.collect(f"{TOPIC_PREFIX}/+")
    return {topic.rsplit("/", 1)[1]: payload.decode(errors="replace") for topic, payload in found.items()}


def list_barriers():
    client = connect()
    found = retained(client)
    client.close()
    if not found:
        print("No retained barriers.")
    for barrier_id in sorted(found):
        try:
            b = json.loads(found[barrier_id])
            print(f"{barrier_id}  {b['kind']}  {b['lat']},{b['lon']}  expires {b['expires_at']}  {b['description']!r}")
        except (ValueError, KeyError, TypeError):
            print(f"{barrier_id}  (unreadable payload)")


def clear():
    client = connect()
    # Only demo-* topics: the known ids plus any other demo- one that is retained now.
    ids = {b["id"] for b in DEMO_BARRIERS + [CONTROL_BARRIER]}
    ids |= {i for i in retained(client) if i.startswith(ID_PREFIX)}
    for barrier_id in sorted(ids):
        client.publish(f"{TOPIC_PREFIX}/{barrier_id}", b"")
        print(f"cleared {barrier_id}")
    client.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("seed").add_argument("--with-control", action="store_true",
                                        help="also seed demo-control, off the route (should change nothing)")
    sub.add_parser("list")
    sub.add_parser("clear")
    args = parser.parse_args()
    if args.command == "seed":
        seed(args.with_control)
    elif args.command == "list":
        list_barriers()
    else:
        clear()


if __name__ == "__main__":
    sys.exit(main())
