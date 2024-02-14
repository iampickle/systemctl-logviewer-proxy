import subprocess
import json
from fastapi import FastAPI
from pydantic import BaseModel
import socket
import uuid
from multiprocessing import Process
import time

app = FastAPI()

callback_processes = []

class Item(BaseModel):
    websocketurl: str
    port: int

class WebsocketHandler:
    def __init__(self, url, port):
        self.url = url
        self.port = port
        self.sock = None

    def connect_to_websocket(self):
        try:
            print(f'Connecting to {self.url}:{self.port}')
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.url, self.port))
            return True
        except Exception as e:
            print(f"Error connecting to websocket: {e}")
            return False

    def send_message(self, message):
        try:
            print(message)
            self.sock.sendall(message.encode('utf-8'))
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            return False

def get_logs(num):
    command = ["journalctl", "-u", "tbot.service", "--no-pager", "-n", str(num), "-o", "json"]
    return subprocess.check_output(command)

def send_logs(websocket_handler):
    old_log_entry = None
    while True:
        try:
            time.sleep(0.002)
            output = get_logs(1)
            output = output.decode()
            #for log_entry in output:
            log_entry = json.loads(output)
            #print(log_entry)#
            #print(log_entry)
            if old_log_entry == None:
                websocket_handler.send_message(json.dumps(log_entry))
            if old_log_entry != None and old_log_entry['MESSAGE'] != log_entry['MESSAGE']:
                websocket_handler.send_message(json.dumps(log_entry))
            old_log_entry = log_entry
        except Exception as e:
            print(f"Error getting or sending logs: {e}")

@app.post("/addwebsocketcallback/")
async def create_item(item: Item):
    global callback_processes
    ruuid = uuid.uuid4()
    for ruuid in dict(callback_processes):
        ruuid = uuid.uuid4()
        
    try:
        wh = WebsocketHandler(url=item.websocketurl, port=item.port)
        if wh.connect_to_websocket():
            p = Process(target=send_logs, args=(wh,))
            callback_processes.append([str(ruuid), p])
            p.start()
            print(callback_processes)
            return {"code": "Server connection to websocket established", "uuid": ruuid}
        else:
            return {"code": "Could not establish connection to websocket"}
    except Exception as e:
        return {"code": f"Error connecting to websocket: {str(e)}"}

@app.get("/removewebsocketcallback/{uuid}")
async def read_item(uuid: str):
    global callback_processes
    temp_dict = dict(callback_processes)
    if uuid and uuid in temp_dict:
        p = temp_dict[uuid]
        p.terminate()
        callback_processes = [item for item in callback_processes if item[0] != uuid]
        print(callback_processes)
        return 'stopped socket stream'
    else:
        return 'uuid not available'
    
