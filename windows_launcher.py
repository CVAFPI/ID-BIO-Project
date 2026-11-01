import os
import shutil
import socket
import subprocess
import sys
import threading
import time


PORT = int(os.environ.get("CVAFPI_PORT", "5000"))
APP_DIR = os.path.dirname(
    os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)
)
os.environ.setdefault("CVAFPI_DATA_DIR", APP_DIR)


def wait_for_server(host="127.0.0.1", port=PORT, timeout=30, server_thread=None):
    """Wait until the HTTP server's TCP port is accepting connections."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if server_thread is not None and not server_thread.is_alive():
            return False
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.25)
    return False


def find_browser():
    candidates = [
        (os.environ.get("ProgramFiles(x86)"), "Microsoft", "Edge", "Application", "msedge.exe"),
        (os.environ.get("ProgramFiles"), "Microsoft", "Edge", "Application", "msedge.exe"),
        (os.environ.get("LOCALAPPDATA"), "Microsoft", "Edge", "Application", "msedge.exe"),
        (os.environ.get("ProgramFiles"), "Google", "Chrome", "Application", "chrome.exe"),
        (os.environ.get("ProgramFiles(x86)"), "Google", "Chrome", "Application", "chrome.exe"),
        (os.environ.get("LOCALAPPDATA"), "Google", "Chrome", "Application", "chrome.exe"),
    ]
    for parts in candidates:
        if parts[0]:
            path = os.path.join(*parts)
            if os.path.isfile(path):
                return path
    return shutil.which("msedge") or shutil.which("chrome")


def open_kiosk(url):
    browser = find_browser()
    if not browser:
        raise RuntimeError("Microsoft Edge or Google Chrome is required for kiosk mode.")

    profile_dir = os.path.join(APP_DIR, ".kiosk-profile")
    os.makedirs(profile_dir, exist_ok=True)
    command = [
        browser, "--kiosk", url,
        "--user-data-dir=" + profile_dir,
        "--no-first-run", "--disable-session-crashed-bubble",
    ]
    if os.path.basename(browser).lower() == "msedge.exe":
        command.append("--edge-kiosk-type=fullscreen")

    process = subprocess.Popen(command, cwd=APP_DIR)
    os.environ["CVAFPI_BROWSER_PID"] = str(process.pid)
    return process


def main():
    # Set data directory before importing app modules.
    from waitress import create_server
    from wsgi import app

    http_server = create_server(app, host="127.0.0.1", port=PORT, threads=4)
    server_thread = threading.Thread(
        target=http_server.run, name="cvafpi-http-server", daemon=True
    )
    browser_process = None
    server_thread.start()

    try:
        if not wait_for_server(server_thread=server_thread):
            raise RuntimeError(
                f"CVAFPI server did not become ready on port {PORT} within 30 seconds."
            )

        print(f"CVAFPI server ready at http://127.0.0.1:{PORT}/")
        browser_process = open_kiosk(f"http://127.0.0.1:{PORT}/")
        print("Kiosk launched. Closing the kiosk will stop the server.")
        browser_process.wait()
    finally:
        # Lifecycle: server starts -> kiosk opens -> kiosk exits -> server closes.
        if browser_process is not None and browser_process.poll() is None:
            browser_process.terminate()
            try:
                browser_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                browser_process.kill()
                browser_process.wait(timeout=5)
        http_server.close()
        server_thread.join(timeout=5)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"CVAFPI launcher error: {exc}", file=sys.stderr)
        raise
