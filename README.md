# 🛡️ CVAFPI IDENTIFICATION SYSTEM v1.2 Alpha

A dedicated Linux kiosk solution and Flask REST API backend engineered for real-time barcode access verification, student attendance logging, badge color customization, and database management.

---

> ⚠️ **IMPORTANT OS SYSTEM REQUIREMENT**
> **RUN ON DEBIAN 13 OS!** *(KDE Plasma Desktop recommended for best performance, display scaling, and user-friendly kiosk management).*

---

## 📂 Project Directory Structure

Based on the official `ID Bio HTML Project` repository:

```text
ID Bio HTML Project/
├── CVA-Database/                    # Backup storage and record archives
├── ID-CODES FOR SYSTEM/             # Reference command barcodes for admin control
├── logs/                            # Real-time daily scan CSV logs (logs_YYYY-MM-DD.csv)
├── venv/                            # Python Virtual Environment (Architecture-specific)
├── app.py                           # Core Flask REST API backend server
├── logger.py                        # Internal log processing and helper utility
├── CVAFPI IDENTIFICATION SYSTEM.sh  # Master Kiosk auto-launcher script
├── id_bio.desktop                   # KDE Desktop shortcut entry
├── Startup                          # Autostart boot script trigger
├── data.csv                         # Primary user database file (Barcode, Name, Grade, Section, Access, Color)
├── jsbarcode.js                     # Offline JavaScript barcode SVG rendering engine
├── launchpad.html                   # Main dashboard launcher interface
├── scanner.html                     # Live Attendance Registry Scanner interface
├── manager.html                     # Database Manager interface
├── logs-manager.html                # Log Manager & Attendance viewer interface
├── CVAFPI-LOGO.png                  # Primary CVA institution logo asset
├── Deped - Logo.png                 # DepEd official logo asset
├── README.txt                       # Legacy text notes
└── server.log                       # Auto-generated Flask server log

```

---

## 🖨️ Hardware Control Barcodes

Scanning any of these barcodes with a physical scanner triggers instant hardware actions:

* **`CD=CLOSEBARCODESYS96%&@CVAFPI`** — Force-closes the Chromium kiosk session.
* **`CD=EMERSHUTDOWNSYSSU62#9CVAFPI`** — Triggers immediate Linux OS hardware shutdown (`sudo shutdown now`).
* **`CD=RETURNTOMNSYS8(*CVAFPI`** — Exits active module and redirects to `launchpad.html`.

---

## ⚙️ Setup & Installation (Debian 13 KDE)

### 1. System Dependencies Installation

Open a terminal on Debian 13 and install the required packages:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip chromium xset curl lsof unclutter

```

### 2. Configure Python Virtual Environment

Navigate to the project folder and build the virtual environment:

```bash
cd ~/"Projects/ID Bio HTML Project"

# Remove existing venv if migrating across different computers/architectures
rm -rf venv

# Create new clean venv
python3 -m venv venv
source venv/bin/activate
pip install flask

```

### 3. Grant Script Execution Permissions

Grants the app launcher permissions to open:

```bash
chmod +x "CVAFPI IDENTIFICATION SYSTEM.sh"
chmod +x Startup

```

### 4. Launch Kiosk

Run the launcher script directly from the terminal:

```bash
./"CVAFPI IDENTIFICATION SYSTEM.sh"

```

---

## 🚀 Setting Up Auto-Start on Boot (KDE Plasma)

To automatically launch the system in full Kiosk mode when Debian 13 boots:

### Method A: Using KDE Autostart Settings (Recommended)

1. Open **System Settings** in KDE.
2. Navigate to **Autostart** (under Workspace).
3. Click **Add...** -> **Add Application or Script...**
4. Select the `id_bio.desktop` file located in the project folder.

### Method B: Terminal Copy

Copy the desktop shortcut into your KDE autostart directory:

```bash
mkdir -p ~/.config/autostart
cp ~/"Projects/ID Bio HTML Project/id_bio.desktop" ~/.config/autostart/

```

---

## ⚠️ Important Deployment & Architecture Warnings

1. **Virtual Environment Isolation:** Never copy the `venv/` folder when moving this project between different hardware (e.g., x86 PC to Raspberry Pi). Always delete `venv/` and re-run `python3 -m venv venv` on the target device.
2. **Offline Rendering:** `jsbarcode.js` is bundled locally inside the project folder so the barcode display on `scanner.html` works completely offline without internet connectivity.
3. **Data Loss Safety:** Scan logs are directly flushed to `data.csv` and `logs/logs_YYYY-MM-DD.csv` upon scan. Sudden power loss will not lose past scanned records.
