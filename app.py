import logging
import requests
from config import policy, supported_methods, default_action, upstream_timeout, BLOCK
from werkzeug.exceptions import Forbidden, BadGateway
from flask import Flask, request, Response


app = Flask(__name__)

if __name__ != "__main__":
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

# headers that belong to a single connection and must not be forwarded
HOP_BY_HOP_HEADERS = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "proxy-connection", "te", "trailer", "trailers", "transfer-encoding", "upgrade",
}


def normalize_host(host):
    """Lowercase the host and drop the port: "WWW.X.com:80" -> "www.x.com"."""
    host = host.strip().lower().rstrip(".")
    if host.startswith("["):  # IPv6 literal, e.g. [::1]:80
        return host.split("]")[0] + "]"
    return host.split(":")[0]


def normalize_path(path):
    return "/".join(part for part in path.lower().split("/") if part)


def path_matches(rule_path, path):
    rule_path = normalize_path(rule_path)
    return not rule_path or path == rule_path or path.startswith(rule_path + "/")


# check the request according to configured policy
# and returns entry's action
def get_action_from_policy(host, method, path):
    host, method, path = normalize_host(host), method.upper(), normalize_path(path)
    app.logger.debug("Checking {} {} /{}".format(method, host, path))
    for (rule_host, rule_method, rule_path), action in policy:
        if (normalize_host(rule_host) == host and rule_method.upper() == method
                and path_matches(rule_path, path)):
            app.logger.info("Found a match, entry: {}".format((rule_host, rule_method, rule_path, action)))
            return action

    # didn't find any match in policy
    # returns default action
    app.logger.info("Didn't find a match, returning default action({})".format(default_action))
    return default_action


def filter_headers(headers):
    return [(k, v) for k, v in headers if k.lower() not in HOP_BY_HOP_HEADERS]


def send_request(host, path, query_string, method, headers, data=None):
    url = "http://{}/{}".format(host, path)
    if query_string:
        url += "?" + query_string
    app.logger.info("Forwarding request to {}".format(url))
    # redirects go back to the client, so the redirect target is checked by the policy too
    response = requests.request(url=url, method=method, headers=headers, data=data,
                                stream=True, allow_redirects=False, timeout=upstream_timeout)
    app.logger.info("Got response from {}, sending back to user".format(url))
    return response


@app.route("/", methods=supported_methods)
def empty_path():
    return proxy("")


@app.route("/<path:path>", methods=supported_methods)
def proxy(path=""):
    app.logger.debug("path is {}".format(path))
    action = get_action_from_policy(request.host, request.method, path)
    if action == BLOCK:
        raise Forbidden

    try:
        response = send_request(request.host, path, request.query_string.decode("latin-1"),
                                request.method, dict(filter_headers(request.headers.items())),
                                request.get_data())
    except requests.RequestException as e:
        app.logger.warning("Upstream request failed: {}".format(e))
        raise BadGateway

    # pass the body through as-is (still compressed if it was), so the
    # Content-Encoding and Content-Length headers stay correct
    body = response.raw.stream(64 * 1024, decode_content=False)
    return Response(body, response.status_code, filter_headers(response.raw.headers.items()))


if __name__ == "__main__":
    app.logger.setLevel(logging.DEBUG)
    app.run(host="0.0.0.0", port=5000)
