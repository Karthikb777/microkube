import time
import redis
import requests
import threading
from flask import Flask, request, jsonify

# ENV VARS
HEALTHY = "healthy"
LOAD_BALANCERS = "load-balancers"
TOTAL_NODES = 'total-nodes'


class HeartBeat:
    def __init__(self):
        self.brain = redis.Redis(host='172.19.0.2', port=6379, db=0, decode_responses=True)

    def check_health(self):
        while True:
            if self.brain.llen(HEALTHY) != 0:
                for server in self.brain.lrange(HEALTHY, start=0, end=-1):
                    url = f'http://{server}/checkheartbeat'
                    try:
                        # if the response time is > 1 second, we consider the server as dead
                        response = requests.get(url, timeout=1, verify=False)
                        if not 200 <= response.status_code < 400:
                            self.brain.lrem(HEALTHY, value=server, count=1)
                            self.brain.set(TOTAL_NODES, int(self.brain.get(TOTAL_NODES)) - 1)

                            load_balancers = self.brain.lrange(LOAD_BALANCERS, start=0, end=-1)
                            for lb in load_balancers:
                                try:
                                    requests.get(f"http://{lb}/removefromqueue", timeout=1)
                                except:
                                    pass
                    except Exception as e:
                        self.brain.lrem(HEALTHY, value=server, count=1)
                        load_balancers = self.brain.lrange(LOAD_BALANCERS, start=0, end=-1)
                        for lb in load_balancers:
                            try:
                                requests.get(f"http://{lb}/removefromqueue", timeout=1)
                            except:
                                pass
            time.sleep(10)  # sleep for 10 seconds


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
    print(args)
    server = args.get("server")
    heartbeat.brain.set(server, "healthy")
    return jsonify(msg="server added")


@app.route('/remove-server')
def remove_server():
    args = request.args.to_dict()
    server = args.get("server")
    heartbeat.brain.delete(server)
    return jsonify(msg="server removed")


# check the other heartbeat server
# if the other server is not well, take over as the primary heartbeat server and
# send a request to auto_scaler to restart that heartbeat server
@app.route('/check-self')
def check_self():
    pass


# THIS IS FOR DEBUG PURPOSES ONLY
@app.route('/kill-server')
def kill_server():
    requests.get(f"as:8000/stop-container")
    return "stopped"


if __name__ == '__main__':
    heartbeat_checker_thread = threading.Thread(target=heartbeat.check_health)
    heartbeat_checker_thread.start()
    app.run(host='0.0.0.0', port=8082, debug=False)
