import os
import time
import redis
import requests
import logging

# ENV VARS
BRAIN_IP = os.environ.get('BRAIN_IP')
BRAIN_PORT = os.environ.get('BRAIN_PORT')
HEALTHY = os.environ.get('BRAIN_KEY_HEALTHY')
LOAD_BALANCERS = os.environ.get('BRAIN_KEY_LOAD_BALANCER')


class HeartBeat:
    def __init__(self):
        logging.info(msg="initializing heartbeat server...")
        self.brain = redis.Redis(host=BRAIN_IP, port=int(BRAIN_PORT), db=0, decode_responses=True)

    def check_health(self):
        while True:
            if self.brain.llen(HEALTHY) != 0:
                for server in self.brain.lrange(HEALTHY, start=0, end=-1):
                    logging.info(msg=f"checking {server}...")
                    url = f'http://{server}/checkheartbeat'
                    try:
                        # if the response time is > 1 second, we consider the server as dead
                        response = requests.get(url, timeout=1, verify=False)
                        if not 200 <= response.status_code < 400:
                            self.brain.lrem(HEALTHY, value=server, count=1)
                            logging.warning(msg=f"{server} dead")
                            load_balancers = self.brain.lrange(LOAD_BALANCERS, start=0, end=-1)
                            for lb in load_balancers:
                                try:
                                    requests.get(f"http://{lb}/removefromqueue?server={server}", timeout=1)
                                except:
                                    pass
                    except Exception as e:
                        logging.warning(msg=f"{server} dead")
                        self.brain.lrem(HEALTHY, value=server, count=1)
                        load_balancers = self.brain.lrange(LOAD_BALANCERS, start=0, end=-1)
                        for lb in load_balancers:
                            try:
                                requests.get(f"http://{lb}/removefromqueue?server={server}", timeout=1)
                            except:
                                pass
            time.sleep(10)  # sleep for 10 seconds


if __name__ == '__main__':
    heartbeat = HeartBeat()
    heartbeat.check_health()
