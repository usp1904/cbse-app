import os
import sys
import signal
import subprocess
import time
import socket
import threading
import http.server
import urllib.request

WORKER_COUNT = int(os.environ.get("WORKER_COUNT", 4))
BASE_PORT = int(os.environ.get("BASE_PORT", 9091))
LB_PORT = int(os.environ.get("LB_PORT", 9090))
APP_SCRIPT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "server.py")


def find_free_port(start):
    port = start
    while port < start + 100:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
        port += 1
    return None


class LoadBalancerProxyHandler(http.server.BaseHTTPRequestHandler):
    workers = []
    lock = threading.Lock()
    next_worker = 0

    def do_request(self):
        start = time.time()
        with LoadBalancerProxyHandler.lock:
            idx = LoadBalancerProxyHandler.next_worker
            LoadBalancerProxyHandler.next_worker = (idx + 1) % len(LoadBalancerProxyHandler.workers)

        worker = LoadBalancerProxyHandler.workers[idx]
        upstream = f"http://127.0.0.1:{worker['port']}{self.path}"

        body = None
        if self.command in ("POST", "PUT", "PATCH"):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length > 0 else b""

        req = urllib.request.Request(upstream, data=body, method=self.command)
        for key, val in self.headers.items():
            if key.lower() not in ("host", "transfer-encoding"):
                req.add_header(key, val)

        try:
            resp = urllib.request.urlopen(req, timeout=30)
            data = resp.read()
            self.send_response(resp.status)
            for key, val in resp.headers.items():
                if key.lower() not in ("content-length", "transfer-encoding", "content-encoding"):
                    self.send_header(key, val)
            self.send_header("X-Upstream", f"worker-{idx+1}:{worker['port']}")
            elapsed = int((time.time() - start) * 1000)
            self.send_header("X-Response-Time", f"{elapsed}ms")
            self.end_headers()
            self.wfile.write(data)
        except urllib.error.HTTPError as e:
            data = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(data)
        except (urllib.error.URLError, socket.timeout) as e:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Upstream unavailable", "detail": str(e)}).encode())

    do_GET = do_request
    do_POST = do_request
    do_PUT = do_request
    do_DELETE = do_request
    do_PATCH = do_request

    def log_message(self, fmt, *args):
        pass


class MeshLoadBalancer:
    def __init__(self):
        self.workers = []
        self.running = True

    def start_workers(self):
        print(f"Starting {WORKER_COUNT} worker processes...")
        for i in range(WORKER_COUNT):
            port = BASE_PORT + i
            env = dict(os.environ, PORT=str(port))
            proc = subprocess.Popen(
                [sys.executable, APP_SCRIPT],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            self.workers.append({"proc": proc, "port": port, "index": i})
            print(f"  Worker {i+1} on port {port} (PID: {proc.pid})")
            time.sleep(0.3)

    def health_check(self):
        for w in self.workers:
            try:
                with socket.create_connection(("127.0.0.1", w["port"]), timeout=2):
                    pass
            except (socket.timeout, ConnectionRefusedError):
                print(f"  Worker {w['index']+1} on port {w['port']} is DOWN, restarting...")
                env = dict(os.environ, PORT=str(w["port"]))
                proc = subprocess.Popen(
                    [sys.executable, APP_SCRIPT],
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )
                w["proc"] = proc
                print(f"  Restarted worker {w['index']+1} (PID: {proc.pid})")

    def run(self):
        self.start_workers()
        LoadBalancerProxyHandler.workers = self.workers

        server = http.server.HTTPServer(("0.0.0.0", LB_PORT), LoadBalancerProxyHandler)
        proxy_thread = threading.Thread(target=server.serve_forever, daemon=True)
        proxy_thread.start()

        print("\nMesh Load Balancer running on http://0.0.0.0:%d" % LB_PORT)
        ports_str = ', '.join("127.0.0.1:%d" % w["port"] for w in self.workers)
        print("Workers: " + ports_str)
        print("Round-robin proxying with health checks every 15s.")

        def shutdown(sig, frame):
            print("\nShutting down all workers...")
            server.shutdown()
            for w in self.workers:
                try:
                    w["proc"].terminate()
                except Exception:
                    pass
            sys.exit(0)

        signal.signal(signal.SIGINT, shutdown)
        signal.signal(signal.SIGTERM, shutdown)

        try:
            while self.running:
                time.sleep(15)
                self.health_check()
        except KeyboardInterrupt:
            shutdown(None, None)


if __name__ == "__main__":
    lb = MeshLoadBalancer()
    lb.run()
