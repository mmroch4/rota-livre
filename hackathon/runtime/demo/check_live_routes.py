#!/usr/bin/env python3
"""Read-only retained MQTT snapshot → fixed 6% wheelchair route and trace check."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
import os
import secrets
import signal
import socket
import struct
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from barriers import Mqtt


class CheckError(Exception):
    def __init__(self, category, message):
        self.category = category
        super().__init__(message)


class Reader(Mqtt):
    """Reuse framing only; prohibit PUBLISH and bound every packet and collection."""
    def __init__(self, host, port, username, password, timeout=5):
        self.deadline = time.monotonic() + timeout
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.packet_id = 0
        try:
            flags = 2
            payload = self._str('live-check-' + secrets.token_hex(4))
            if username is not None:
                flags |= 128
                payload += self._str(username)
                if password is not None:
                    flags |= 64
                    payload += self._str(password)
            self._send(0x10, self._str('MQTT') + bytes([4, flags]) + struct.pack('>H', 30) + payload)
            kind, body = self._read()
            if kind != 0x20 or len(body) != 2 or body[0] != 0:
                raise CheckError('mqtt_protocol', 'Invalid CONNACK')
            if body[1]:
                raise CheckError('authentication' if body[1] in (4, 5) else 'mqtt_connection',
                                 f'CONNACK code {body[1]}')
        except BaseException:
            self.sock.close()
            raise

    def _send(self, header, body):
        if header not in (0x10, 0x82, 0xE0):
            raise CheckError('read_only', 'Only CONNECT, SUBSCRIBE and DISCONNECT permitted')
        self.sock.settimeout(max(0.001, self.deadline - time.monotonic()))
        super()._send(header, body)

    def _recv(self, count):
        data = bytearray()
        while len(data) < count:
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                raise socket.timeout()
            self.sock.settimeout(remaining)
            chunk = self.sock.recv(count - len(data))
            if not chunk:
                raise CheckError('mqtt_transport', 'Broker closed connection')
            data.extend(chunk)
        return bytes(data)

    def _read(self, first=None):
        header = (self._recv(1) if first is None else first)[0]
        length = 0
        for shift in range(0, 28, 7):
            byte = self._recv(1)[0]
            length |= (byte & 127) << shift
            if not byte & 128:
                if length > 1024 * 1024:
                    raise CheckError('mqtt_protocol', 'Packet exceeds 1 MiB limit')
                return header, self._recv(length)
        raise CheckError('mqtt_protocol', 'Invalid remaining length')

    def snapshot(self, prefix, idle=1.5, duration=8):
        end = time.monotonic() + duration
        self.deadline = end
        topic_root = prefix + '/barriers/'
        self._send(0x82, b'\x00\x01' + self._str(topic_root + '+') + b'\x00')
        records, acknowledged, updates = {}, False, 0
        while True:
            if time.monotonic() >= end:
                raise CheckError('snapshot_timeout', 'Busy broker: snapshot deadline reached')
            self.deadline = min(end, time.monotonic() + idle)
            # Only silence before a new packet can finish a snapshot. A partial
            # packet timing out is an incomplete snapshot, never success.
            try:
                first = self._recv(1)
            except socket.timeout:
                if time.monotonic() >= end or not acknowledged:
                    raise CheckError('snapshot_timeout', 'No complete quiet snapshot/SUBACK')
                return records, updates
            try:
                kind, body = self._read(first)
            except socket.timeout:
                raise CheckError('snapshot_timeout', 'Partial MQTT packet timed out') from None
            if kind == 0x90:
                if body != b'\x00\x01\x00':
                    raise CheckError('subscription', 'Subscription rejected or invalid SUBACK')
                acknowledged = True
            elif kind & 0xF0 == 0x30:
                if kind & 6 or len(body) < 2:
                    raise CheckError('mqtt_protocol', 'Expected QoS 0 PUBLISH')
                size = int.from_bytes(body[:2], 'big')
                if size == 0 or len(body) < 2 + size:
                    raise CheckError('mqtt_protocol', 'Truncated topic')
                try:
                    topic = body[2:2 + size].decode('utf-8')
                except UnicodeError:
                    raise CheckError('mqtt_protocol', 'Invalid topic encoding') from None
                suffix = topic[len(topic_root):] if topic.startswith(topic_root) else ''
                if not suffix or '/' in suffix:
                    continue
                if not kind & 1:
                    updates += 1
                    continue
                records[suffix] = body[2 + size:]
                if len(records) > 10000:
                    raise CheckError('snapshot_limit', 'More than 10000 records')
            else:
                raise CheckError('mqtt_protocol', 'Unexpected packet during subscription')


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def exclusion(lat, lon):
    dy = 15 / 111320
    dx = 15 / (111320 * math.cos(math.radians(lat)))
    return [[lon-dx, lat-dy], [lon+dx, lat-dy], [lon+dx, lat+dy],
            [lon-dx, lat+dy], [lon-dx, lat-dy]]


def classify(records, now):
    counts = dict.fromkeys(('retained_records', 'active_barriers', 'active_city_barriers',
                           'expired_records', 'invalid_records', 'missing_expiry_active'), 0)
    counts['retained_records'] = len(records)
    reasons, polygons = Counter(), []
    for identifier, payload in records.items():
        try:
            b = json.loads(payload)
            if not isinstance(b, dict) or not all(number(b.get(k)) for k in ('lat', 'lon')):
                raise ValueError('coordinates')
            polygon = exclusion(b['lat'], b['lon']) if abs(b['lat']) < 90 else []
            if not polygon or any(abs(lon) > 180 or abs(lat) > 90 for lon, lat in polygon):
                raise ValueError('coordinate_range')
            expiry = b.get('expires_at')
            # JavaScript falsy JSON values; empty lists/objects are truthy there.
            missing = expiry is None or expiry is False or expiry == '' or (number(expiry) and expiry == 0)
            if not missing:
                if not isinstance(expiry, str):
                    raise ValueError('expiry')
                try:
                    parsed = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
                    if parsed.tzinfo is None:
                        raise ValueError()
                except ValueError:
                    raise ValueError('expiry') from None
                if parsed <= now:
                    counts['expired_records'] += 1
                    continue
            counts['active_barriers'] += 1
            counts['active_city_barriers'] += identifier.startswith('city-')
            counts['missing_expiry_active'] += missing
            polygons.append(polygon)
        except (ValueError, TypeError, OverflowError) as error:
            counts['invalid_records'] += 1
            reason = str(error) if str(error) in ('coordinates', 'coordinate_range', 'expiry') else 'json'
            reasons[reason] += 1
    return counts, polygons, dict(reasons)


def post(base, path, body, timeout):
    request = Request(base.rstrip('/') + path, data=json.dumps(body, allow_nan=False).encode(),
                      headers={'Content-Type': 'text/plain'})
    status = 200
    try:
        try:
            response = urlopen(request, timeout=timeout)
        except HTTPError as error:
            response, status = error, error.code
        with response:
            raw = response.read(4 * 1024 * 1024 + 1)
        if len(raw) > 4 * 1024 * 1024:
            raise CheckError('invalid_response', path + ': response too large')
        data = json.loads(raw)
    except (URLError, OSError):
        raise CheckError('http_transport', path + ': connection/read failed') from None
    except (ValueError, UnicodeError):
        raise CheckError('invalid_response', f'{path}: HTTP {status}, invalid JSON') from None
    if not isinstance(data, dict):
        raise CheckError('invalid_response', path + ': expected JSON object')
    if 'error_code' in data:
        code = data['error_code']
        category = 'no_route' if code in (442, 443) else 'valhalla_error'
        # Do not echo arbitrary server text or request data.
        safe_code = code if type(code) is int else 'invalid'
        raise CheckError(category, f'{path}: Valhalla code {safe_code} (HTTP {status})')
    if status >= 400:
        raise CheckError('http_error', f'{path}: HTTP {status}')
    return data


def grade_summary(edges):
    if not isinstance(edges, list) or not edges or any(not isinstance(e, dict) for e in edges):
        raise CheckError('invalid_response', 'Trace requires nonempty edge objects')
    def group(items):
        up, down, missing, violations = [], [], 0, 0
        for edge in items:
            u, d = edge.get('max_upward_grade'), edge.get('max_downward_grade')
            if not number(u) or not number(d) or abs(u) == 32768 or abs(d) == 32768:
                missing += 1
                continue
            up.append(u)
            down.append(d)
            violations += not (0 <= u <= 6 and -6 <= d <= 0)
        return {'edges': len(items), 'max_up_percent': max(up, default=None),
                'min_down_percent': min(down, default=None), 'missing_elevation_edges': missing,
                'outside_cap_edges': violations}
    return {'interior': group(edges[1:-1]),
            'endpoint_candidates': group(edges[:1] + (edges[-1:] if len(edges) > 1 else []))}


def run(args, result):
    try:
        client = Reader(args.broker_host, args.broker_port, os.getenv('BROKER_USERNAME'),
                        os.getenv('BROKER_PASSWORD'), args.connect_timeout)
        try:
            records, updates = client.snapshot(args.topic_prefix, args.read_timeout, args.snapshot_timeout)
        finally:
            client.close()
    except OSError:
        raise CheckError('mqtt_transport', 'Broker connection/read failed or timed out') from None
    now = datetime.now(timezone.utc)
    counts, polygons, reasons = classify(records, now)
    result.update(snapshot_at=now.isoformat(), counts=counts, invalid_reasons=reasons,
                  concurrent_updates=updates, polygons=len(polygons), vertices=5*len(polygons))
    if updates:
        raise CheckError('snapshot_changed', 'Live updates during retained replay; retry snapshot')
    costing = {'costing': 'pedestrian', 'costing_options': {'pedestrian': {
        'type': 'wheelchair', 'max_grade': 6, 'step_penalty': 43200}}}
    route = post(args.valhalla_url, '/route', {**costing,
        'locations': [{'lat': 41.1455, 'lon': -8.6105}, {'lat': 41.1459, 'lon': -8.6064}],
        'exclude_polygons': polygons, 'units': 'kilometers', 'language': 'pt-PT'}, args.http_timeout)
    try:
        trip = route['trip']
        length, seconds = trip['summary']['length'], trip['summary']['time']
        shape = trip['legs'][0]['shape']
        if trip.get('status') != 0 or not isinstance(shape, str) or not shape or not all(
                number(n) and n >= 0 for n in (length, seconds)):
            raise ValueError()
    except (KeyError, IndexError, TypeError, ValueError):
        raise CheckError('invalid_response', 'Invalid route summary, status or shape') from None
    result['route'] = {'length_km': length, 'time_seconds': seconds}
    trace = post(args.valhalla_url, '/trace_attributes', {**costing, 'encoded_polyline': shape,
        'shape_match': 'edge_walk', 'filters': {'action': 'include', 'attributes': [
            'edge.length', 'edge.use', 'edge.max_upward_grade', 'edge.max_downward_grade',
            'edge.begin_shape_index', 'edge.end_shape_index']}}, args.http_timeout)
    result['grades'] = grade_summary(trace.get('edges'))
    interior = result['grades']['interior']
    if not interior['edges'] or interior['missing_elevation_edges'] or interior['outside_cap_edges']:
        raise CheckError('grade_check', 'Interior cap could not be verified within 6%')
    if counts['invalid_records']:
        raise CheckError('invalid_barriers', 'Invalid retained records excluded; inspect producer data')


def positive(value):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError('must be finite and positive')
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--broker-host', default=os.getenv('BROKER_HOST', '127.0.0.1'))
    parser.add_argument('--broker-port', type=int, default=os.getenv('BROKER_PORT', '1883'))
    parser.add_argument('--topic-prefix', default=os.getenv('TOPIC_PREFIX', 'access'))
    parser.add_argument('--valhalla-url', default=os.getenv('VALHALLA_URL', 'http://127.0.0.1:8003'))
    for name, default in [('connect', 5), ('read', 1.5), ('snapshot', 8), ('http', 20), ('overall', 55)]:
        parser.add_argument('--' + name + '-timeout', type=positive, default=default)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    if not args.topic_prefix or any(c in args.topic_prefix for c in '+#\x00') or args.topic_prefix.endswith('/'):
        parser.error('topic prefix must be a literal MQTT prefix without trailing slash')
    result = {'ok': False, 'cap_percent': 6}
    def timeout_handler(signum, frame):
        raise CheckError('overall_timeout', 'Overall check deadline reached')
    previous = signal.signal(signal.SIGALRM, timeout_handler)
    signal.setitimer(signal.ITIMER_REAL, args.overall_timeout)
    try:
        run(args, result)
        result['ok'] = True
    except CheckError as error:
        result['error'] = {'category': error.category, 'message': str(error)}
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
    if args.json:
        print(json.dumps(result, allow_nan=False))
    else:
        print('PASS' if result['ok'] else 'FAIL', '— live barrier check; fixed 6% cap')
        for key in ('snapshot_at', 'counts', 'invalid_reasons', 'concurrent_updates', 'polygons', 'vertices', 'route', 'grades', 'error'):
            if key in result:
                print(f'{key}: {json.dumps(result[key])}')
        print('Endpoint candidates are separate from the interior cap check. Not accessibility certification.')
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
