from flask import Flask, request, jsonify
import docker
import redis
import requests

"""
AutoScaler basic functionality: 
start_node: brings a node up. informs the load balancer and the heartbeat server 
to add the nodes to their respective tables. 
stop_node: takes a node down. informs the load balancer and the heartbeat server to remove the nodes from 
their respective tables. 
check_scaling: periodically check the health table in the brain
if all the nodes are healthy. always try to keep the cluster at the desired state. if all nodes are 
healthy, kill one node. if one node is dying, add 2 more nodes. 
"""

# ENV VARS
NETWORK_NAME = 'HAN'
CONTAINER_IMAGE = "karthikb777/testserver:1.0"
HEALTHY = "healthy"
NODES = "nodes"
LOAD_BALANCERS = "load-balancers"


class AutoScaler:
    def __init__(self):
        self.brain = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        self.docker_client = docker.from_env()
        self.network = self.docker_client.networks.get(network_id="22de9f28bf1b")

    # this method will run in a separate thread
    def check_scaling(self, desired):
        pass

    """
        start a docker container
        add that container's IP address to the brain
        inform the load-balancer about the newly added container 
    """
    def start_node(self):
        # start a container
        container = self.docker_client.containers.run(image=CONTAINER_IMAGE, detach=True, network=NETWORK_NAME)
        container.reload()
        ip = container.attrs['NetworkSettings']['Networks'][NETWORK_NAME]['IPAddress']
        # add the container IP to the brain
        self.brain.rpush(NODES, ip)
        self.brain.rpush(HEALTHY, ip)
        # inform the load balancers about the newly created container
        load_balancers = self.brain.lrange(LOAD_BALANCERS, start=0, end=-1)
        for lb in load_balancers:
            try:
                requests.get(f"http://{lb}/addtoqueue", timeout=1)
            except:
                pass

    """
        stop a docker container
        remove that container's IP address from the brain
        inform the load-balancer about the removed container
    """
    def stop_node(self):
        # stop the container
        container = self.docker_client.containers.list()[0]
        ip = container.attrs['NetworkSettings']['Networks'][NETWORK_NAME]['IPAddress']
        container.stop()
        # remove the container IP from the brain
        self.brain.lrem(NODES, value=ip, count=1)
        self.brain.lrem(HEALTHY, value=ip, count=1)
        # inform the load balancers about the removal of the node
        load_balancers = self.brain.lrange(LOAD_BALANCERS, start=0, end=-1)
        for lb in load_balancers:
            try:
                requests.get(f"http://{lb}/removefromqueue", timeout=1)
            except:
                pass


app = Flask(__name__)
auto_scaler = AutoScaler()


@app.route('/')
def root_path():
    return "root path"


# DEBUG
@app.route('/start-container')
def start_container():
    auto_scaler.start_node()
    return jsonify(msg="node up")


@app.route('/stop-container')
def stop_container():
    auto_scaler.stop_node()
    return jsonify(msg="node down")


# nuke all containers at once
# DO NOT USE THIS, REALLY!
@app.route('/nuke')
def nuke():
    for node in auto_scaler.docker_client.containers.list():
        node.stop()
    return "nuked"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)
