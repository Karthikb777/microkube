import time
import redis
import requests
import threading
from flask import Flask, request, jsonify


class HeartBeat:
    def __init__(self):
        self.brain = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

    def check_health(self):
        while True:
            if len(self.brain.keys(pattern="*")) != 0:
                for server in self.brain.keys(pattern="*"):
                    url = f'http://{server}/checkheartbeat'
                    try:
                        # if the response time is > 1 second, we consider the server as dead
                        response = requests.get(url, timeout=1, verify=False)
                        if 200 <= response.status_code < 400:
                            self.brain.set(server, "healthy")
                        else:
                            self.brain.set(server, "dead")
                    except Exception as e:
                        self.brain.set(server, "dead")
            print(self.brain)
            time.sleep(10)  # sleep for 60 seconds

    """
        stops and restarts an unhealthy server
    """

    # send a request to the auto-scaler to restart the server
    def resurrect(self):
        pass


app = Flask(__name__)
heartbeat = HeartBeat()


@app.route('/ishealthy')
def return_is_healthy():
    args = request.args.to_dict()
    server = args.get("server")
    return jsonify(status=heartbeat.brain.get(server))


@app.route('/add-server')
def add_server():
    args = request.args.to_dict()
    server = args.get("server")
    heartbeat.brain.set(server, "healthy")
    return jsonify(msg="server added")


@app.route('/remove-server')
def remove_server():
    args = request.args.to_dict()
    server = args.get("server")
    heartbeat.brain.delete(server)
    return jsonify(msg="server removed")


# THIS IS FOR DEBUG PURPOSES ONLY
@app.route('/kill-server')
def kill_server():
    args = request.args.to_dict()
    server = args.get("server")
    heartbeat.brain.set(server, "dead")


if __name__ == '__main__':
    heartbeat_checker_thread = threading.Thread(target=heartbeat.check_health)
    heartbeat_checker_thread.start()
    app.run(host='0.0.0.0', port=80, debug=False)
