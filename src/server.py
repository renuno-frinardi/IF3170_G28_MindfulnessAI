"""Backend HTPP dengan python"""

# Import library
import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import random
import threading
import traceback
from urllib.parse import unquote, urlsplit
from src.experiment import INPUT_DIR, OUTPUT_DIR, REPO_ROOT, parse_text, run_experiment, save_envelope
from src.objective import DEFAULT_OBJECTIVE

# Definisi variabel global
RUN_LOCK = threading.Lock()
MAX_BODY = 1_000_000

# Membentuk kelas handler HTTP request dengan method untuk menangani request dan response
class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

    # Menyimpan seluruh fil .js sebagai text/javascript
    def guess_type(self, path):
        return "text/javascript" if str(path).endswith(".js") else super().guess_type(path)

    # Formatting dasar header
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    # Formatting untuk bentuk dasar JSON response
    def json_response(self, status, value):
        data = json.dumps(value, allow_nan=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # Handle GET
    def do_GET(self):
        if not self.local_request():
            self.json_response(403, {"error": "Only local requests are allowed."})
            return
        path = unquote(urlsplit(self.path).path)
        if path == "/":
            self.send_response(302)
            self.send_header("Location", "/src/gui/frontend/index.html")
            self.end_headers()
        elif path == "/api/inputs":
            files = [{"name": p.name, "stem": p.stem, "size": p.stat().st_size, "modified": p.stat().st_mtime} for p in INPUT_DIR.glob("*.txt") if p.is_file() and not p.is_symlink()]
            self.json_response(200, {"files": sorted(files, key=lambda p: p["name"].lower())})
        elif path == "/api/results":
            files = [{"name": p.name, "size": p.stat().st_size, "modified": p.stat().st_mtime} for p in OUTPUT_DIR.glob("*.json") if p.is_file() and not p.is_symlink()]
            self.json_response(200, {"files": sorted(files, key=lambda p: p["modified"], reverse=True)})
        elif path == "/health":
            self.json_response(200, {"status": "ok"})
        elif self.allowed_file(path):
            super().do_GET()
        else:
            self.send_error(404, "File not found")

    # Filter file yang dibolehkkan
    @staticmethod
    def allowed_file(path):
        if "\\" in path or "\x00" in path:
            return False
        target = (REPO_ROOT / path.lstrip("/")).resolve()
        roots = {REPO_ROOT / "src/gui": {".html", ".css", ".js", ".ttf", ".otf", ".woff", ".woff2", ".png", ".svg", ".ico"}, INPUT_DIR: {".txt"}, OUTPUT_DIR: {".json", ".txt"}}
        return target.is_file() and any(target.is_relative_to(root.resolve()) and target.suffix in suffixes for root, suffixes in roots.items())

    # Membaca header
    def do_HEAD(self):
        if self.local_request() and self.allowed_file(unquote(urlsplit(self.path).path)):
            super().do_HEAD()
        else:
            self.send_error(404)

    # Handle request lokal
    def local_request(self):
        host = self.headers.get("Host", "")
        allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        origin = self.headers.get("Origin")
        return host in allowed and (origin is None or origin == f"http://{host}")

    # Handle POST
    def do_POST(self):
        if not self.local_request():
            self.json_response(403, {"error": "Hanya request lokal dengan asal yang sama, yang dibolehkan"})
            return
        if urlsplit(self.path).path != "/api/run":
            self.json_response(404, {"error": "Endpoint tidak diketahui"})
            return
        if not RUN_LOCK.acquire(blocking=False):
            self.json_response(409, {"error": "Proses lainnya lagi dijalankan"})
            return
        try:
            if self.headers.get_content_type() != "application/json":
                raise ValueError("Send application/json with text, seed, repeats and optional objective.")
            size = int(self.headers.get("Content-Length", "0"))
            if size > MAX_BODY:
                self.connection.settimeout(2)
                try:
                    self.rfile.read(min(size, MAX_BODY * 2))
                except TimeoutError:
                    pass
                self.json_response(413, {"error": "Input melebihi batas 1,000,000 byte"})
                return
            if size <= 0:
                raise ValueError("JSON body harus tidak kosong")
            self.connection.settimeout(10)
            data = json.loads(self.rfile.read(size).decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("JSON harus dalam bentuk objek")
            seed = data.get("seed")
            if seed is None:
                seed = random.SystemRandom().randrange(2**31)
            problem = parse_text(data.get("text"))
            objective = data.get("objective", DEFAULT_OBJECTIVE)
            envelope = run_experiment(problem, seed, data.get("repeats", 3), input_text=data["text"], objective=objective)
            saved = save_envelope(envelope)
            self.json_response(200, {"saved_as": saved.relative_to(REPO_ROOT).as_posix(),
                                     "saved_txt": saved.with_suffix(".txt").relative_to(REPO_ROOT).as_posix(),
                                     "envelope": envelope})
        except (ValueError, TimeoutError) as exc:
            self.json_response(400, {"error": str(exc)})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            traceback.print_exc()
            self.json_response(500, {"error": "Error terjadi, cek console untuk lebih detail"})
        finally:
            RUN_LOCK.release()

# Fungsi utama server
def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    try:
        with ThreadingHTTPServer(("127.0.0.1", args.port), Handler) as server:
            print(f"Menyusun viewer: http://127.0.0.1:{server.server_port}/", flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        pass
    except OSError as exc:
        parser.exit(1, f"Tidak bisa memulai server: {exc}. Coba menggunakan port lain --port.\n")

# Entrypoint server
if __name__ == "__main__":
    main()
