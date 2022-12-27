import requests
import redis

from flask import Flask, request, Response, jsonify

# ENV VARS
HEARTBEAT_SERVER_DNS = ""
NODES = "nodes"
HEALTHY = "healthy"


class LoadBalancer:
    """
        LoadBalancer class:
            this contains the algorithm to select which server the request has to go to
    """

    def __init__(self):
        self.brain = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        self.server_queue = list()
        list_of_servers = self.brain.lrange(HEALTHY, start=0, end=-1)
        print(list_of_servers)
        for server in list_of_servers:
            self.server_queue.append(server)

    """
        selects a server based on the following criteria:
            get the server at the front of the queue
            check if the server is healthy, if yes, redirect the request to the selected server
            else, take the server and put it to the back of the queue, and move 
            on to the next available server in the queue   
    """

    def select_server(self):
        while True:
            curr_server = self.server_queue[0]
            self.server_queue.append(curr_server)
            self.server_queue.pop(0)
            if self.check_is_healthy(curr_server):
                return curr_server

    # check if the selected server is healthy in the health table
    def check_is_healthy(self, server_ip):
        if self.brain.get(server_ip) == "healthy":
            return True
        else:
            return False

    # add a new server to the LoadBalancer service, part of auto-scaling functionality
    def add_new_server(self, server_ip):
        self.server_queue.append(server_ip)
        print(self.server_queue)

    # remove an existing server from the LoadBalancer service, part of auto-scaling functionality
    def remove_existing_server(self, server_ip):
        self.server_queue.remove(server_ip)
        print(self.server_queue)


app = Flask(__name__)
load_balancer = LoadBalancer()


@app.route('/')
def hello_world():
    return "hello world"


@app.route('/addtoqueue')
def add_to_queue():
    args = request.args.to_dict()
    server = args.get("server")
    load_balancer.add_new_server(server)
    return "added"


@app.route('/removefromqueue')
def remove_from_queue():
    args = request.args.to_dict()
    server = args.get("server")
    load_balancer.remove_existing_server(server)
    return "removed"


@app.route('/checkheartbeat')
def check_heart_beat():
    return jsonify(msg="healthy")


@app.route('/<path:path>', methods=['GET', 'POST', 'DELETE'])
def reverse_proxy(path):
    redirect_server = load_balancer.select_server()
    print("current queue: ", redirect_server)
    print("current queue: ", load_balancer.server_queue)
    if request.method == "GET":
        response = requests.get(f"http://{redirect_server}/{path}")

        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in response.raw.headers.items() if
                   name.lower() not in excluded_headers]

        return Response(response.content, response.status_code, headers)

    elif request.method == "POST":
        response = requests.post(f"http://{redirect_server}/{path}", json=request.get_json())

        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in response.raw.headers.items() if
                   name.lower() not in excluded_headers]

        return Response(response.content, response.status_code, headers)

    elif request.method == "DELETE":
        response = requests.delete(f"http://{redirect_server}/{path}")
        return Response(response.content, response.status_code, response.headers)


if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=8081)
