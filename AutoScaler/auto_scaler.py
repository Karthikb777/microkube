import threading
import time
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

# IMAGES
BRAIN_IMAGE = "karthikb777/brain:1.0"
NODE_IMAGE = "karthikb777/testserver:1.0"
LOAD_BALANCER_IMAGE = "karthikb777/loadbalancer:1.1"
HEART_BEAT_SERVER_IMAGE = "karthikb777/heartbeat:1.1"
AUTO_SCALER_IMAGE = "karthikb777/autoscaler:1.1"

# PORTS TO OPEN
BRAIN_PORT = 6379
LOAD_BALANCER_PORT = 80
HEART_BEAT_SERVER_PORT = 80

# NAMES FOR THE CONTAINERS
BRAIN_NAME = "brain"
LOAD_BALANCER_NAME = "lb"
AUTO_SCALER_NAME = "as"
HEART_BEAT_SERVER_NAME = "hb"

# BRAIN KEYS
HEALTHY = "healthy"
NODES = "nodes"
LOAD_BALANCERS = "load-balancers"
TOTAL_NODES = 'total-nodes'


class AutoScaler:
    def __init__(self, desired):
        # steps
        #   bring up brain
        #   bring up heartbeat server
        #   bring up load balancer
        self.brain = redis.Redis(host='172.19.0.2', port=6379, db=0, decode_responses=True)
        self.docker_client = docker.DockerClient()
        self.network = self.docker_client.networks.get(network_id="22de9f28bf1b")
        self.currdata = ""
        self.desired = desired
        self.start_load_balancers()

    # this method will run in a separate thread
    def do_scaling(self):
        desired = self.desired
        container_type = NODES
        if container_type == NODES:
            # get the total no. of nodes and the current node count
            desired_node_count = desired.total
            desired_node_max_count = desired.max
            current_node_count = self.brain.llen(HEALTHY)

            if current_node_count < desired_node_count:
                while current_node_count < desired_node_max_count:
                    self.start_node()
                    current_node_count += 1

            elif current_node_count > 2 * desired_node_count:
                self.stop_node()

            self.currdata = f"AUTOSCALER: current: {self.brain.llen(HEALTHY)} desired: {desired_node_max_count}"

        elif container_type == LOAD_BALANCERS:
            pass  # scale load balancers here
        time.sleep(15)

    """
        start a docker container
        add that container's IP address to the brain
        inform the load-balancer about the newly added container 
    """

    def start_node(self):
        # start a container
        container = self.docker_client.containers.run(image=NODE_IMAGE, detach=True, network=NETWORK_NAME)
        container.reload()
        ip = container.attrs['NetworkSettings']['Networks'][NETWORK_NAME]['IPAddress']
        # add the container IP to the brain
        self.brain.rpush(NODES, ip)
        self.brain.rpush(HEALTHY, ip)
        # self.brain.set(TOTAL_NODES, int(self.brain.get(TOTAL_NODES)) + 1)
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
        # remove the container IP from the brain, also decrement the number of available nodes
        self.brain.lrem(NODES, value=ip, count=1)
        self.brain.lrem(HEALTHY, value=ip, count=1)
        # self.brain.set(TOTAL_NODES, int(self.brain.get(TOTAL_NODES)) - 1)
        # inform the load balancers about the removal of the node
        load_balancers = self.brain.lrange(LOAD_BALANCERS, start=0, end=-1)
        for lb in load_balancers:
            try:
                requests.get(f"http://{lb}/removefromqueue", timeout=1)
            except:
                pass

    # TODO: move the init part of the cluster to Core.py file
    def start_brain(self):
        brain_container = self.docker_client.containers.run(
            image=BRAIN_IMAGE,
            detach=True,
            network=NETWORK_NAME,
            ports={
                '6379/tcp': 6379
            },
            name=""
        )

    def start_load_balancers(self):
        pass

    def start_heartbeat_servers(self):
        pass


class Desired_state:
    def __init__(self):
        self.total = 3
        self.max = 10


app = Flask(__name__)
desired = Desired_state()
auto_scaler = AutoScaler(desired)


@app.route('/')
def root_path():
    return auto_scaler.currdata


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
    auto_scaler_thread = threading.Thread(target=auto_scaler.do_scaling)
    auto_scaler_thread.start()
    app.run(host="0.0.0.0", port=8000, debug=True)
