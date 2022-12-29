import os
import time
import docker
import redis
import requests
import logging

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
IDEAL_NODES = os.environ.get("IDEAL_NODES")
MAX_NODES = os.environ.get("MAX_NODES")
NETWORK_NAME = os.environ.get("NETWORK")
NODE_IMAGE = os.environ.get("NODE_IMAGE")
BRAIN_IP = os.environ.get("BRAIN_IP")
BRAIN_PORT = os.environ.get("BRAIN_PORT")
BRAIN_KEY_HEALTHY = os.environ.get("BRAIN_KEY_HEALTHY")
BRAIN_KEY_LOAD_BALANCER = os.environ.get("BRAIN_KEY_LOAD_BALANCER")


class AutoScaler:
    def __init__(self):
        logging.info(msg="initializing auto-scaler...")
        self.brain = redis.Redis(host=BRAIN_IP, port=int(BRAIN_PORT), db=0, decode_responses=True)
        self.docker_client = docker.DockerClient()
        # self.network = self.docker_client.networks.get(network_id="22de9f28bf1b")
        self.ideal_nodes = int(IDEAL_NODES)
        self.max_nodes = int(MAX_NODES)

    # this method will run in a separate thread
    def do_scaling(self):
        while True:
            # get the total no. of nodes and the current node count
            desired_node_count = self.ideal_nodes
            desired_node_max_count = self.max_nodes
            current_node_count = self.brain.llen(BRAIN_KEY_HEALTHY)

            # if the difference between current node count and desired node count is 2 or more,
            # then scale all the way up to the max no. of nodes
            if desired_node_count - current_node_count >= 2:
                logging.warning(msg="number of nodes are less than desired. scaling up...")
                curr_nodes = current_node_count
                while curr_nodes <= desired_node_max_count:
                    self.start_node()
                    curr_nodes += 1

            # if current node count is more than desired node count, remove one node
            elif current_node_count > desired_node_count:
                logging.info(msg="number of nodes are more than desired. scaling down...")
                self.stop_node()

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
        self.brain.rpush(BRAIN_KEY_HEALTHY, ip)
        # self.brain.set(TOTAL_NODES, int(self.brain.get(TOTAL_NODES)) + 1)
        # inform the load balancers about the newly created container
        load_balancers = self.brain.lrange(BRAIN_KEY_LOAD_BALANCER, start=0, end=-1)
        for lb in load_balancers:
            try:
                requests.get(f"http://{lb}/addtoqueue?server={ip}", timeout=1)
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
        self.brain.lrem(BRAIN_KEY_HEALTHY, value=ip, count=1)
        # self.brain.set(TOTAL_NODES, int(self.brain.get(TOTAL_NODES)) - 1)
        # inform the load balancers about the removal of the node
        load_balancers = self.brain.lrange(BRAIN_KEY_LOAD_BALANCER, start=0, end=-1)
        for lb in load_balancers:
            try:
                requests.get(f"http://{lb}/removefromqueue?server={ip}", timeout=1)
            except:
                pass


if __name__ == "__main__":
    auto_scaler = AutoScaler()
    auto_scaler.do_scaling()
