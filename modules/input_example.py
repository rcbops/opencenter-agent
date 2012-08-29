#!/usr/bin/env python

import BaseHTTPServer
import threading

producer_thread = threading.Lock()
producer_queue = []


class RestishHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_POST(self):
        # Maybe this is send request

        producer_thread.acquire()
        producer_queue.append('{ "action": "testing", "payload": {} ')

        # should use a pthread_cond here
        producer_thread.release()

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def do_GET(self):
        # Maybe this is status?
        pass

class ServerThread(threading.Thread):
    def run(self):
        server_class = BaseHTTPServer.HTTPServer
        httpd = server_class(('0.0.0.0', 8080), RestishHandler)
        httpd.serve_forever()

# Amazing stupid handler.  Throw off a thread
# and start waiting for stuff...
def setup():
    server_thread = ServerThread()
    server_thread.start()

def fetch():
    result = {}

    producer_thread.acquire()
    if len(producer_queue) > 0:
        result = producer_queue.pop()
    producer_thread.release()

    return result
