import json
import uuid
from dataclasses import dataclass
from enum import Enum, IntEnum
from threading import Thread, Event

import xmlrpc.client
from xmlrpc.server import SimpleXMLRPCServer

from UnrealBS.Common import Step, Order, Recipe


class WorkerStatus(Enum):
    FREE = 0,
    BUSY = 1

@dataclass
class WorkerData:
    id: str
    port: int
    status: WorkerStatus

class Worker:
    # TODO
    # Add executing order steps and updating server about progres
    # For now skip any output handling
    def __init__(self, server_port):
        self.kill_event = Event()
        self.current_order = None

        self.id = f'worker-{str(uuid.uuid4().hex)[:5]}'
        self.server_port = server_port

        self.rpc_server = SimpleXMLRPCServer(('localhost', 2138))
        self.setup_RPCServer()

    def setup_RPCServer(self):
        self.rpc_server.register_function(self.rpc_recv_order, 'receiveOrder')
        self.rpc_server_thread = Thread(target=self.rpc_server.serve_forever)
        self.rpc_server_thread.daemon = True

    def run(self):
        self.rpc_server_thread.start()

        with xmlrpc.client.ServerProxy(f'http://localhost:{self.server_port}') as proxy:
            proxy.registerWorker(self.id, 2138)

        self.kill_event.wait()

    def rpc_recv_order(self, order_data):
        json_data = json.loads(order_data)
        self.current_order = Order(Recipe(json.loads(json_data['recipe'])), json_data['order'])
        print(f'Worker[{self.id}] got new order {self.current_order.id}')
        with xmlrpc.client.ServerProxy('http://localhost:2137') as proxy:
            proxy.updateWorkerStatus(self.id, WorkerStatus.BUSY.value)
        return True

    def clean_up(self):
        with xmlrpc.client.ServerProxy('http://localhost:2137') as proxy:
            proxy.deregisterWorker(self.id)

    def kill(self):
        self.kill_event.set()
        self.clean_up()