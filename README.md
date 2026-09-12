# CVAFPI Identification System for Windows 11

A local Windows kiosk application for barcode attendance, student management, CSV migration, audit logs, webcam snapshots, school branding, and PIN-protected system controls.

## Windows requirements

- Windows 11 64-bit
- Python 3.11 or newer for building or development
- Microsoft Edge or Google Chrome
- A USB barcode scanner that behaves as a keyboard
- A webcam if scan photos are enabled

The packaged application does not require Python. The browser is required because the interface runs in locked browser kiosk mode.

## Build one executable

Build on Windows 11. PyInstaller creates Windows executables and cannot cross-compile a Windows binary from Debian or Linux.

1. Install 64-bit Python 3.11 or newer from python.org.
2. Copy or clone this repository to the Windows computer.
3. Double-click `build-windows.bat`.
4. Run `dist\\CVAFPI-IDSYS.exe`.

The build script creates a temporary `.venv-windows` environment, installs the Windows dependencies, and builds a single file. The final executable is:

```text
dist\\CVAFPI-IDSYS.exe
```

No Python installation is needed on the deployment computer after the executable has been built.

## Kiosk mode

Starting `CVAFPI-IDSYS.exe` will:

1. Start the local Flask server on `127.0.0.1:5000`.
2. Open Microsoft Edge or Chrome using fullscreen kiosk mode.
3. Use a dedicated `.kiosk-profile` browser profile so an existing personal browser session is not reused.
4. Keep the application local to the computer; it is not exposed to the network.

Edge is preferred when installed. Chrome is used as a fallback. If neither browser is installed, the executable reports that a kiosk browser is required.

The kiosk controls are PIN-protected. `Exit kiosk mode` closes only the browser process started by this application. It does not close other Edge or Chrome windows.

For the strongest Windows lockdown, configure Windows Assigned Access or Shell Launcher for the account used by the kiosk. Browser kiosk mode controls the application window, while Assigned Access controls the Windows desktop and keyboard escape paths.

## Development run

To run without building the executable, install Python 3.11 or newer and run:

```text
run-windows.bat
```

This starts the same server and browser kiosk launcher from `.venv-windows`.

## Data and backup

The executable stores writable data beside itself:

```text
CVA_Database\\cva.sqlite3   Student, attendance, and settings database
CVA_Database\\logs_*         Daily logs and captured snapshots
logs\\                         Auxiliary application logs
settings.json                  Application settings
static\\custom-logo.png       Uploaded school logo
```

Stop the kiosk before copying the database. Back up the complete application data directories, not only the executable. Do not edit the SQLite database while the application is running.

## Security controls

The initial setup requires a 4 to 12 digit PIN and a recovery question. The PIN protects settings, logo uploads, kiosk exit, restart, shutdown, and system barcodes.

The Windows restart and shutdown controls use the standard Windows `shutdown` command. Do not run the application from an administrator account unless Windows kiosk policy requires it.

## Project structure

- `app.py` - Flask API and application routes
- `logger.py` - SQLite database and attendance logging
- `windows_launcher.py` - local server and browser kiosk launcher
- `ID-BIO-Project.spec` - single-file PyInstaller configuration
- `build-windows.bat` - Windows build script
- `run-windows.bat` - Windows development launcher
- `templates/` - application pages
- `static/` - packaged interface assets

## Troubleshooting

### The build does not start

Run `build-windows.bat` from a Windows command prompt and confirm that 64-bit Python is available with:

```text
py --version
```

### The browser does not open

Install Microsoft Edge or Google Chrome, then start the executable again. The application intentionally does not fall back to a normal, unlocked browser window.

### Port 5000 is already in use

Close the other local service using port 5000, then restart the executable. The application uses port 5000 by default.

### Existing records are missing

Copy the previous `CVA_Database`, `logs`, `settings.json`, and `static\\custom-logo.png` files beside the new executable before starting it.
