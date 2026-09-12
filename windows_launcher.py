import os
import socket
import shutil
import subprocess
import sys
import threading
import time


PORT = int(os.environ.get('CVAFPI_PORT', '5000'))
APP_DIR = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
os.environ.setdefault('CVAFPI_DATA_DIR', APP_DIR)


def wait_for_server(host='127.0.0.1', port=PORT, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.25)
    return False


def open_kiosk(url):
    profile_dir = os.path.join(APP_DIR, '.kiosk-profile')
    browser_paths = [
        (os.environ.get('ProgramFiles(x86)'), 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
        (os.environ.get('ProgramFiles'), 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
        (os.environ.get('LOCALAPPDATA'), 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
        (os.environ.get('ProgramFiles'), 'Google', 'Chrome', 'Application', 'chrome.exe'),
        (os.environ.get('ProgramFiles(x86)'), 'Google', 'Chrome', 'Application', 'chrome.exe'),
        (os.environ.get('LOCALAPPDATA'), 'Google', 'Chrome', 'Application', 'chrome.exe'),
    ]
    browser_commands = []
    for parts in browser_paths:
        if parts[0]:
            browser_path = os.path.join(*parts)
            if os.path.exists(browser_path):
                browser_commands.append([browser_path, '--kiosk', url, '--edge-kiosk-type=fullscreen', '--user-data-dir=' + profile_dir, '--no-first-run', '--disable-session-crashed-bubble'])
    for name in ('msedge', 'chrome'):
        if shutil.which(name):
            browser_commands.append([name, '--kiosk', url, '--user-data-dir=' + profile_dir, '--no-first-run', '--disable-session-crashed-bubble'])
    for command in browser_commands:
        try:
            browser_process = subprocess.Popen(command, cwd=APP_DIR)
            os.environ['CVAFPI_BROWSER_PID'] = str(browser_process.pid)
            return
        except FileNotFoundError:
            continue
    raise RuntimeError('Microsoft Edge or Google Chrome is required for locked kiosk mode.')


def main():
    from app import app

    server = threading.Thread(
        target=app.run,
        kwargs={'host': '127.0.0.1', 'port': PORT, 'debug': False, 'use_reloader': False},
        daemon=True,
    )
    server.start()
    if not wait_for_server():
        raise RuntimeError(f'CVAFPI server did not start on port {PORT}.')
    open_kiosk(f'http://127.0.0.1:{PORT}/')
    server.join()


if __name__ == '__main__':
    main()