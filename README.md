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

This project must be built on Windows to produce the final `.exe` file. PyInstaller
will not create a Windows executable from a Linux environment.

Use the steps below when creating the production kiosk build for distribution or testing.

### 1. Install the required software

Before you build anything, install the following on a Windows 11 machine:

- Python 3.11 or newer from <https://www.python.org/downloads/windows/>
- The Python launcher enabled during installation
- Microsoft Edge or Google Chrome for the kiosk browser
- Git if you are cloning the repository instead of using a local zip file

Important: during the Python install, check the option to add Python to PATH and enable the Python launcher.

### 2. Prepare the project folder

Copy or clone this repository to a local Windows folder such as:

```text
C:\Users\YourName\Desktop\ID-BIO-Project
```

Open that folder in File Explorer, then do one of these:

- click the address bar,
- type `cmd`,
- press Enter.

This opens a Command Prompt in the project directory.

Confirm the folder contains these build files:

```text
build-windows.bat
ID-BIO-Project.spec
requirements.txt
app.py
logger.py
wsgi.py
```

If those files are missing, the build will not run correctly.

### 3. Understand what the build script does

The script `build-windows.bat` should be treated as the official Windows build command.
It performs the following actions automatically:

1. Creates a Windows virtual environment named `.venv-windows`
2. Installs the Python dependencies from `requirements.txt`
3. Installs PyInstaller if it is not already present
4. Runs PyInstaller using `ID-BIO-Project.spec`
5. Produces the executable in `dist\CVAFPI-IDSYS.exe`
6. Copies `data.csv`, `backup-data.csv`, and `settings.json` into the output folder
7. Creates writable `CVA_Database` and `logs` directories beside the executable

This is the exact command you run:

```bat
build-windows.bat
```

### 4. Build the executable

From the project folder, run:

```bat
build-windows.bat
```

Wait until the process finishes. The result should be a generated file similar to:

```text
dist\CVAFPI-IDSYS.exe
```

If the build is successful, you should also see a `dist` folder with the supporting runtime files.

### 5. Verify the output folder

After the build completes, the output should look like this:

```text
dist/
  CVAFPI-IDSYS.exe
  data.csv
  backup-data.csv
  settings.json
  CVA_Database/
  logs/
```

This layout is intentional. The executable needs its data files and writable folders beside it.

Do not move only the `.exe` into another folder. Leave the CSV files, settings, logs,
and database directory with it.

### 6. Run the compiled application

You can start the built app in either of these ways:

#### Option A: from the project folder

```bat
run-windows.bat
```

#### Option B: run the built executable directly

```bat
dist\CVAFPI-IDSYS.exe
```

The compiled startup code sets `CVAFPI_DATA_DIR` to the app's own output directory. That means
CSV records, logs, snapshots, and settings remain writable next to the executable while the
bundled Flask templates and static files remain packaged with the app.

### 7. Rebuild after code changes

Whenever you update the Python code, run the build again:

```bat
build-windows.bat
```

This rebuilds the app from scratch and refreshes the output in `dist`.

Only copy updated CSV or settings files into `dist` if you intentionally want to replace the local app data.

### Common build problems

- **`py` is not recognized:** reinstall Python and enable the Python launcher, or create the virtual environment manually with:

  ```bat
  python -m venv .venv-windows
  ```

- **The browser does not open:** install Microsoft Edge or Google Chrome.
- **The port is busy:** close another instance of the app or stop the process using port `5000`.
- **Student records are missing:** confirm that `data.csv` and `backup-data.csv` are located beside `CVAFPI-IDSYS.exe`.
- **The build stops unexpectedly:** make sure the project folder is not nested inside a protected folder such as OneDrive or a system-managed directory.

### Required output layout

Keep these files beside the executable so the app can read and write the data safely:

```text
dist/
  CVAFPI-IDSYS.exe
  data.csv
  backup-data.csv
  settings.json
  CVA_Database/
  logs/
```

This layout ensures the application can maintain daily attendance records, student CSV data, and runtime logs without breaking the packaged executable.

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
app.py                       Flask routes, kiosk UI, and app logic
logger.py                    CSV persistence, attendance logging, and backups
wsgi.py                      Production WSGI export
windows_launcher.py          Waitress and kiosk browser launcher
jsbarcode.js                 Barcode rendering library used by the UI
settings.json                Runtime settings and branding configuration
ID-BIO-Project.spec          PyInstaller build configuration
build-windows.bat            Windows executable build script
run-windows.bat              Windows launcher for the compiled app
CVAFPI IDENTIFICATION SYSTEM.bat  Source-mode launcher
requirements.txt             Python dependencies
LICENSE                      Project license
README.md                    Project documentation
data.csv                     Primary student records
backup-data.csv              Backup student records
CVA_Database/                Attendance logs and snapshot folders
logs/                       Generated runtime logs
templates/                   Flask HTML templates
static/                     Frontend CSS, JS, and assets
ID-CODES FOR SYSTEM/        Reference control barcode files
```

## Hardware controls

The scanner interface provides controls for returning to the launchpad, exiting kiosk mode, restarting Windows, and shutting down Windows. Keep printed control barcodes secured because they trigger local system actions.

## Data safety

Do not manually edit `data.csv` while the application is running. Use the Student Manager or CSV Migration pages so the primary and backup CSV files stay synchronized.
