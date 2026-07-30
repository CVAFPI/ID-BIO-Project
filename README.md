# 🛡️ CVAFPI IDENTIFICATION SYSTEM v1.2 BETA
A dedicated, production-ready Linux kiosk solution and Flask REST API backend engineered for real-time barcode access verification, student attendance logging, badge color customization, and seamless database management. Built specifically for educational institutions under Department of Education (DepEd) standards.
Repository: https://github.com/CVAFPI/ID-BIO-Project
## ⚠️ Crucial System Warnings: What NOT To Do
Before deploying this system, keep these strict operational guidelines in mind to prevent data corruption, hardware locks, or security flaws:
 * **DO NOT manually edit data.csv while the server is actively running:** Doing so risks file-locking conflicts or data corruption if a student scans a barcode at the exact same millisecond. Always use the built-in Database Manager web interface.
 * **DO NOT copy the venv/ folder across different computers:** Python virtual environments are architecture- and path-specific. The master installer script automatically handles building a fresh, clean environment for you.
 * **DO NOT expose your NTFY notification tokens:** The secret string generated for real-time parent mobile alerts must remain completely private to protect student privacy and ensure safe communication channels.
 * **DO NOT rely on wireless connections for server hardware:** As a fundamental networking rule, always use a hardwired **Ethernet cable** rather than Wi-Fi for server kiosks to guarantee rock-solid stability and zero dropped attendance packets.
## 🐧 Note on Debian & KDE Plasma Environment
Standard clean installations of Debian (especially Netinst or minimal server ISO images) **do not come with a graphical desktop environment or KDE Plasma pre-installed**.
 * If you are setting this up on a fresh machine, ensure you select **KDE Plasma** during the Debian installation task selector, or install it post-install using sudo apt install task-kde-desktop.
 * KDE Plasma is strongly recommended because it offers superior display scaling, reliable power-state handling, and smooth kiosk window management out of the box.
## ⚡ The Master Script Advantage (Zero-Fuss Installation)
We designed the installation process so that school administrators and technicians—even those completely new to Linux—don't have to manually execute a dozen complex commands.
The core master script (CVAFPI IDENTIFICATION SYSTEM.sh) handles the heavy lifting automatically:
 1. It checks and performs system package updates (sudo apt update and upgrades).
 2. It provisions and configures the Python virtual environment (venv).
 3. It installs all required Flask and system dependencies (chromium, unclutter, etc.).
 4. It interactively prompts you if you want to update the repository or components and handles the rest seamlessly.
All you have to do is clone the repository and run the script!
## 🔑 Setting Up Passwordless Sudo (Required for Kiosk Automation)
Because this system runs as an automated kiosk where physical scanner barcodes can trigger hardware actions (such as system shutdowns via CD=EMERSHUTDOWNSYSSU62#9CVAFPI) and background scripts require root privileges to update packages without human intervention, you must configure **passwordless sudo** for your kiosk user. Without this, the system will freeze or fail when attempting administrative tasks behind the scenes.
### How to Configure Passwordless Sudo:
 1. Open your terminal and edit the sudoers configuration file safely using visudo:
   ```bash
   sudo visudo
   
   ```
 2. Scroll to the bottom of the file and add the following line (replace your-username with your actual Debian login username):
   ```text
   your-username ALL=(ALL) NOPASSWD: ALL
   
   ```
 3. Press Ctrl + O then Enter to save, and Ctrl + X to exit the editor.
## 📥 Step-by-Step Deployment Guide
Follow these simple steps to get your CVAFPI Kiosk up and running from scratch:
### 1. Install Git (If Not Already Installed)
```bash
sudo apt update
sudo apt install -y git

```
### 2. Clone the Repository
Clone the official project directly into your local machine workspace (e.g., inside your home directory or /home/CVAFPI/):
```bash
git clone https://github.com/CVAFPI/ID-BIO-Project.git

```
### 3. Change Directory (cd)
 * **cd** stands for **Change Directory**. Think of it like double-clicking a folder on a graphical desktop to enter it.
```bash
cd ID-BIO-Project

```
### 4. Grant Execution Permissions to the Master Script
 * **chmod** stands for **Change Mode**. By default, Linux treats downloaded text scripts as plain documents for security. chmod +x tells the system: *"This file is safe; grant it permission to execute as a program."*
```bash
chmod +x "CVAFPI IDENTIFICATION SYSTEM.sh"
chmod +x Startup

```
### 5. Run the Master Installer & Kiosk Launcher
Simply execute the master script. It will automatically walk you through environment setup, dependencies, updates, and launch the kiosk:
```bash
./"CVAFPI IDENTIFICATION SYSTEM.sh"

```
## 📂 Project Directory Structure
```text
ID-BIO-Project/
├── CVA-Database/                      # Backup storage and record archives
├── ID-CODES FOR SYSTEM/               # Reference command barcodes for admin control
├── logs/                              # Real-time daily scan CSV logs (logs_YYYY-MM-DD.csv)
├── venv/                              # Python Virtual Environment (Architecture-specific)
├── app.py                             # Core Flask REST API backend server
├── logger.py                          # Internal log processing and helper utility
├── CVAFPI IDENTIFICATION SYSTEM.sh    # Master Kiosk auto-launcher script
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
Scanning any of these reference command barcodes using a physical scanner immediately executes system-level shortcuts:
 * **Close Kiosk Session:** CD=CLOSEBARCODESYS96%&@CVAFPI
 * **OS Emergency Shutdown:** CD=EMERSHUTDOWNSYSSU62#9CVAFPI *(Executes immediate system power-down)*
 * **Return to Main Menu:** CD=RETURNTOMNSYS8(*CVAFPI *(Exits active module and redirects to launchpad.html)*
## 🚀 Helpful Tips & Advanced Administration
### Setting Up SSH for Remote Management
If your kiosk is mounted inside an enclosure or positioned in a hallway, you don't want to plug in a monitor every time you need to manage it. Install and enable SSH for remote terminal administration:
```bash
sudo apt install -y openssh-server
sudo systemctl enable --now ssh

```
You can now securely log in from any computer on the school network using: ssh your-username@your-kiosk-ip-address.
### Configuring Auto-Start on Boot (KDE Plasma)
To ensure the system boots straight into the attendance kiosk interface automatically after a power outage or reboot:
 1. Open **System Settings** in KDE Plasma.
 2. Navigate to **Autostart** (under *Workspace*).
 3. Click **Add...** -> **Add Application or Script...**
 4. Select the id_bio.desktop file located inside your project folder.
Alternatively, deploy via terminal command:
```bash
mkdir -p ~/.config/autostart
cp id_bio.desktop ~/.config/autostart/

```
## 🤝 100% Free & Open Source for ALL Schools!
We passionately believe that **every school deserves modern, secure, and reliable IT tools—regardless of budget.**
Many educational institutions struggle with expensive software licensing fees, monthly SaaS subscriptions, or closed proprietary hardware. This system was built to break those barriers down completely.
### 🌟 Why Your School Can Confidently Use This Project:
 * **Zero Licensing Fees (Forever Free):** Whether you are a public school, private academy, university campus, or local community center, you can download, deploy, and run this system on as many computers as you want without paying a single cent.
 * **100% Local Data Privacy:** All attendance logs and student data stay strictly on your school's hardware inside local .csv files. No external cloud servers are harvesting or selling your students' information.
 * **Runs on Recycled/Existing Hardware:** Designed to run lean on Linux (Debian 13), allowing you to convert older, repurposed school desktop PCs into powerful attendance kiosks instead of buying expensive new equipment.
## 🎨 Want Your School's Logo & Custom Branding? (We'll Do It For You Free!)
Please **do not feel hesitant or shy** to reach out if you aren't familiar with editing HTML or CSS code! We want your kiosk interface to look official and feel like a proud part of your institution.
If you decide to adopt this system for your school, **we will gladly customize the interface for you completely free of charge!**
### What We Can Customize For Your School:
 * Replacing default logos with your **Official School Logo / Seal** and regional DepEd division banners.
 * Updating the header text, school name, and institution mission statement on the kiosk interface.
 * Matching the dashboard accent colors to your official school colors.
 * Adjusting grade level formats, section names, or badge layout fields to fit your campus records.
### 📩 How to Request Free Customization & Assistance:
Don't hesitate—reach out through whichever channel is most comfortable for you:
 1. **Email Us Directly:** Send an email to **allthingslinux2026@gmail.com**
   * *What to attach:* Your school's logo (PNG or JPEG format), your school name, and any specific color or design requests.
 2. **Open a GitHub Issue:** Visit our GitHub Issues Page and click **New Issue**.
   * Title it something simple like: *"Custom Logo Request for [Your School Name]"*.
Whether you need help fixing a setup bug, customizing your design, or figuring out Linux commands, we are here to support your school community every step of the way!
> 💡 **A Note from the Developers:**
> *"This is Lance, together with Google AI assistant Gemini—we will help go one step closer to a brighter IT for you!"*
> 
