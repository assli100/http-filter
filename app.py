import logging
import requests
from config import policy, supported_methods, default_action, PASS, BLOCK
from werkzeug.exceptions import Forbidden
from flask import Flask, request, Response


app = Flask(__name__)

if __name__ != "__main__":
    try:
        gunicorn_logger = logging.getLogger("gunicorn.error")
        app.logger.handlers = gunicorn_logger.handlers
        app.logger.setLevel(gunicorn_logger.level)
    except Exception as e:
        pass

# check the request according to configured policy
# and returns entry's action 
def get_action_from_policy(host, method, path):
    for entry in policy:
        app.logger.debug("{}, {}, {}".format(host, method, path))
        if (host, method, path) == entry[0]:
            app.logger.info("Found a match, entry: {}".format(entry))
            return entry[1]
    
    # didn't find any match in policy
    # returns default action
    app.logger.info("Didn't find a match, returning default action({})".format(default_action))
    return default_action

def send_request(host, path, method, headers={}, data=None):
    url = "http://{}/{}".format(host, path)
    app.logger.info("Forwarding request to {}".format(url))
    response = requests.request(url=url, method=method, headers=headers, data=data, stream=True)
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
    
    response = send_request(request.host, "", request.method, dict(request.headers), request.data)

    # return as flask Response
    return Response(response.content, response.status_code, response.headers.items())


if __name__ == "__main__":
    app.logger.setLevel(logging.DEBUG)
    app.run(host="0.0.0.0", port=5000)
