import os
import sys
import webbrowser
import threading
import time
import socket
import uvicorn
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure root directory is on Python path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.database import init_db

def find_available_port(start_port=8000, max_attempts=10):
    for p in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    return start_port

def open_browser(port):
    time.sleep(1.5)
    url = f"http://localhost:{port}"
    print(f"\n[+] Launching Aura Web Interface at {url} ...")
    webbrowser.open(url)

def main():
    port_env = os.getenv("PORT")
    if port_env:
        port = int(port_env)
        host = "0.0.0.0"
        is_cloud = True
    else:
        port = find_available_port(8000)
        host = "127.0.0.1"
        is_cloud = False

    print("=" * 60)
    print("           [+] AURA - AI PERSONAL ASSISTANT [+]           ")
    print("=" * 60)
    print("[*] Initializing Database & Vector Engine...")
    init_db()
    print(f"[✓] Ready! Starting FastAPI Web Server on host {host} port {port}...")
    if not is_cloud:
        print(f"[*] Open in browser: http://localhost:{port}")
    print("=" * 60)

    # Automatically launch browser only in local mode
    if not is_cloud:
        threading.Thread(target=open_browser, args=(port,), daemon=True).start()

    # Start Uvicorn Server
    uvicorn.run("backend.app:app", host=host, port=port, reload=False, log_level="info")

if __name__ == "__main__":
    main()
