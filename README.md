<img src="https://github.com/Linux-now/Image-Assets-Lance-Debian13/blob/main/CVAIDSYS%20LOGO.png?raw=true" align="left" width="100" height="100" alt="Project Logo">


# CVAFPI Identification System v2.1.1

<br clear="left"/>


Windows 11 kiosk application for barcode attendance, camera snapshots, CSV student records, audit logs, and optional ntfy notifications.

This is the CSV edition. Student records remain in `data.csv` and `backup-data.csv`; attendance history remains in `CVA_Database` as dated CSV files with snapshot images.

## Requirements

- Windows 11 64-bit
- Python 3.11 or newer with the Python launcher enabled
- Microsoft Edge or Google Chrome
- Internet access during the first setup for Python packages

## Run from source

Double-click `CVAFPI IDENTIFICATION SYSTEM.bat`. It creates `venv`, installs `requirements.txt`, checks the CSV files, starts the Flask application through Waitress, and opens the kiosk browser.

The production WSGI target is `wsgi:app`. To start it manually from the project directory:

```bat
venv\Scripts\waitress-serve.exe --listen=0.0.0.0:5000 --threads=4 --url-scheme=http wsgi:app
```

## Build the executable on Windows 11

The executable must be built on Windows. PyInstaller does not create a Windows
executable when run on Linux.

### 1. Install the prerequisites

Install Python 3.11 or newer from <https://www.python.org/downloads/windows/>.
During installation, enable **Add python.exe to PATH** and install the Python
launcher. Install Microsoft Edge or Google Chrome for kiosk mode.

### 2. Open the project folder

Extract or clone this repository to a local Windows folder. Open that folder in
File Explorer, click the address bar, type `cmd`, and press Enter. Confirm that
the folder contains `build-windows.bat`, `requirements.txt`, and
`ID-BIO-Project.spec`.

### 3. Build the `.exe`

Run this command in the project folder:

```bat
build-windows.bat
```

The script creates `.venv-windows`, installs the Python dependencies and
PyInstaller, then uses `ID-BIO-Project.spec` to create:

```text
dist\CVAFPI-IDSYS.exe
```

The script also copies `data.csv`, `backup-data.csv`, and `settings.json` into
`dist`, and creates writable `CVA_Database` and `logs` folders there.

### 4. Run the compiled application

Run this command from the project folder:

```bat
run-windows.bat
```

Or open `dist\CVAFPI-IDSYS.exe` directly. Do not move only the `.exe` to
another folder. Keep the executable and its data files together:

```text
dist/
  CVAFPI-IDSYS.exe
  data.csv
  backup-data.csv
  settings.json
  CVA_Database/
  logs/
```

The compiled launcher sets `CVAFPI_DATA_DIR` to its own directory. Templates
and static assets are bundled into the executable, while CSV files, settings,
logs, snapshots, and uploaded branding remain writable beside it.

### Rebuild after code changes

Run `build-windows.bat` again. It cleans and rebuilds the PyInstaller output.
Copy any updated CSV or settings files into `dist` only when you intentionally
want to replace the executable's local data.

### Common build problems

- **`py` is not recognized:** reinstall Python and enable the Python launcher,
  or create `.venv-windows` manually with `python -m venv .venv-windows`.
- **The browser does not open:** install Microsoft Edge or Google Chrome.
- **The port is busy:** close another copy of the application or stop the
  process using port `5000` before starting again.
- **Student records are missing:** confirm that `data.csv` and
  `backup-data.csv` are beside `CVAFPI-IDSYS.exe`.

Keep these items beside the executable so the CSV data remains writable:

```text
dist/
  CVAFPI-IDSYS.exe
  data.csv
  backup-data.csv
  settings.json
  CVA_Database/
  logs/
```

The compiled launcher sets `CVAFPI_DATA_DIR` to its own directory. Bundled templates and static assets remain read-only application resources, while CSV files, settings, logs, snapshots, and uploaded branding stay beside the executable.

## CSV features

- Add, edit, delete, preview, merge, and replace student records.
- Keep `data.csv` and `backup-data.csv` synchronized.
- Record daily attendance in `CVA_Database\logs_YYYY-MM-DD\logs_YYYY-MM-DD.csv`.
- Save scanner snapshots beside the daily attendance CSV.
- Automatically remove attendance folders older than seven days.
- Export attendance logs from the logs manager.

Required student CSV columns:

```text
BARCODE,NAME,GRADE,SECTION,ACCESS,COLOR,NTFY_TOPIC
```

## Project structure

```text
app.py                       Flask routes and API
logger.py                   CSV student and attendance storage
wsgi.py                     Production WSGI export
windows_launcher.py         Waitress and kiosk browser launcher
ID-BIO-Project.spec         PyInstaller configuration
build-windows.bat           Windows executable build script
run-windows.bat             Compiled executable runner
CVAFPI IDENTIFICATION SYSTEM.bat  Source-mode runner
requirements.txt            Windows Python dependencies
data.csv                   Primary student CSV
backup-data.csv             Student CSV backup
CVA_Database/               Attendance CSV files and snapshots
logs/                       Runtime log directory
templates/                  Flask HTML templates
static/                     Frontend assets and logos
ID-CODES FOR SYSTEM/        Reference control barcodes
```

## Hardware controls

The scanner interface provides controls for returning to the launchpad, exiting kiosk mode, restarting Windows, and shutting down Windows. Keep printed control barcodes secured because they trigger local system actions.

## Data safety

Do not manually edit `data.csv` while the application is running. Use the Student Manager or CSV Migration pages so the primary and backup CSV files stay synchronized.
