import docker
import redis
import json
import argparse


# FIXME: when creating multiple load balancers / heartbeat servers, change the naming scheme of the containers
def create(filename):
    with open(filename, 'r') as f:
        cluster_config = json.load(f)

    docker_client = docker.DockerClient()

    # get the config
    print("parsing config file...")
    network_config = cluster_config['network']
    container_names = cluster_config['container_names']
    images = cluster_config['images']
    open_ports = cluster_config['open_ports']
    desired_state = cluster_config['desired_state']
    redis_keys = cluster_config['redis_keys']

    print("config file parsed.")


    # create the network
    print("creating the network...")
    network = docker_client.networks.create(
        name=network_config['name'],
        driver=network_config['driver']
    )
    print("network created.")

    # start the brain
    print("starting the brain...")
    brain = docker_client.containers.run(
        image=images['brain_image'],
        detach=True,
        network=network_config['name'],
        ports={
            f'{open_ports["brain_port"]}/tcp': int(open_ports['brain_port']),
        }
    )
    brain.reload()
    brainIP = brain.attrs['NetworkSettings']['Networks'][network_config['name']]['IPAddress']

    brain_client = redis.Redis(host='localhost', port=open_ports['brain_port'], db=0, decode_responses=True)
    brain_client.set("init", "true")
    print(brain_client.get("init"))
    print("brain started.")

    # start the heartbeat server
    print("starting heartbeat server...")
    heart_beat = docker_client.containers.run(
        image=images['heart_beat_server_image'],
        detach=True,
        network=network_config['name'],
        # ports={
        #     f'{open_ports["heart_beat_server_port"]}/tcp': int(open_ports['heart_beat_server_port']),
        # },
        environment={
            'BRAIN_IP': brainIP,
            'BRAIN_PORT': open_ports['brain_port'],
            'BRAIN_KEY_HEALTHY': redis_keys['healthy_nodes'],
            'BRAIN_KEY_LOAD_BALANCER': redis_keys['load_balancers']
        }
    )
    heart_beat.reload()
    heart_beat_ip = heart_beat.attrs['NetworkSettings']['Networks'][network_config['name']]['IPAddress']
    # add the heartbeat server IP to redis
    brain_client.rpush(redis_keys['heart_beat_servers'], heart_beat_ip)
    brain_client.set(redis_keys['primary_heart_beat_server'], heart_beat_ip)

    print("heartbeat server started.")

    # start the load balancer
    print("starting loadbalancer...")
    load_balancer = docker_client.containers.run(
        image=images['load_balancer_image'],
        detach=True,
        network=network_config['name'],
        ports={
            f'{open_ports["load_balancer_port"]}/tcp': int(open_ports['load_balancer_port']),
        },
        environment={
            'BRAIN_IP': brainIP,
            'BRAIN_PORT': open_ports['brain_port'],
            'BRAIN_KEY_HEALTHY': redis_keys['healthy_nodes'],
        }
    )
    load_balancer.reload()
    load_balancer_ip = load_balancer.attrs['NetworkSettings']['Networks'][network_config['name']]['IPAddress']
    print(load_balancer.attrs)
    # add the load balancer IP to redis
    brain_client.rpush(redis_keys['load_balancers'], load_balancer_ip)
    brain_client.set(redis_keys['primary_load_balancer'], load_balancer_ip)
    print(brain_client.lrange(redis_keys['load_balancers'], 0, -1))
    print("loadbalancer started.")

    # start the autoscaler
    print("starting the autoscaler...")
    auto_scaler = docker_client.containers.run(
        image=images['auto_scaler_image'],
        detach=True,
        network=network_config['name'],
        # ports={
        #     f'{open_ports["auto_scaler_port"]}/tcp': int(open_ports['auto_scaler_port']),
        # },
        volumes=['/var/run/docker.sock:/var/run/docker.sock'],
        environment={
            'IDEAL_NODES': desired_state['ideal_nodes'],
            'MAX_NODES': desired_state['max_nodes'],
            'NETWORK': network_config['name'],
            'NODE_IMAGE': images['node_image'],
            'BRAIN_IP': brainIP,
            'BRAIN_PORT': open_ports['brain_port'],
            'BRAIN_KEY_HEALTHY': redis_keys['healthy_nodes'],
            'BRAIN_KEY_LOAD_BALANCER': redis_keys['load_balancers']
        }
    )
    print("autoscaler started.")

    print("cluster up.")


# bring the whole cluster down
def nuke(filename):
    with open(filename, 'r') as f:
        cluster_config = json.load(f)

    docker_client = docker.DockerClient()

    network_name = cluster_config['network']['name']

#     get all the containers in the network and stop all of them
    all_containers = docker_client.containers.list(filters={
        "network": network_name
    })

    for container in all_containers:
        container.stop()

    networks = docker_client.networks.list()
    for network in networks:
        if network.attrs['Name'] == network_name:
            network.remove()
            break

    print("cluster nuked")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('-c', '--config', help='path to config file for the cluster')
    parser.add_argument('-u', '--up', help='bring the cluster up')
    parser.add_argument('-d', '--down', help='bring the cluster down')

    args = parser.parse_args()

    if args.config:
        pass
    else:
        print("no config file specified. aborting...")
        exit(1)

    if args.up:
        create(args.config)
    elif args.down:
        nuke(args.config)
