import flask
from flask import Flask, request
import socket

app = Flask(__name__)


@app.route('/checkheartbeat')
def heartbeat():
    return flask.jsonify(msg="im-alive")


@app.route('/<path:path>', methods=["GET", "POST", "DELETE"])
def sayHello(path):
    return f"{path} {request.method} {socket.gethostname()}"


if __name__ == "__main__":
    app.run(debug=True, port=80, host='0.0.0.0')