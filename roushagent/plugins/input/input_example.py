#!/usr/bin/env python

import BaseHTTPServer
import threading
import json
import urllib

producer_lock = threading.Lock()
producer_queue = []
server_quit = False
server_thread = None
name = "example"

class RestishHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    # these will be
    def do_POST(self):
        action = self.path.split("/")[1]
        retval = {'action': action}

        if self.headers.getheader('content-type') == 'application/json':
            payload_len = self.headers.getheader('content-length')

            # FIXME: Danger, timeout vs. memory.
            try:
                if payload_len:
                    retval['payload'] = json.loads(self.rfile.read(
                        int(payload_len)))
                else:
                    retval['payload'] = json.load(self.rfile)
            except ValueError:
                self.send_response(500)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                return

        producer_lock.acquire()
        producer_queue.append(retval)

        # should use a pthread_cond here
        producer_lock.release()

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def do_GET(self):
        # Maybe this is status?
        pass


class ServerThread(threading.Thread):
    def stop(self):
        LOG.debug("closing underlying server socket")
        # make a best-effort attempt to kill the underlying server
        try:
            LOG.debug(urllib.urlopen('http://%s:%s' % self.httpd.server_address))
            self.httpd.shutdown()
            self.httpd.socket.close()
        except Exception as e:
            pass

    def run(self):
        global server_quit

        server_class = BaseHTTPServer.HTTPServer
        self.httpd = server_class(('0.0.0.0', 8000), RestishHandler)
        while not server_quit:
            try:
                self.httpd.handle_request()
            except Exception as e:
                LOG.error("Got an exception: %s.  Aborting." % type(e))
                if server_quit:
                    return

        LOG.error("Exiting run thread")

# Amazing stupid handler.  Throw off a thread
# and start waiting for stuff...
def setup(config={}):
    global server_thread
    LOG.debug('Starting rest-ish server')
    server_thread = ServerThread()
    server_thread.start()


def teardown():
    global server_thread
    global server_quit

    LOG.debug('Shutting down rest-ish server')
    server_quit = True
    server_thread.stop()
    server_thread.join()


def fetch():
    result = {}

    producer_lock.acquire()
    if len(producer_queue) > 0:
        result = producer_queue.pop()
        LOG.debug('Got input from rest-ish server')
    producer_lock.release()

    return result
