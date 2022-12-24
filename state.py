"""
    contains the state of the whole system
    consists of:
    - health table
    - server queue
"""


class State:
    def __init__(self):
        self.health_table = dict()
        self.server_queue = list()
