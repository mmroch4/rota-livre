"""Offline verification only: no real broker, HTTP requests or MQTT publications."""
import io
import json
import socket
import time
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import check_live_routes as live


NOW = datetime(2026, 10, 24, 12, tzinfo=timezone.utc)


def payload(**extra):
    return json.dumps({'lat': 41.1455, 'lon': -8.6105, **extra}).encode()


class FakeSocket:
    def __init__(self, data=b'', repeat=False, delay=0):
        self.data, self.repeat, self.delay = data, repeat, delay
        self.index = 0
        self.sent = []

    def settimeout(self, value):
        self.timeout = value

    def recv(self, count):
        if self.delay:
            time.sleep(min(self.delay, self.timeout))
        if self.index >= len(self.data):
            if self.repeat:
                self.index = 0
            else:
                raise socket.timeout()
        out = self.data[self.index:self.index + min(count, 1)]
        self.index += len(out)
        return out

    def sendall(self, data):
        self.sent.append(data)

    def close(self):
        pass


def reader(data, **kwargs):
    client = live.Reader.__new__(live.Reader)
    client.sock = FakeSocket(data, **kwargs)
    client.deadline = time.monotonic() + 1
    return client


def publish(topic, data, retained=True):
    body = live.Mqtt._str(topic) + data
    assert len(body) < 128
    return bytes([0x31 if retained else 0x30, len(body)]) + body


class BarrierTests(unittest.TestCase):
    def test_expiry_and_city_retirement(self):
        records = {'city-active': payload(expires_at='2026-10-24T14:00:00+01:00'),
                   'city-retired': payload(expires_at='2026-10-24T11:00:00Z'),
                   'equal': payload(expires_at='2026-10-24T12:00:00Z')}
        counts, polygons, _ = live.classify(records, NOW)
        self.assertEqual((counts['retained_records'], counts['active_city_barriers'],
                          counts['expired_records'], len(polygons)), (3, 1, 2, 1))

    def test_missing_and_falsy_expiry_match_app(self):
        records = {str(i): payload(expires_at=e) for i, e in enumerate([None, '', False, 0])}
        records['absent'] = payload()
        counts, _, _ = live.classify(records, NOW)
        self.assertEqual(counts['missing_expiry_active'], 5)

    def test_malformed_and_stricter_validation(self):
        records = {'bool': payload(lat=True), 'string': payload(lat='41'),
                   'range': payload(lat=91), 'nan': payload(lat=float('nan')),
                   'date': payload(expires_at='not-a-date'), 'naive': payload(expires_at='2026-10-25'),
                   'list': b'[]', 'bad': b'{', 'empty': b'', 'expiry_array': payload(expires_at=[])}
        counts, polygons, _ = live.classify(records, NOW)
        self.assertEqual(counts['invalid_records'], len(records))
        self.assertEqual(polygons, [])

    def test_polygon_matches_app(self):
        ring = live.exclusion(41.1455, -8.6105)
        self.assertEqual(len(ring), 5)
        self.assertEqual(ring[0], ring[-1])
        self.assertAlmostEqual(ring[2][1] - 41.1455, 15 / 111320)
        self.assertLess(ring[0][0], -8.6105)
        self.assertGreater(ring[1][0], -8.6105)


class MqttTests(unittest.TestCase):
    def test_retained_direct_children_and_updates(self):
        client = reader(b'\x90\x03\x00\x01\x00' +
                        publish('access/barriers/city-1', b'{}') +
                        publish('access/barriers/a/feedback', b'{}') +
                        publish('access/barriers/a', b'{}', False))
        records, updates = client.snapshot('access')
        self.assertEqual(records, {'city-1': b'{}'})
        self.assertEqual(updates, 1)
        self.assertEqual(client.sock.sent[0][0], 0x82)

    def test_suback_rejected_or_missing(self):
        for data in (b'\x90\x03\x00\x01\x80', b''):
            with self.assertRaises(live.CheckError):
                reader(data).snapshot('access')

    def test_partial_packet_is_failure(self):
        with self.assertRaises(live.CheckError) as error:
            reader(b'\x90\x03\x00\x01\x00\x31\x05\x00').snapshot('access')
        self.assertEqual(error.exception.category, 'snapshot_timeout')

    def test_continuously_busy_broker_bounded(self):
        start = time.monotonic()
        with self.assertRaises(live.CheckError) as error:
            reader(b'\x90\x03\x00\x01\x00', repeat=True, delay=.001).snapshot(
                'access', idle=.02, duration=.03)
        self.assertEqual(error.exception.category, 'snapshot_timeout')
        self.assertLess(time.monotonic() - start, .3)

    def test_slow_packet_bound_and_bad_length(self):
        client = reader(b'\x30\x7f' + b'x' * 127, delay=.003)
        client.deadline = time.monotonic() + .02
        with self.assertRaises(socket.timeout):
            client._read()
        with self.assertRaises(live.CheckError):
            reader(b'\x30\xff\xff\xff\xff')._read()

    def test_authentication_failure_and_no_publish(self):
        with patch.object(live.socket, 'create_connection', return_value=FakeSocket(b'\x20\x02\x00\x05')):
            with self.assertRaises(live.CheckError) as error:
                live.Reader('localhost', 1883, 'test', 'test')
        self.assertEqual(error.exception.category, 'authentication')
        with self.assertRaises(live.CheckError):
            reader(b'')._send(0x31, b'')


class HttpAndGradeTests(unittest.TestCase):
    def test_overall_deadline_returns_json_failure(self):
        output = io.StringIO()
        with patch.object(live, 'run', side_effect=lambda *args: time.sleep(.2)), patch('sys.stdout', output):
            self.assertEqual(live.main(['--json', '--overall-timeout', '.01']), 1)
        self.assertEqual(json.loads(output.getvalue())['error']['category'], 'overall_timeout')

    def test_invalid_route_response(self):
        with patch.object(live, 'Reader') as client, patch.object(live, 'post', return_value={'trip': {}}):
            client.return_value.snapshot.return_value = ({}, 0)
            output = io.StringIO()
            with patch('sys.stdout', output):
                self.assertEqual(live.main(['--json']), 1)
            self.assertEqual(json.loads(output.getvalue())['error']['category'], 'invalid_response')

    def test_errors_and_no_route(self):
        for code, category in [(176, 'valhalla_error'), (442, 'no_route'), (443, 'no_route')]:
            error = HTTPError('http://localhost', 400, 'bad', {}, io.BytesIO(json.dumps({'error_code': code}).encode()))
            with patch.object(live, 'urlopen', side_effect=error):
                with self.assertRaises(live.CheckError) as caught:
                    live.post('http://localhost', '/route', {}, 1)
            self.assertEqual(caught.exception.category, category)
            self.assertIn(str(code), str(caught.exception))

    def test_invalid_json_transport_and_content_type(self):
        with patch.object(live, 'urlopen', return_value=io.BytesIO(b'no')) as request:
            with self.assertRaises(live.CheckError) as caught:
                live.post('http://localhost', '/route', {}, 1)
            self.assertEqual(caught.exception.category, 'invalid_response')
            self.assertEqual(request.call_args.args[0].get_header('Content-type'), 'text/plain')
        with patch.object(live, 'urlopen', side_effect=URLError('private detail')):
            with self.assertRaises(live.CheckError) as caught:
                live.post('http://localhost', '/route', {}, 1)
            self.assertEqual(caught.exception.category, 'http_transport')
            self.assertNotIn('private', str(caught.exception))

    def test_percent_endpoints_missing_and_violations(self):
        def edge(up, down):
            return {'max_upward_grade': up, 'max_downward_grade': down}
        result = live.grade_summary([edge(16, -10), edge(6, -6), edge(32768, 0), edge(7, -8), {}])
        self.assertEqual(result['interior']['max_up_percent'], 7)
        self.assertEqual(result['interior']['missing_elevation_edges'], 1)
        self.assertEqual(result['interior']['outside_cap_edges'], 1)
        self.assertEqual(result['endpoint_candidates']['outside_cap_edges'], 1)


if __name__ == '__main__':
    unittest.main()
