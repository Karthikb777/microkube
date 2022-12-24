from .state import State

from flask import Flask

class LoadBalancer:
    """
        LoadBalancer class:
            this contains the algorithm to select which server the request has to go to
    """
    def __init__(self, servers: list, state_obj: State):
        self.server_queue = list()
        for server in servers:
            state_obj.server_queue.append(server)
            state_obj.health_table[server] = "healthy"


    """
        selects a server based on the following criteria:
            get the server at the front of the queue
            check if the server is healthy, if yes, redirect the request to the selected server
            else, take the server and put it to the back of the queue, and move 
            on to the next available server in the queue
            
    """
    def select_server(self, state: State):
        while True:
            curr_server = self.server_queue[0]
            if self.check_is_healthy(curr_server):
                return curr_server
            else:
                # TODO: send request to heartbeat server to restart the dying server
                self.server_queue.append(curr_server)
                self.server_queue.pop(0)

    """
        check if the selected server is healthy in the health table 
    """
    def check_is_healthy(self, server_ip):
        curr_server_status = self.health_table.get(server_ip)
        return True if curr_server_status == "healthy" else False

    # FIXME: the below 2 methods should be moved to auto-scaler
    """
        add a new server to the LoadBalancer service, part of auto-scaling functionality
        things to do here:
            add the server to the health table and mark it as "healthy"
            add the server to the end of the server queue
    """
    def add_new_server(self, server_ip):
        self.health_table[server_ip] = "healthy"
        self.server_queue.append(server_ip)

    """
        remove an existing server from the LoadBalancer service, part of auto-scaling functionality
        things to do here:
            remove the server from the server queue
            remove the server entry from the health table
    """
    def remove_existing_server(self, server_ip):
        self.server_queue.remove(server_ip)
        self.health_table.pop(server_ip)


app = Flask(__name__)


@app.route('/')
def hello_world():
    return "hello world"



if __name__ == '__main__':
    app.run()



