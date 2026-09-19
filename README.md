<img src="https://github.com/Linux-now/Image-Assets-Lance-Debian13/blob/main/CVAIDSYS%20LOGO.png?raw=true" align="left" width="100" height="100" alt="Project Logo">


# CVAFPI Identification System SQL for Windows 11

<br clear="left"/>

CVAIDSYS (Windows) is a local school identification and attendance system for Windows 11. It uses a USB barcode scanner to identify students, stores attendance records in a local SQLite database, and can capture scan snapshots with a webcam. The system also supports student-specific NTFY parent notifications, office alerts, CSV import, audit logs, school branding, themes, and passcode-protected kiosk controls.

The application is designed to keep student and attendance data on the kiosk computer. NTFY notifications are the exception: when enabled and configured, the application sends attendance messages to `https://ntfy.sh` over the internet.

## How the system works

The application runs as a local web service. The Flask application provides the user interface and API routes, Waitress serves the application in production and development runs, and the browser displays the scanner, database, migration, log-management, and settings pages.

1. The application starts the local web service and initializes the SQLite database if it does not already exist.
2. The scanner page receives a barcode from a USB scanner or manual input and submits it to the local API.
3. The API looks up the barcode in the student database. For a recognized student, it records the attendance timestamp and optional image snapshot.
4. Repeated scans of the same barcode within two seconds are ignored. A different barcode is logged immediately and becomes the active debounce barcode.
5. An unknown barcode is never added to attendance. The scanner displays the error in the last-scanned card so staff can add the student without an interrupting dialog.
6. If parent notifications are enabled and the student has a configured topic, the application sends a background notification through NTFY.
7. Authorized staff can manage student records, review logs, import student lists, configure branding, themes, and passcode-protected kiosk controls.
8. Restart, shutdown, kiosk exit, logo upload, student changes, CSV imports, audit events, and security settings require the configured passcode. Passcodes are stored as salted PBKDF2-SHA256 hashes; the original passcode is never stored.

The application listens only on the local computer by default. It is not intended to be exposed directly to a public network.

## Windows requirements

- Windows 11 64-bit
- Python 3.11 or newer for building or development
- Microsoft Edge or Google Chrome
- A USB barcode scanner that behaves as a keyboard
- A webcam if scan photos are enabled

The packaged application does not require Python. The browser is required because the interface runs in locked browser kiosk mode.

## Before building

Complete this checklist on a Windows 11 test computer before creating the final executable:

- Confirm the computer has 64-bit Python 3.11 or newer, Edge or Chrome, and network access if NTFY will be used.
- Run the server-only test described below and open every page: launchpad, scanner, manager, logs manager, migration, and settings.
- Add one test student with a unique barcode and an NTFY topic. Scan the barcode and verify the attendance row, timestamp, saved snapshot if the camera is enabled, and the parent notification.
- Test a student without a topic, with parent notifications disabled, and with an unknown barcode. None of these should send a parent notification.
- Test CSV preview/import, log viewing/export, logo upload, passcode setup/recovery, and the configured system barcodes.
- Test an unknown barcode. Confirm that it is not added to attendance, appears as a scan error in the scanner card, and is visible in Audit Events.
- Test two rapid scans of the same barcode and confirm that only one attendance row is created. Test two different barcodes and confirm that both are logged.
- Test an application restart with a valid database backup, then verify the database opens normally. Test recovery only on a disposable copy of the data.
- Back up `CVA_Database`, `logs`, `settings.json`, and `static\custom-logo.png` before packaging.

The Linux development environment can check Python code and server routes, but it cannot produce a Windows executable. The final build must run on Windows 11.

## Build one executable

Build on Windows 11. PyInstaller creates Windows executables and cannot cross-compile a Windows binary from Debian or Linux.

1. Install 64-bit Python 3.11 or newer from python.org.
2. Copy or clone this repository to the Windows computer.
3. Double-click `build-windows.bat`.
4. Run `dist\CVAFPI-IDSYS.exe`.

The build script creates a temporary `.venv-windows` environment, installs the Windows dependencies, and builds a single file. The final executable is:

```text
dist\CVAFPI-IDSYS.exe
```

No Python installation is needed on the deployment computer after the executable has been built.

## Server-only development run

To inspect the application in a normal browser without opening kiosk mode, activate the project environment and run:

```text
python -m waitress --listen=127.0.0.1:8080 wsgi:app
```

The server listens on `http://127.0.0.1:8080`. Open that address and test the pages and APIs. To use another port:

```text
python -m waitress --listen=127.0.0.1:5050 wsgi:app
```

For a quick Python-only route check, run `python -m py_compile app.py logger.py windows_launcher.py wsgi.py`.

For a direct development run with Flask, use:

```text
python app.py
```

The Flask development server listens on `http://127.0.0.1:5000`. Use Waitress for a production-like local run.

## Kiosk mode

Starting `CVAFPI-IDSYS.exe` will:

1. Start the local Waitress WSGI server on `127.0.0.1:5000`.
2. Open Microsoft Edge or Chrome using fullscreen kiosk mode.
3. Use a dedicated `.kiosk-profile` browser profile so an existing personal browser session is not reused.
4. Keep the application local to the computer; it is not exposed to the network.

Edge is preferred when installed. Chrome is used as a fallback. If neither browser is installed, the executable reports that a kiosk browser is required.

The kiosk controls are passcode-protected. A passcode must contain 4 to 12 non-space characters; letters, numbers, and symbols are supported. `Exit kiosk mode` closes only the browser process started by this application. It does not close other Edge or Chrome windows.

The scanner also supports protected quick-access barcodes:

- `DataManagerCVAFPI8%/?` opens Student Manager.
- `LogManagerCVAFPI34#%` opens Logs & Audit Trail.
- `SettingsCVAFPI8&5?` opens the System Settings modal.

These values can be changed in the `System barcodes` section of Settings. Quick-access commands require the configured passcode before redirecting.

For the strongest Windows lockdown, configure Windows Assigned Access or Shell Launcher for the account used by the kiosk. Browser kiosk mode controls the application window, while Assigned Access controls the Windows desktop and keyboard escape paths.

## Development run

To run without building the executable, install Python 3.11 or newer and run:

```text
run-windows.bat
```

This starts the same server and browser kiosk launcher from `.venv-windows`.

The launcher serves the Flask application through Waitress `2.1.1` instead of Flask's development server.

## Notifications

### Parent notifications

Parent notifications are controlled by the `Parent notifications` setting and a topic on each student record. A successful scan sends a message such as `Student Name checked in at 09/13/2026 08:30:00 AM.` to `https://ntfy.sh/<topic>`. A blank topic or `None` skips the notification. Notification delivery happens in the background so a slow internet connection does not block the scanner.

Use unique, private topic names. Anyone who knows an NTFY topic can subscribe to it. For stronger privacy, use an authenticated NTFY server and extend the configuration before deployment.

### Office alerts

Office alerts use the configured office topic for camera-blocked alerts. They are separate from parent notifications and can be enabled independently.

## Scanner errors and audit events

An unrecognized barcode returns a scan error and is not inserted into the attendance table. The scanner keeps focus available and shows the barcode, error message, timestamp, and red `ERROR` badge in the last-scanned card. Staff can then add the missing student in Student Manager.

The Logs Manager includes a passcode-protected **Audit Events** view. It records invalid scans, duplicate scans, successful scans, settings failures and saves, invalid passcode attempts, student changes, CSV imports, and database recovery events.

Audit records are stored in SQLite and included in the automatic database backups.

## Data and backup

The executable stores writable data beside itself:

```text
CVA_Database\cva.sqlite3             Student, attendance, audit, and settings database
CVA_Database\cva.sqlite3.backup      Latest automatic SQLite backup
CVA_Database\logs_*                  Daily logs and captured snapshots
logs\                                Auxiliary application logs
settings.json                        Application settings
static\custom-logo.png              Uploaded school logo
```

Stop the kiosk before copying the database. Back up the complete application data directories, not only the executable. Do not edit the SQLite database while the application is running.

After database writes, the application creates a consistent SQLite backup and replaces the previous backup atomically. On startup, if the primary database is corrupt or cannot be opened, the application attempts to restore `CVA_Database\cva.sqlite3.backup`. If recovery fails, the application stops serving normal pages and displays a database error message instead of silently losing data.

## Security controls

The initial setup requires a 4 to 12 character passcode and a recovery question. Letters, numbers, and symbols are supported, but spaces are not. Once configured, an empty or incorrect current passcode cannot save settings. The passcode protects settings, logo uploads, student changes, CSV imports, audit events, kiosk exit, restart, shutdown, and system barcodes. The passcode is stored as a salted PBKDF2-SHA256 hash.

Themes are selected in System Settings and apply to the launchpad, scanner, student manager, logs manager, and migration pages. Supported themes are Night, Light, Grassy, Ocean, and Sunset. Accent colors must be six-digit hexadecimal colors such as `#4da3ff`.

The Windows restart and shutdown controls use the standard Windows `shutdown` command. Do not run the application from an administrator account unless Windows kiosk policy requires it.

## Project structure

- `app.py` - Flask API and application routes
- `wsgi.py` - WSGI application entry point
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

Copy the previous `CVA_Database`, `logs`, `settings.json`, and `static\custom-logo.png` files beside the new executable before starting it.

If the primary database is damaged, stop the application and preserve a copy of `CVA_Database\cva.sqlite3` before restarting. The application will attempt automatic recovery from `CVA_Database\cva.sqlite3.backup`. Review Audit Events after recovery and create a fresh external backup.

### A scan says student not found

The barcode is not present in the student database. Add or update the student in Student Manager, then scan again. The failed scan remains available in Audit Events for staff review.

### Settings will not save

Enter the current passcode. Changing the passcode also requires a complete security question and recovery answer. Leaving those fields blank is valid only when keeping the existing passcode and recovery details unchanged.

### Parent notification did not arrive

Check that parent notifications are enabled, the student topic is not blank or `None`, the kiosk has internet access, and the topic is spelled exactly the same in the NTFY subscriber and student record. Check the server console for `[ntfy Parent Error]` messages.
