from flask import Flask, request, Response
import subprocess
import time
import threading
import logging
import os
from datetime import datetime

try:
    os.remove('logs/supervisor.log')
except OSError:
    pass

logging.basicConfig(filename='logs/supervisor.log', level=logging.DEBUG)


#logging.info("Starting main.py")
#Popen('/usr/bin/python3 /home/ubuntu/That-Discord-Bot/main.py',shell=True)
#logging.info("Started main.py")


def Tunnel_Thread():
    logging.info("Starting Tunnel")
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    logging.info("date and time =", dt_string)
    logging.info(subprocess.run(['lt --port 5000 --subdomain inefowaiefwojane --host https://loca.lt'],shell=True))

def Pull_Thread():
    logging.info("Performing Pull")
    with open('gitUrl') as f:
        URL = f.read().strip()
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    logging.info("date and time =", dt_string)
    logging.debug(subprocess.run(['cd /home/ubuntu/Music-Bot/'],shell=True))
    logging.debug(subprocess.run(['git pull ' + URL + ' main'],shell=True))
    time.sleep(3)
    logging.debug(subprocess.run(['sudo systemctl restart musicbot'],shell=True))
    logging.info("Finished Pull")

app = Flask(__name__)

@app.route('/', methods=['POST'])
def respond():
    #print(request.json)
    logging.info("Starting Pull Thread")
    y = threading.Thread(target=Pull_Thread)
    y.start()
    logging.info("Responding to Websocket")
    return Response(status=200)

if __name__ == "__main__":
    logging.info('Starting Tunnel Thread')
    x = threading.Thread(target=Tunnel_Thread)
    x.start()
    app.run()