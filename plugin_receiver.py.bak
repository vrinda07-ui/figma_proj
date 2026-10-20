
import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = 8765

INPUT_FILE = ROOT / "dataset" / "new_dashboard" / "figma_data.json"

PIPELINE = [ ]


class Handler(BaseHTTPRequestHandler):
    
    def send_json(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


    def do_POST(self):
        if self.path != "/ingest":
            self.send_json(404, {"error": "Unknown endpoint"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                self.send_json(400, {"error": "Empty request"})
                return

            payload = json.loads(self.rfile.read(length))

            if "document" not in payload:
                self.send_json(400, {
                    "error": "Missing document in design data"
                })
                return

            INPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
            INPUT_FILE.write_text(
                json.dumps(payload, indent=2),
                encoding="utf-8",
            )

            logs = []

            for label, script in PIPELINE:
                result = subprocess.run(
                    [sys.executable, str(ROOT / script)],
                    cwd=str(ROOT),
                    capture_output=True,
                    text=True,
                    timeout=600,
                )

                logs.append({
                    "step": label,
                    "return_code": result.returncode,
                    "stdout": result.stdout[-4000:],
                    "stderr": result.stderr[-4000:],
                })

                if result.returncode != 0:
                    print(f"\nERROR IN STEP: {label}")
                    print("STDOUT:")
                    print(result.stdout)
                    print("STDERR:")
                    print(result.stderr)

                    self.send_json(500, {
                        "error": f"{label} failed",
                        "details": result.stderr[-3000:],
                        "logs": logs,
                    })
                    return

            self.send_json(200, {
                "message": "Design received and pipeline completed.",
                "logs": logs,
            })

        except Exception as exc:
            self.send_json(500, {"error": str(exc)})

    def log_message(self, format, *args):
        print("%s - %s" % (self.address_string(), format % args))


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Waiting for Figma plugin at http://{HOST}:{PORT}")
    print("Keep this terminal open while using the plugin.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping receiver.")
    finally:
        server.server_close()
