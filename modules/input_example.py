#!/usr/bin/env python

import BaseHTTPServer
import threading

producer_lock = threading.Lock()
producer_queue = []
server_quit = False
server_thread = None

class RestishHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_POST(self):
        # Maybe this is send request

        producer_lock.acquire()
        producer_queue.append('{ "action": "testing", "payload": {} ')

        # should use a pthread_cond here
        producer_lock.release()

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
        while not server_quit:
            httpd.handle_request()

# Amazing stupid handler.  Throw off a thread
# and start waiting for stuff...
def setup():
    LOG.debug('Starting rest-ish server')
    server_thread = ServerThread()
    print "server_thread in setup" + str(dir(server_thread))
    server_thread.start()

def teardown():
    LOG.debug('Shutting down rest-ish server')
    server_quit = True
    print "server thread in teardown: " + str(dir(server_thread))
    server_thread.join()

def fetch():
    result = {}

    producer_lock.acquire()
    if len(producer_queue) > 0:
        result = producer_queue.pop()
        LOG.debug('Got input from rest-ish server')
    producer_lock.release()

    return result
