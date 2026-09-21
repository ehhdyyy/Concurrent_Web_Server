"""
PA1 — HTTP Web Server
client.py

Part C — Concurrency Experiment

This client plays ONE of two roles per run, chosen on the command line:

    python client.py slow      <- requests a large object, reads it back
                                   deliberately slowly (simulating a slow
                                   or struggling client)
    python client.py fast      <- requests a small file and reports how
                                   long it had to wait for a response

YOUR TASK:
- Implement the two functions marked with TODO below:
      slow_client()
      fast_client()
- Design an experiment to showcase the benefits of a concurrent server
- Measure, analyze and report your findings

"""

import socket
import sys
import time


def _ts():
    """
    Wall-clock timestamp for log lines, e.g. '22:41:07.183'. Use this in
    every print() you write for slow_client() and fast_client() below, so
    your client terminal output can be lined up against server.py's log
    (which already timestamps its own lines the same way) and against
    your other client's terminal. Without a shared clock, three separate
    screenshots can't be cross-checked against each other.
    """
    return time.strftime('%H:%M:%S', time.localtime()) + f'.{int((time.time() % 1) * 1000):03d}'

# ---------------------------------------------------------------------------
# Configuration — must match server.py
# ---------------------------------------------------------------------------
HOST            = '127.0.0.1'
PORT            = 8080
LARGE_FILE_PATH = '/large.bin'   # requested by the slow client — generate this first, see above
SMALL_FILE_PATH = '/about.html'  # requested by the fast client

SLOW_READ_CHUNK_SIZE = 16     # bytes per recv() call — deliberately tiny
SLOW_READ_DELAY      = 1.5    # seconds to sleep between recv() calls
PRINT_INTERVAL        = 1.0   # only print progress at most once per this
                               # many seconds, so a multi-second slow read
                               # doesn't scroll your terminal past what a
                               # single screenshot can capture


# ===========================================================================
# ── BOILERPLATE — do not modify ──────────────────────────────────────────────
# ===========================================================================

def read_http_response(sock):
    """
    Read exactly one complete HTTP response off an already-open socket, at
    full speed: read until the header block is complete, pull
    Content-Length out of the headers, then read exactly that many more
    body bytes. Use this in fast_client() — it is NOT what slow_client()
    should use, since slow_client() needs to deliberately throttle its
    reads instead of draining the socket as fast as possible.

    Parameters:
        sock (socket.socket): an already-connected socket with a response
                               waiting to be read

    Returns:
        bytes: the complete raw response (headers + body)
    """
    data = b''
    headers_end = -1
    while headers_end == -1:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
        headers_end = data.find(b'\r\n\r\n')

    content_length = 0
    if headers_end != -1:
        header_text = data[:headers_end].decode('utf-8', errors='ignore')
        for line in header_text.split('\r\n'):
            if line.lower().startswith('content-length:'):
                content_length = int(line.split(':', 1)[1].strip())
                break

        body_so_far = len(data) - (headers_end + 4)
        while body_so_far < content_length:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
            body_so_far += len(chunk)

    return data


def build_get_request(host, port, path):
    """Build a minimal HTTP GET request with Connection: close."""
    return (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
    ).encode('utf-8')


def slow_client(host, port, path):
    """
    Parameters:
        host (str): server hostname or IP
        port (int): server port
        path (str): URL path to request, e.g. '/large.bin'
    """
    # TODO: implement this function
    # connect to the server
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((host, port))
        request = build_get_request(host, port, path)
        sock.sendall(request)

        current_time = time.time()
        start_time = current_time
        last_print_time = current_time
        
        total_bytes_received = 0

        while True:
            chunk = sock.recv(SLOW_READ_CHUNK_SIZE)
            if not chunk:
                break
            total_bytes_received += len(chunk)
            current_time = time.time()
            if current_time - last_print_time >= PRINT_INTERVAL:
                print(f"[{_ts()}] Received {total_bytes_received} bytes so far...")
                last_print_time = current_time
            time.sleep(SLOW_READ_DELAY)

        print(f"[{_ts()}] Finished receiving {total_bytes_received} bytes. Took {current_time - start_time:.2f} seconds.")
        sock.close()


def fast_client(host, port, path):
    """
    Parameters:
        host (str): server hostname or IP
        port (int): server port
        path (str): URL path to request, e.g. '/about.html'
    """
    # TODO: implement this function
    # connect to the server
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((host, port))
        request = build_get_request(host, port, path)
        sock.sendall(request)

        start_time = time.time()
        response = read_http_response(sock)
        end_time = time.time()

        print(f"[{_ts()}] Received {len(response)} bytes in {end_time - start_time:.2f} seconds.")
        sock.close()


# ===========================================================================
# ── BOILERPLATE — do not modify below this line ─────────────────────────────
# ===========================================================================

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ('slow', 'fast'):
        print("Usage: python client.py [slow|fast]")
        print("\nRun these in TWO separate terminals:")
        print("    Terminal A:  python client.py slow")
        print("    Terminal B:  python client.py fast   (start ~1s after A)")
        print("\nBoth terminals target whatever server mode is currently")
        print("running in server.py — restart the server in a different")
        print("mode and repeat both commands to compare.")
        sys.exit(1)

    role = sys.argv[1]

    if role == 'slow':
        print(f"[SlowClient] Requesting {LARGE_FILE_PATH} from {HOST}:{PORT}, reading slowly on purpose...")
        slow_client(HOST, PORT, LARGE_FILE_PATH)
    else:
        print(f"[FastClient] Requesting {SMALL_FILE_PATH} from {HOST}:{PORT}...")
        fast_client(HOST, PORT, SMALL_FILE_PATH)


if __name__ == "__main__":
    main()
