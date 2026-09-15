"""
Run the server:
    python server.py                  <- persistent mode (default)
    python server.py non-persistent   <- non-persistent mode
    python server.py single-threaded  <- single-threaded mode (Part C)

Then open a browser (or use curl) and navigate to:
    http://127.0.0.1:8080/index.html
    http://127.0.0.1:8080/about.html
    http://127.0.0.1:8080/missing.html   <-- should return 404

Or use the provided client.py to run the Part C concurrency experiment.
"""

import socket
import threading
import os
import time


def _ts():
    """Wall-clock timestamp for log lines, e.g. '22:41:07.183'. Lets you
    line up this server's log against client terminals that print the
    same format."""
    return time.strftime('%H:%M:%S', time.localtime()) + f'.{int((time.time() % 1) * 1000):03d}'

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
HOST    = '127.0.0.1'
PORT    = 8080
WEBROOT = './www'        # Folder where the server looks for files to serve
TIMEOUT = 10           	 # Seconds of inactivity before a persistent connection closes

# ---------------------------------------------------------------------------
# MIME type map — maps file extensions to Content-Type values
# ---------------------------------------------------------------------------
MIME_TYPES = {
    '.html': 'text/html',
    '.htm':  'text/html',
    '.txt':  'text/plain',
    '.css':  'text/css',
    '.js':   'application/javascript',
    '.jpg':  'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png':  'image/png',
    '.ico':  'image/x-icon',
}


def get_status_line(code):
    """
    Required codes to handle: 200, 400, 404, 405, 500

    Parameters:
        code (int): HTTP status code

    Returns:
        str: Full status line including HTTP version, code, and reason phrase
    """
    # TODO: implement this function
    status_lines = {
        200: 'HTTP/1.1 200 OK',
        400: 'HTTP/1.1 400 Bad Request',
        404: 'HTTP/1.1 404 Not Found',
        405: 'HTTP/1.1 405 Method Not Allowed',
        500: 'HTTP/1.1 500 Internal Server Error'
    }
    return status_lines.get(code)
    


def parse_http_request(raw_data):
    """

    Parameters:
        raw_data (bytes): The raw bytes received from the socket

    Returns:
        dict with keys 'method', 'path', 'version', 'headers'
        Return None if the data cannot be parsed.
    """
    # TODO: implement this function

    try:
        raw = raw_data.decode('utf-8', errors='replace')
        raw_lines = raw.split('\r\n')

        request_line_info = raw_lines[0].split()
        if len(request_line_info) != 3:
            return None

        headers = {}
        for line in raw_lines[1:]:
            if not line:
                break
            if (":") not in line:
                return None
            key,value = line.split(":", 1)
            headers[key] = value

        return {
            "method":   request_line_info[0],
            "path":     request_line_info[1],
            "version":  request_line_info[2],
            "headers":  headers,
        }
    except(AttributeError, UnicodeError):
        None
        

def serve_file(path):
    """
    Attempt to read and return a file from the web root directory.

    Parameters:
        path (str): The URL path from the HTTP request (e.g. "/index.html")

    Returns:
        tuple: (status_code, content_bytes, mime_type)
               status_code   - int, 200 or 404
               content_bytes - bytes or None
               mime_type     - str or None
    """

    path = path.lstrip('/\\')
    full_path = os.path.join(WEBROOT, path)

    if os.path.exists(full_path) and os.path.isfile(full_path):
        with open(full_path, 'rb') as f:
            content = f.read()
        ext = os.path.splitext(full_path)[1]
        mime_type = MIME_TYPES.get(ext, 'application/octet-stream')
        return (200, content, mime_type)
    else:
        return (404, None, None)


def build_http_response(status_code, body_bytes, extra_headers=None):
    """
    Construct a complete HTTP response as a byte string ready to send.

    Parameters:
        status_code   (int)  : e.g. 200 or 404
        body_bytes    (bytes): response body, or b'' for empty responses
        extra_headers (dict) : optional additional header name -> value pairs

    Returns:
        bytes: the complete HTTP response
    """
    status_line = get_status_line(status_code)

    headers = {
        'Content-Length': str(len(body_bytes)),
        'Date': time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime()),
        'Server': 'PA1Server/1.0',
    }
    if extra_headers:
        headers.update(extra_headers)

    header_lines = f"{status_line}\r\n"
    for name, value in headers.items():
        header_lines += f"{name}: {value}\r\n"
    header_lines += "\r\n"

    return header_lines.encode('utf-8') + body_bytes


def handle_connection_non_persistent(conn):
    """
    Handle exactly ONE HTTP request on the given connection, then close it.

    Parameters:
        conn (socket.socket): An already-connected client socket
    """
    # TODO: implement this function
    conn.settimeout(TIMEOUT)
    try:
        raw_data = conn.recv(4096)
        if not raw_data:
            return

        request = parse_http_request(raw_data)
        if request is None:
            response = build_http_response(400, b'Bad Request')
            conn.sendall(response)
            return

        if request['method'] != 'GET':
            response = build_http_response(405, b'Method Not Allowed')
            conn.sendall(response)
            return

        status_code, content, mime_type = serve_file(request['path'])
        if status_code == 200:
            extra_headers = {'Content-Type': mime_type}
            response = build_http_response(200, content, extra_headers)
        else:
            response = build_http_response(404, b'Not Found')

        conn.sendall(response)
    except socket.timeout:
        print(f"[{_ts()}] [Server] Connection timed out.")
    except Exception as e:
        print(f"[{_ts()}] [Server] Error handling connection: {e}")
        response = build_http_response(500, b'Internal Server Error')
        conn.sendall(response)
    finally:
        conn.close()


def handle_connection_persistent(conn):
    """
    Handle MULTIPLE HTTP requests on the same connection (HTTP/1.1 keep-alive).

    The connection stays open until one of these happens:
        - The client sends a "Connection: close" header
        - The client closes the connection (recv returns b'')
        - No data arrives within TIMEOUT seconds


    Parameters:
        conn (socket.socket): An already-connected client socket
    """
    # TODO: implement this function
    conn.settimeout(TIMEOUT)
    while True:
        try:
            raw_data = conn.recv(4096)
            if not raw_data:
                break

            request = parse_http_request(raw_data)
            if request is None:
                response = build_http_response(400, b'Bad Request')
                conn.sendall(response)
                break

            if request['method'] != 'GET':
                response = build_http_response(405, b'Method Not Allowed')
                conn.sendall(response)
                break

            status_code, content, mime_type = serve_file(request['path'])
            if status_code == 200:
                extra_headers = {'Content-Type': mime_type}
                response = build_http_response(200, content, extra_headers)
            else:
                response = build_http_response(404, b'Not Found')

            conn.sendall(response)

            # Check for "Connection: close" header
            if 'Connection' in request['headers'] and request['headers']['Connection'].lower() == 'close':
                break

        except socket.timeout:
            print("[Server] Connection timed out.")
            break
        except Exception as e:
            print("[Server] Error handling connection: {e}")
            response = build_http_response(500, b'Internal Server Error')
            conn.sendall(response)
            break   
        finally:
            conn.close()


# ===========================================================================
# ── BOILERPLATE — do not modify below this line ─────────────────────────────
# ===========================================================================

def _run_handler_with_logging(handler, conn, addr):
    """
    Wraps a connection handler so we can print when it actually finishes,
    and so one connection's exception can't crash the whole server. This
    matters most in single-threaded mode: in threaded mode an unhandled
    exception only kills that one thread silently, but with no thread to
    contain it, an unhandled exception here would take down the entire
    server -- including every other client waiting to be accepted.
    """
    try:
        handler(conn)
    except Exception as e:
        print(f"[{_ts()}] [Server] Handler error for {addr}: {e!r}")
    finally:
        print(f"[{_ts()}] [Server] Finished handling {addr}")


def start_server(mode='persistent'):
    """
    Start the HTTP server and dispatch connections to the correct handler.

    Parameters:
        mode (str): 'persistent', 'non-persistent', or 'single-threaded'

    Mode behavior:
        'persistent' / 'non-persistent':
            Each accepted connection is handed to its own thread
            immediately, so the accept loop is free to accept the next
            connection right away, even while earlier connections are
            still being served.

        'single-threaded':
            Each accepted connection is handled directly in the main
            thread, with NO threading.Thread involved at all. The accept
            loop cannot call accept() again until the current connection's
            handler function fully returns. If that handler is in the
            middle of sending a large, slowly-consumed response, every
            other client is stuck waiting in the OS's connection backlog
            with no way to even start being served. This is the
            head-of-line blocking effect Part C asks you to measure.

            single-threaded mode always uses the persistent connection
            handler (handle_connection_persistent), since the blocking
            effect is about the accept loop itself, not about which
            handler is running.
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(10)

    mode_labels = {
        'persistent': 'persistent (HTTP/1.1 keep-alive, multi-threaded)',
        'non-persistent': 'non-persistent (HTTP/1.0 style, multi-threaded)',
        'single-threaded': 'single-threaded (no concurrency — one connection at a time)',
    }
    print(f"[Server] Running in {mode_labels[mode]} mode")
    print(f"[Server] Serving files from: {os.path.abspath(WEBROOT)}")
    print(f"[Server] Listening on http://{HOST}:{PORT}")
    print(f"[Server] Press Ctrl+C to stop.\n")

    if mode == 'persistent':
        handler = handle_connection_persistent
    elif mode == 'non-persistent':
        handler = handle_connection_non_persistent
    else:  # single-threaded
        handler = handle_connection_persistent

    try:
        while True:
            print(f"[{_ts()}] [Server] Waiting for the next connection...")
            conn, addr = server_socket.accept()
            print(f"[{_ts()}] [Server] Accepted connection from {addr}")

            if mode == 'single-threaded':
                # No thread — this call has to fully return before the
                # loop can go back to accept() and take the next client.
                _run_handler_with_logging(handler, conn, addr)
            else:
                t = threading.Thread(target=_run_handler_with_logging, args=(handler, conn, addr))
                t.daemon = True
                t.start()
    except KeyboardInterrupt:
        print("\n[Server] Shutting down.")
    finally:
        server_socket.close()


if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else 'persistent'
    if mode not in ('persistent', 'non-persistent', 'single-threaded'):
        print("Usage: python server.py [persistent|non-persistent|single-threaded]")
        sys.exit(1)
    start_server(mode)
