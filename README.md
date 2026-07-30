# 🛡️ CVAFPI Identification System (v1.2 Beta)
A dedicated Linux kiosk solution and Flask REST API backend engineered for real-time barcode access verification, student attendance logging, badge color customization, and seamless database management. Designed specifically for schools with easy, automated installation routines.
Repository: https://github.com/CVAFPI/ID-BIO-Project
## ⚠️ Crucial System Warnings & Prerequisites
Before setting up, keep these important points in mind:
 * **Debian Desktop Requirement:** Standard minimal or netinstall Debian images do **not** come with KDE Plasma pre-installed. Make sure your Debian system has a desktop environment (specifically KDE Plasma) installed so the kiosk display and scaling work correctly.
 * **DO NOT manually edit data.csv while the server is running:** Doing so can cause file locking or data corruption if a scan happens at the exact same millisecond. Use the built-in Database Manager interface instead.
 * **DO NOT copy the venv/ folder across different computers:** Python virtual environments are architecture-specific. The automated script handles this for you.
 * **DO NOT share your NTFY notification string:** The secret letters/numbers generated for parent alerts must remain private to protect student and parent security.
 * **DO NOT panic at terminal commands:** If you're new to Linux, commands might look intimidating, but everything you need is fully automated or explained below!
## 📂 Project Directory Structure
```text
ID-BIO-Project/
├── CVA-Database/                      # Backup storage and record archives
├── ID-CODES FOR SYSTEM/               # Reference command barcodes for admin control
├── logs/                              # Real-time daily scan CSV logs (logs_YYYY-MM-DD.csv)
├── venv/                              # Python Virtual Environment (Auto-generated)
├── app.py                             # Core Flask REST API backend server
├── logger.py                          # Internal log processing and helper utility
├── CVAFPI IDENTIFICATION SYSTEM.sh    # Master Kiosk auto-installer and launcher script
├── id_bio.desktop                     # KDE Desktop shortcut entry
├── Startup                            # Autostart boot script trigger
├── data.csv                           # Primary user database file (Barcode, Name, Grade, Section, Access, Color, NTFY_TOPIC)
├── jsbarcode.js                       # Offline JavaScript barcode SVG rendering engine
├── launchpad.html                     # Main dashboard launcher interface
├── scanner.html                       # Live Attendance Registry Scanner interface
├── manager.html                       # Database Manager interface
├── logs-manager.html                  # Log Manager & Attendance viewer interface
├── CVAFPI-LOGO.png                    # Primary CVA institution logo asset
├── Deped - Logo.png                   # DepEd official logo asset
├── README.txt                         # Legacy text notes
└── server.log                         # Auto-generated Flask server log

```
## 🖨️ Hardware Control Barcodes
Scanning any of the following reference barcodes using a physical scanner immediately triggers system-level commands:
 * **Close Kiosk Session:** CD=CLOSEBARCODESYS96%&@CVAFPI
 * **OS Emergency Shutdown:** CD=EMERSHUTDOWNSYSSU62#9CVAFPI *(Executes sudo shutdown now)*
 * **Return to Main Menu:** CD=RETURNTOMNSYS8(*CVAFPI *(Exits active module and loads launchpad.html)*
## 📖 Beginner's Guide: Understanding Terminal Commands
If you are completely new to Linux, here is what the commands mean so you never have to feel paranoid about typing them:
 * **git clone**: Downloads a copy of the project repository from GitHub directly onto your computer.
 * **cd (Change Directory)**: Short for **Change Directory**. Think of it like double-clicking a folder on your desktop to step inside it.
 * **chmod (Change Mode)**: Short for **Change Mode**. By default, Linux treats downloaded text scripts as plain documents for safety. chmod +x tells the operating system: *"Hey, this file is safe; give it permission to run as a program."*
 * **sudo (Superuser Do)**: Temporarily grants administrative privileges so your system can install required software packages and updates.
## 📥 Step 1: Download the Project (Git Clone)
Open your terminal and clone the repository to your system workspace:
```bash
# Download the project from GitHub
git clone https://github.com/CVAFPI/ID-BIO-Project.git

# Step inside the downloaded folder using 'cd'
cd "ID-BIO-Project"

```
## ⚙️ Step 2: Automated Installation & Setup
Good news for school deployment: **You do not need to manually install dependencies or build virtual environments!**
The master script (CVAFPI IDENTIFICATION SYSTEM.sh) features a built-in auto-installer. It will check for updates, handle sudo apt update and upgrade, build the Python virtual environment (venv), and set everything up automatically. All you have to do is make the script executable and run it:
### 1. Grant Script Execution Permissions (chmod)
Tell Linux that the master script and startup triggers are allowed to run:
```bash
chmod +x "CVAFPI IDENTIFICATION SYSTEM.sh"
chmod +x Startup

```
### 2. Run the Master Script
Execute the launcher. The script will guide you (such as asking if you want to update) and take care of the rest:
```bash
./"CVAFPI IDENTIFICATION SYSTEM.sh"

```
## 🚀 Step 3: Setting Up Auto-Start on Boot (KDE Plasma)
To have the system automatically boot straight into full Kiosk mode:
### Method A: Using KDE Autostart Settings (Recommended)
 1. Open **System Settings** in KDE Plasma.
 2. Navigate to **Autostart** (located under *Workspace*).
 3. Click **Add...** and select **Add Application or Script...**
 4. Choose the id_bio.desktop file located inside your project folder.
### Method B: Terminal Shortcut Deployment
Alternatively, copy the desktop entry straight into your local autostart directory:
```bash
mkdir -p ~/.config/autostart
cp id_bio.desktop ~/.config/autostart/

```
## ⚠️ Important Deployment & Architecture Warnings
 * **Offline Rendering:** jsbarcode.js is bundled locally within the repository, ensuring barcode rendering on scanner.html operates entirely offline without an active internet connection.
 * **Data Loss Safety:** Attendance scan logs are immediately flushed to data.csv and daily files within logs/ at the moment of scanning. Unexpected power failures will not cause historical scan logs to be lost.
 * **Parental Notification Alerts:** Real-time push notifications utilize the **NTFY** mobile app (available on the Google Play Store and Apple App Store). Using the built-in random topic generator in the Database Manager and clicking save activates notifications instantly.
   > 🔒 **Security Notice:** For privacy and safety guidelines, never share your secret string of letters and numbers to safeguard both the child and parent.
   > 
