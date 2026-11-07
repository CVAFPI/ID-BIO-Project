import os
import shutil
import socket
import subprocess
import sys
import threading
import time


PORT = int(os.environ.get('CVAFPI_PORT', '5000'))
APP_DIR = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))


def configure_data_directory():
    data_dir = os.environ.get('CVAFPI_DATA_DIR')
    if not data_dir:
        if getattr(sys, 'frozen', False):
            local_app_data = os.environ.get('LOCALAPPDATA')
            if not local_app_data:
                raise RuntimeError('LOCALAPPDATA is not available; cannot choose a writable data directory.')
            data_dir = os.path.join(local_app_data, 'CVAFPI-IDSYS')
        else:
            data_dir = APP_DIR

    os.makedirs(data_dir, exist_ok=True)
    if os.path.abspath(data_dir) != os.path.abspath(APP_DIR):
        student_file = os.path.join(data_dir, 'data.csv')
        backup_file = os.path.join(data_dir, 'backup-data.csv')
        if not os.path.exists(student_file):
            seed_file = backup_file if os.path.isfile(backup_file) else os.path.join(APP_DIR, 'data.csv')
            if os.path.isfile(seed_file):
                shutil.copy2(seed_file, student_file)
        if not os.path.exists(backup_file):
            seed_file = student_file if os.path.isfile(student_file) else os.path.join(APP_DIR, 'backup-data.csv')
            if os.path.isfile(seed_file):
                shutil.copy2(seed_file, backup_file)
        settings_file = os.path.join(data_dir, 'settings.json')
        settings_seed = os.path.join(APP_DIR, 'settings.json')
        if not os.path.exists(settings_file) and os.path.isfile(settings_seed):
            shutil.copy2(settings_seed, settings_file)
    os.environ['CVAFPI_DATA_DIR'] = data_dir


def wait_for_server(host='127.0.0.1', port=PORT, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.25)
    return False


def ensure_port_available(host='127.0.0.1', port=PORT):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind((host, port))
        except OSError as error:
            raise RuntimeError(f'Port {port} is already in use.') from error


def open_kiosk(url):
    profile_dir = os.path.join(os.environ['CVAFPI_DATA_DIR'], 'KioskProfile')
    os.makedirs(profile_dir, exist_ok=True)
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
            return subprocess.Popen(command, cwd=APP_DIR)
        except FileNotFoundError:
            continue
    raise RuntimeError('Microsoft Edge or Google Chrome is required for kiosk mode.')


def main():
    configure_data_directory()
    from waitress import serve
    from wsgi import app

    ensure_port_available()
    server = threading.Thread(
        target=serve,
        kwargs={'app': app, 'host': '127.0.0.1', 'port': PORT, 'threads': 4},
        daemon=True,
    )
    server.start()
    if not wait_for_server():
        raise RuntimeError(f'CVAFPI server did not start on port {PORT}.')

    browser = open_kiosk(f'http://127.0.0.1:{PORT}/')
    app.config['KIOSK_BROWSER_PROCESS'] = browser
    browser.wait()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        if getattr(sys, 'frozen', False) and os.name == 'nt':
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                None,
                str(error),
                'CVAFPI Identification System',
                0x10
            )
        raise