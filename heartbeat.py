import time
import subprocess

class HeartBeat:
    def __init__(self):
        pass
    #     while True:
    # #         get all the servers and check for heartbeat for every one of them
    # #         if any one of the server is found unhealthy, resurrect the server
    #         pass

    def check_health(self, server_ip):
        response = subprocess.run(f"ping -n 1 {server_ip}")
        if response.returncode == 1:
            return True
        else:
            return False

    """
        stops and restarts an unhealthy server
    """
    def resurrect(self):
        pass



if __name__ == '__main__':
    hb = HeartBeat()
    hb.check_health('192.168.3.5')



