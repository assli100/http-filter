import unittest
from unittest import mock

import requests

import app as proxy_app
from app import app, get_action_from_policy
from config import PASS, BLOCK


class PolicyTest(unittest.TestCase):
    def test_block_cannot_be_bypassed(self):
        for host, path in [("www.malicious.com", "malicious"),
                           ("WWW.MALICIOUS.COM", "malicious"),
                           ("www.malicious.com:80", "malicious"),
                           ("www.malicious.com.", "malicious"),
                           ("www.malicious.com", "Malicious/"),
                           ("www.malicious.com", "malicious/sub/page"),
                           ("www.malicious.com", "/malicious")]:
            self.assertEqual(get_action_from_policy(host, "GET", path), BLOCK, (host, path))

    def test_pass(self):
        self.assertEqual(get_action_from_policy("www.malicious.com", "GET", "maliciousness"), PASS)
        self.assertEqual(get_action_from_policy("www.malicious.com", "GET", ""), PASS)
        self.assertEqual(get_action_from_policy("www.google.co.il", "GET", "bad"), PASS)
        self.assertEqual(get_action_from_policy("www.google.co.il", "post", "bad"), BLOCK)


class FakeRaw(object):
    def __init__(self, body, headers):
        self.body = body
        self.headers = mock.Mock()
        self.headers.items.return_value = headers

    def stream(self, size, decode_content=True):
        assert decode_content is False
        yield self.body


class ProxyTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    @mock.patch("app.requests.request")
    def test_forwards_path_query_and_body(self, request):
        request.return_value = mock.Mock(status_code=201, raw=FakeRaw(
            b"\x1f\x8bzipped", [("Content-Encoding", "gzip"), ("Content-Length", "8"),
                                ("Set-Cookie", "a=1"), ("Set-Cookie", "b=2"),
                                ("Connection", "keep-alive")]))
        res = self.client.post("/some/path?x=1&y=2", base_url="http://example.com",
                               data={"field": "value"}, headers={"Proxy-Connection": "keep-alive"})
        kwargs = request.call_args.kwargs
        self.assertEqual(kwargs["url"], "http://example.com/some/path?x=1&y=2")
        self.assertEqual(kwargs["data"], b"field=value")
        self.assertFalse(kwargs["allow_redirects"])
        self.assertNotIn("Proxy-Connection", kwargs["headers"])
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data, b"\x1f\x8bzipped")
        self.assertEqual(res.headers["Content-Encoding"], "gzip")
        self.assertEqual(res.headers.getlist("Set-Cookie"), ["a=1", "b=2"])
        self.assertNotIn("Connection", res.headers)

    @mock.patch("app.requests.request")
    def test_blocked(self, request):
        res = self.client.get("/MALICIOUS/x", base_url="http://www.malicious.com")
        self.assertEqual(res.status_code, 403)
        request.assert_not_called()

    @mock.patch("app.requests.request", side_effect=requests.ConnectionError("down"))
    def test_upstream_down(self, request):
        res = self.client.get("/", base_url="http://example.com")
        self.assertEqual(res.status_code, 502)


if __name__ == "__main__":
    unittest.main()
