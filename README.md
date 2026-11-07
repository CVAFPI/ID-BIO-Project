<img src="https://github.com/Linux-now/Image-Assets-Lance-Debian13/blob/main/CVAIDSYS%20LOGO.png?raw=true" align="left" width="100" height="100" alt="Project Logo">


# CVAFPI Identification System v2.2.0

<br clear="left"/>


Windows 11 kiosk application for barcode attendance, camera snapshots, CSV student records, audit logs, and optional ntfy notifications.

This release keeps student records in `data.csv` and `backup-data.csv`, and attendance history in `CVA_Database` as dated CSV files with snapshot images. Packaged Windows builds store writable data under `%LOCALAPPDATA%\CVAFPI-IDSYS`, not beside the application in Program Files. When running from source, data is stored in the project directory.

Version 2.2.0 incorporates the updated Windows kiosk interface, administrator passcodes and recovery, a protected security audit manager, configurable system-command barcodes, and optional ntfy attendance alerts. Student and attendance data continue to use CSV.

## Requirements

- Windows 11 64-bit
- Python 3.11 or newer, 64-bit, with the Python launcher enabled to build the executable
- Inno Setup 6.3 or newer to compile the Windows setup installer
- Microsoft Edge or Google Chrome
- Internet access when installing source-mode Python packages or sending optional ntfy notifications

## Run from source

Double-click `CVAFPI IDENTIFICATION SYSTEM.bat`. It creates `venv`, installs `requirements.txt`, checks the CSV files, starts the Flask application through Waitress, and opens the kiosk browser.

The production WSGI target is `wsgi:app`. To start it manually from the project directory:

```bat
venv\Scripts\waitress-serve.exe --listen=127.0.0.1:5000 --threads=4 --url-scheme=http wsgi:app
```

## Build the executable on Windows 11

This project must be built on Windows to produce the final `.exe` file. PyInstaller
will not create a Windows executable from a Linux environment.

Use the steps below when creating the production kiosk build for distribution or testing.

### 1. Install the required software

Before you build anything, install the following on a Windows 11 machine:

- Python 3.11 or newer, 64-bit, from <https://www.python.org/downloads/windows/>
- Inno Setup 6.3 or newer to produce the final setup executable
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

1. Creates a Windows Python 3.11+ 64-bit virtual environment named `.venv-windows`
2. Installs the Windows build/runtime dependencies from `requirements-windows.txt`
3. Runs PyInstaller using `ID-BIO-Project.spec` and embeds the CVAFPI app icon
4. Produces the executable in `dist\CVAFPI-IDSYS.exe` as an intermediate build artifact
5. Stages a clean portable release in `dist\portable` with header-only CSV seeds, README, icon, and license notices (never workstation records or settings)
6. Compiles `installer.iss` into `installer\CVAFPI-IDSYS-Setup.exe`

Inno Setup 6.3 or newer is required. The script reports an error if it cannot
produce the setup installer; the clean portable release is still available in
`dist\portable` for troubleshooting or separate use.

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
dist\portable\CVAFPI-IDSYS.exe
```

If the build is successful, you should also see a `dist` folder with the supporting runtime files.

### 5. Verify the output folder

After the build completes, the output should look like this:

```text
dist/
  portable/
    CVAFPI-IDSYS.exe
    data.csv
    backup-data.csv
    README.md
    LICENSE
    CVAIDSYSLOGO.ico
    LICENSES/
installer/
  CVAFPI-IDSYS-Setup.exe
```

Distribute only `dist\portable` or the setup executable; the root `dist` directory may contain local build artifacts and is not a release folder. The portable executable needs its two CSV seed files beside it. The setup installer displays the combined project and third-party licenses during setup, installs per-user, creates a Start Menu entry, and offers an optional desktop shortcut. It also installs the individual license notices and credits. Packaged builds copy their CSV seeds to `%LOCALAPPDATA%\CVAFPI-IDSYS` on first launch and leave existing files untouched during upgrades and uninstall. Settings are created in the writable data folder as needed and are never included in the portable release or installer.

To compile the setup manually, install Inno Setup 6.3 or newer, run `build-windows.bat` once, then run `"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss` from the project directory (adjust the path if installed elsewhere).

### 6. Run the compiled application

You can start the built app in one of these ways:

#### Option A: from the project folder

```bat
run-windows.bat
```

#### Option B: run the built executable directly

```bat
dist\portable\CVAFPI-IDSYS.exe
```

#### Option C: install with the setup program

Run `installer\CVAFPI-IDSYS-Setup.exe` and launch the app from the Start Menu. The installer is per-user and does not require administrator privileges. The app copies its seed CSV files into `%LOCALAPPDATA%\CVAFPI-IDSYS` on first run; settings are generated there when needed. User data is not overwritten by app upgrades or uninstall. The Start Menu also includes documentation and license links.

The barcode library is bundled with the app. Internet access is only needed for optional ntfy notifications.

### 7. Rebuild after code changes

Whenever you update the Python code, run the build again:

```bat
build-windows.bat
```

This rebuilds the app from scratch and refreshes the clean release in `dist\portable`.

Keep the portable seed files header-only. Import the school roster after installation rather than placing student records or workstation settings in a release build.

### Common build problems

- **`py` is not recognized:** reinstall Python and enable the Python launcher, or create the virtual environment manually with:

  ```bat
  python -m venv .venv-windows
  ```

- **The browser does not open:** install Microsoft Edge or Google Chrome.
- **The setup program was not created:** install Inno Setup 6.3 or newer, then rerun `build-windows.bat`. The script returns an error if setup compilation was skipped or failed.
- **The port is busy:** close another instance of the app or stop the process using port `5000`.
- **Student records are missing:** import the school roster in Student Manager or CSV Migration. The packaged seed files intentionally contain only column headers; installed data is stored in `%LOCALAPPDATA%\CVAFPI-IDSYS`.
- **The build stops unexpectedly:** make sure the project folder is not nested inside a protected folder such as OneDrive or a system-managed directory.

### Required output layout

For the portable build, keep these seed files beside the executable. Installed builds copy them into the writable user-data folder on first launch:

```text
dist\portable\
  CVAFPI-IDSYS.exe
  data.csv
  backup-data.csv
```

These header-only seed files let the application initialize its writable student records without requiring write access to its installation folder. Runtime settings, attendance records, audit history, and snapshots are created under `%LOCALAPPDATA%\CVAFPI-IDSYS` for installed builds.

## CSV features

- Add, edit, delete, preview, merge, and replace student records.
- Keep `data.csv` and `backup-data.csv` synchronized.
- Record daily attendance in `CVA_Database\logs_YYYY-MM-DD\logs_YYYY-MM-DD.csv`.
- Save scanner snapshots beside the daily attendance CSV.
- Automatically remove attendance folders older than seven days; audit history is retained separately.
- Export attendance logs from the logs manager.
- Protect student changes, CSV imports, settings, and system controls with an administrator passcode.
- Review scan, security, settings, student, import, and system events in the passcode-protected audit manager (`audit.csv`).
- Optionally send attendance notifications to each student's configured ntfy topic.
- Use configurable system-control barcodes to navigate the kiosk or request an administrator-authorized system action.

Set the administrator passcode and recovery question/answer in System Settings before using protected management functions. Passcodes and recovery answers are stored as salted PBKDF2 hashes in `settings.json`; the recovery answer is case-insensitive. Keep the recovery answer private. Audit events are stored separately from attendance logs and are not removed by the seven-day attendance cleanup.

Required student CSV columns:

```text
BARCODE,NAME,GRADE,SECTION,ACCESS,COLOR,NTFY_TOPIC
```

## Project structure

```text
app.py                       Flask routes, kiosk UI, and app version
logger.py                    CSV persistence, attendance logging, and backups
wsgi.py                      Production WSGI export
windows_launcher.py          Waitress and kiosk browser launcher
static/JsBarcode.all.min.js  Bundled barcode rendering library
CVAIDSYSLOGO.ico             Application and installer icon
ID-BIO-Project.spec          PyInstaller build configuration
build-windows.bat            Windows executable build script
installer.iss                Inno Setup installer definition
LICENSES/                    Third-party license notices and credits
templates/audit-manager.html Protected audit-event browser
run-windows.bat              Windows launcher for the compiled app
CVAFPI IDENTIFICATION SYSTEM.bat  Source-mode launcher
requirements.txt             Source-mode runtime dependencies
requirements-windows.txt     Windows build and runtime dependencies
LICENSE                      Project license
README.md                    Project documentation
data.csv                     Local primary student records (not shipped with source)
backup-data.csv              Local backup student records (not shipped with source)
CVA_Database/                Local attendance logs and snapshot folders
audit.csv                    Local security and administration event history
logs/                        Generated runtime logs
templates/                   Flask HTML templates
static/                     Frontend CSS, JS, and assets
ID-CODES FOR SYSTEM/        Reference control barcode files
```

## Hardware controls

The scanner interface provides controls for returning to the launchpad, exiting kiosk mode, restarting Windows, and shutting down Windows. Keep printed control barcodes secured because they trigger local system actions.

## Data safety

Do not manually edit `data.csv` while the application is running. Use the Student Manager or CSV Migration pages so the primary and backup CSV files stay synchronized.
