import socket
import http.server
import socketserver
import threading
import datetime
import json
from time import strftime
from xml.etree.ElementPath import prepare_child
import logging
import sys
import traceback
import argparse
import hashlib

from generator import GenerationCancelled

port = 8080

# a standard python logger
logger = logging.getLogger(__name__)
# basiConfig can only be called once
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')

global_junit_version = 4

class StatusMessage:
    def __init__(self, status: str, message: str | dict = ''):
        self.status = status
        self.message = message
    
    def response(self):
        return json.dumps({
            "type": "status",
            "data": {
                "status": self.status,
                "message": self.message
            }
        }).encode()

class ModelMessage:
    def __init__(self, data):
        self.data = data
    
    def response(self):
        return json.dumps({
            "type": "msg",
            "data": self.data
        }).encode()
    
class NoRefMessage:
    def __init__(self, data):
        self.data = data
    
    def response(self):
        return json.dumps({
            "type": "noreference",
            "data": self.data
        }).encode()

class QueryHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ('/', '/health'):
            self.send_response(200, 'OK')
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            try:
                self.wfile.write(b'OK')
            except BrokenPipeError:
                pass
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        global global_junit_version

        if self.path == '/session':

            try:
                self.request.settimeout(2.0)
                query_text_bytes = self.rfile.read(int(self.headers['Content-Length']))
                query_text = query_text_bytes.decode('utf-8')
                self.request.settimeout(None)

                try:
                    query_session = assign_to_session(query_text, self)
                except Exception as e:
                    logger.error(f'Request may be invalid. Message: {e}. Request:\n{query_text}\n{traceback.format_exc()}')
                    self.end_with_request_error(str(e))
                    return
                
                if query_session:
                    self.send_keep_alive_header()
                    # self.write_single_line(StatusMessage('start').response())
                    query_session.write_start_message()
                    try:
                        query_session.start_query()
                    except GenerationCancelled:
                        logger.info(f'Session {query_session.session_id} cancelled by client')
                    finally:
                        with sessions_lock:
                            sessions.pop(query_session.session_id, None)
                    # self.write_single_line(StatusMessage('finish').response())
                    try:
                        query_session.write_finish_message()
                    except BrokenPipeError:
                        pass
                    # no need to flush because the handle_one_request will do that
                    self.end_session()
                else:
                    raise ValueError("No query session can be constructed or retrieved from request")
            
            except Exception as e:
                logger.error(f'Error handling request. Message: {e}. Request:\n{self.request}\n{traceback.format_exc()}')
                self.end_with_internal_error(str(e))

        elif self.path == '/session/stop':
            try:
                self.request.settimeout(2.0)
                payload_text = self.rfile.read(int(self.headers['Content-Length'])).decode('utf-8')
                self.request.settimeout(None)

                payload = json.loads(payload_text) if payload_text else {}
                session_id = payload.get('session_id')
                if not session_id:
                    self.end_with_request_error('Missing session_id')
                    return

                with sessions_lock:
                    session = sessions.get(session_id)

                if not session:
                    self.send_response(404, 'Session Not Found')
                    self.end_headers()
                    return

                session.request_stop()
                self.send_response(200, 'Stopping')
                self.end_headers()

            except Exception as e:
                logger.error(f"Error handling stop request. Message: {e}. Request:\n{self.request}\n{traceback.format_exc()}")
                self.end_with_internal_error(str(e))

        elif self.path == '/junitVersion':
            try:
                self.request.settimeout(2.0)
                junit_version = int(json.loads(self.rfile.read(int(self.headers['Content-Length'])).decode('utf-8'))['data'])
                self.request.settimeout(None)

                global_junit_version = junit_version
                self.send_response(200, 'Success')
                self.end_headers()
            except Exception as e:
                logger.error(f"Error handling request. Message: {e}. Request:\n{self.request}\n{traceback.format_exc()}")
                self.end_with_internal_error(str(e))

        else:
            self.send_response(404)
            self.end_headers()

    def send_keep_alive_header(self):
        self.send_response(200, 'Success')
        self.send_header('Content-type', 'application/json')   # this doesn't exist on <https://www.iana.org/assignments/media-types/media-types.xhtml#text>
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.end_headers()
    
    def end_with_error(self, code: int, error_msg: str, concrete_msg: str):
        self.send_response(code, error_msg)
        self.end_headers()
        self.end_session()
        # self.wfile.write(StatusMessage('error', concrete_msg).response())

    def end_with_request_error(self, msg: str):
        self.end_with_error(400, 'Bad Request', msg)

    def end_with_internal_error(self, msg: str):
        self.end_with_error(500, 'Internal Server Error', msg)

    def end_session(self):
        self.close_connection = True

    def write_single_line(self, data: bytes):
        self.wfile.write(data + b'\n')
        self.wfile.flush()

class ModelQuerySession:
    '''Session persistent data.'''
    required_fields = ['target_focal_method', 'target_focal_file', 'test_desc', 'project_path', 'focal_file_path']

    def __init__(self, session_id: str, raw_data: dict, handler: QueryHandler):
        self.session_id = session_id
        self.raw_data = raw_data
        self.handler = handler
        self.messages = []
        self.junit_version = global_junit_version
        self._stop_event = threading.Event()

        self.query_data = self.prepare_query_arguments()
        self.session_running = False

    def prepare_query_arguments(self):
        # do with session_meta_data
        return {x: self.raw_data[x] for x in self.required_fields }

    def start_query(self):
        if not self.session_running:
            self.session_running = True
            logger.info(f'Starting query session {self.session_id}')
            try:
                import main

                main.main(**self.query_data, query_session = self)
            finally:
                self.session_running = False

    def request_stop(self):
        self._stop_event.set()

    def should_stop(self) -> bool:
        return self._stop_event.is_set()

    def update_messages(self, messages):
        self.messages = messages
        data_to_send = {
            'session_id': self.session_id,
            'messages': messages
        }
        self.handler.write_single_line(ModelMessage(data_to_send).response())

    def write_start_message(self):
        data = {
            'session_id': self.session_id
        }
        self.handler.write_single_line(StatusMessage('start', data).response())

    def write_noref_message(self):
        data = {
            'session_id': self.session_id,
            'junit_version': self.junit_version
        }
        self.handler.write_single_line(NoRefMessage(data).response())

    def write_finish_message(self):
        data = {
            'session_id': self.session_id
        }
        self.handler.write_single_line(StatusMessage('finish', data).response())

# Not used now, we still send raw time
def get_hash(s: str):
    h = hashlib.sha256(s.encode('utf-8'))
    return h.hexdigest()

sessions: dict[str, ModelQuerySession] = {}
sessions_lock = threading.Lock()

def assign_to_session(query_text: str, query_handler: QueryHandler) -> ModelQuerySession | None:
    # do with sessions
    query_data = json.loads(query_text)
    if query_data['type'] != 'query':
        raise NotImplementedError('None query is not supported yet')
    
    time_str = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')
    new_session = ModelQuerySession(time_str, query_data['data'], query_handler)
    with sessions_lock:
        sessions[new_session.session_id] = new_session
    return new_session
    # TODO sometimes session should be retrived, return None if not found

# def find_open_port():
#     with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
#         s.bind(('', 0))  # Bind to any available port
#         return s.getsockname()[1]  # Return the port number

def start_http_server(port: int):
    logger.info(f'Starting HTTP server on port {port}')

    class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        daemon_threads = True
        allow_reuse_address = True

    httpd = ThreadedTCPServer(("", port), QueryHandler)
    actual_port = httpd.server_address[1]
    logger.info(f'HTTP server is started and listening on {actual_port}')

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info('Shutting down HTTP server')
    finally:
        httpd.server_close()

# class StdioServer:
#     def __init__(self):
#         self.handler = QueryHandler()
#         self.should_run = True

#     def serve_forever(self):
#         while self.should_run:
#             request = sys.stdin.read()
#             if request:
#                 self.handler.handle_one_request()

#     def shutdown(self):
#         self.should_run = False

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Start the model server')
    parser.add_argument('--port', type=int, default=8080, help='Port to start the server on')  # by default listen to a random port
    
    args = parser.parse_args()
    start_http_server(args.port)
