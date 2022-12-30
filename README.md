
# MicroKube

A simple container orchestration service, made with Python.

## Architecture
The following parts are present in the cluster:
- LoadBalancer: A simple Load balancer service with Round Robin load balancing, written in Flask.
- HeartBeat: A service which checks the servers periodically if they are up or down. 
- AutoScaler: A service which automatically scales up or down the number of servers based on the condition of the cluster.
- Brain: An in-memory Redis data store which holds the state data for the entire cluster.
- Server: Runs our app.

[![Architecture.png](https://i.postimg.cc/G2hvNvWq/Architecture.png)](https://postimg.cc/4KqKHHN9)

## Requirements
- [Docker](https://www.docker.com/)
- [Python](https://www.python.org/)
- [Docker SDK for Python](https://docker-py.readthedocs.io/en/stable/)
- [Redis-py](https://redis-py.readthedocs.io/en/stable/)

## How to Run
- Install all the required dependencies.
- Build the images for the different components (LoadBalancer, HeartBeat, AutoScaler, Brain, Server)
- Update the config.json with the names of the images that were built.
- Make changes to the values in config.json, if required.
- Run Core.py.
- To bring the cluster up: `python Core.py -c path/to/config.json -u true`
- To bring the cluster down: `python Core.py -c path/to/config.json -d true`
