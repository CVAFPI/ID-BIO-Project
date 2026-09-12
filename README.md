<img src="https://github.com/CVAFPI/Image-Asset-for-CVAFPI-website/blob/main/CHRISTIAN%20VISON%20ACADEMY%20FONDATION%20PAMPANGA%20INCORPORATION%20(1).png?raw=true" alt="Repository Banner" width="100%">


# 🛡️ CVAFPI Identification System v2.0 — "The Setting Update"

A production-ready Linux kiosk solution and Flask REST API backend engineered for real-time barcode access verification, student attendance logging, badge color customization, automated 7-day privacy cleanup, visual snapshot audits, and remote security push notifications.

Built specifically for educational institutions under **Department of Education (DepEd)** standards.

**Repository:** [github.com/CVAFPI/ID-BIO-Project](https://github.com/CVAFPI/ID-BIO-Project)

**DEBIAN KDE ISO** [Debian KDE download](https://cdimage.debian.org/debian-cd/current-live/amd64/iso-hybrid/debian-live-13.6.0-amd64-kde.iso)

---

## 📋 Table of Contents

- [What's New in v2.0](#-whats-new-in-version-20)
- [Security and Kiosk Controls](#-security-and-kiosk-controls)
- [SQL Branch & Database](#-sql-branch--database)
- [System Requirements](#-system-requirements--hardware-specifications)
- [Hardware Compatibility Guidelines](#️-strict-hardware-compatibility-guidelines)
- [Crucial Warnings](#️-crucial-system-warnings-what-not-to-do)
- [Debian & KDE Plasma Setup](#-debian--kde-plasma-environment-notes)
- [Master Installer](#-master-installer-setup)
- [Passwordless Sudo Configuration](#-configured-passwordless-sudo-required)
- [Deployment Guide](#-step-by-step-deployment-guide)
- [Project Structure](#-project-directory-structure)
- [Hardware Control Barcodes](#️-hardware-control-barcodes)
- [Remote Management](#-remote-management--system-administration)
- [Open Source Commitment](#-100-free--open-source-for-all-schools)
- [Recommended PC Builds](#️-recommended-pc-parts-for-new-builds)
- [Custom Branding & Support](#-custom-branding--free-assistance)

---

## 🚀 What's New in Version 2.0

| Feature | Description |
|---|---|
| **Automated 7-Day Privacy Cleanup** | A built-in startup routine (`cleanup_old_logs`) automatically scans the database directory and permanently purges log folders and webcam snapshots older than one week, ensuring ongoing data privacy compliance. |
| **Visual Snapshot Audit Trail** | Instantly captures a webcam frame upon every successful ID scan, binding visual proof to the timestamped record for review in the logs manager. |
| **Hardware Watchdog & Remote Push Alerts (ntfy.sh)** | Continuously monitors camera status and dispatches high-priority security notifications to mobile or desktop devices if the scanner camera is blocked or fails to initialize. |
| **Local SQLite Database** | Student records and attendance data are stored in `CVA_Database/cva.sqlite3`, giving the single-machine kiosk transactional writes without requiring a separate database server. |
| **GUI CSV Migration Tool** | IT can open **CSV to SQLite** from the launchpad, preview a CSV, and import it without using a terminal or database commands. |
| **PIN-Protected Administration** | Reboot, shutdown, kiosk exit, settings changes, logo uploads, and system barcode commands require a configurable security PIN. |
| **Touch-Friendly Security Dialogs** | In-page modal dialogs replace browser alerts and prompts, preserving kiosk focus and providing masked PIN entry with an on-screen numeric keypad. |

---

## 🗄️ SQL Branch & Database

The `SQL-IDBIOSYS` branch uses a local SQLite database as the system of record. It does not require MySQL, PostgreSQL, or a separate database service.

| Database item | Details |
|---|---|
| **Database file** | `CVA_Database/cva.sqlite3` |
| **Student records** | `students` table, keyed by barcode |
| **Attendance records** | `attendance` table, including timestamp, student details, and snapshot ID |
| **Application settings** | `app_settings` table |
| **Database mode** | SQLite WAL mode with foreign-key enforcement enabled |

### Startup and Migration Behavior

On startup, the application automatically creates the SQLite database and tables when they do not exist. SQLite is the system of record for students, attendance, and application settings. The old root-level student CSV files have been retired; use the **CSV to SQLite** page for an intentional, reviewed import when receiving a new CSV file.

After migration, use the Database Manager or the **CSV to SQLite** page for changes. Do not edit CSV files or the SQLite database while the server is running.

---

## 🔐 Security and Kiosk Controls

Open **System settings** from the launchpad to configure the kiosk security controls:

- Set an initial 4 to 12 digit security PIN.
- Change the PIN only after entering the current PIN.
- Configure a security question and answer for PIN recovery.
- Change the close kiosk, shutdown, and return-to-launchpad barcodes.
- Upload a custom school logo only after PIN authorization.

The PIN is stored as a salted PBKDF2 hash. It is never returned by the settings API or displayed in the interface. If the PIN is forgotten, use **Forgot PIN** in System settings and answer the configured recovery question. A recovery question must be configured during initial setup.

System actions use custom in-page dialogs rather than native browser alerts, confirmations, or prompts. PIN fields are masked by default and include a **Show PIN / Mask PIN** toggle and touchscreen numeric keypad where appropriate. The dialogs keep the kiosk browser focused and inherit the active application theme.

> **Important:** The PIN protects the application actions, but the kiosk account still requires carefully restricted physical and SSH access. Passwordless `sudo` is required for operating-system reboot and shutdown commands; follow the hardening guidance below.

### Backup and Restore

Stop the kiosk before copying the database so its WAL files are included consistently:

```bash
cp CVA_Database/cva.sqlite3 CVA_Database/cva.sqlite3.backup
```

To restore, stop the kiosk, replace `CVA_Database/cva.sqlite3` with a known-good backup, and start the launcher again. Keep the backup in a separate location for protection against disk failure.

---

## 💻 System Requirements & Hardware Specifications

To ensure high-speed barcode processing, stable UI rendering, and continuous 24/7 reliability, your server hardware must meet or exceed the following specifications:

| Hardware Component | Minimum Requirement | Recommended for 24/7 Deployment |
|---|---|---|
| **System Architecture** | 64-bit only (x86_64 / amd64 or aarch64) | 64-bit architecture (amd64 or aarch64) |
| **Processor (CPU)** | Intel / AMD 64-bit CPU (post-2010) or aarch64 ARM | Modern Intel Core i3/i5, AMD Ryzen, or Raspberry Pi 4/5 (64-bit OS) |
| **System Memory (RAM)** | 4 GB | 8 GB (ensures smooth KDE Plasma & browser rendering) |
| **Storage Capacity** | 64 GB SSD / storage | 2 TB SSD/HDD (recommended for multi-year logs and daily visual snapshots) |
| **Network Interface** | 100 Mbps hardwired Ethernet | Gigabit Ethernet (RJ45 cable connected) |
| **Operating System** | Debian 13 (Trixie) 64-bit | Debian 13 (Trixie) 64-bit + KDE Plasma Desktop |
| **Barcode Scanner** | USB / Serial HID barcode scanner | USB handheld or hands-free omnidirectional barcode scanner |

---

## ⚠️ Strict Hardware Compatibility Guidelines

- **64-bit architecture only** — Legacy 32-bit (i386 / x86_32) processors and operating systems are strictly unsupported. Python 3 virtual environments and modern Chromium browser engines require full 64-bit architecture.
- **Obsolete CPU restriction** — Do **not** deploy on outdated x86 processors manufactured prior to 2009 (e.g., legacy Intel Pentium 4, Intel Atom N-series, or early AMD Sempron/Athlon 64 chips).
- **Standard chipset suppliers** — Use standard Intel or AMD 64-bit x86 processors, or standard ARM64 (aarch64) single-board computers such as a Raspberry Pi 4/5 running a 64-bit OS. Avoid obscure, unbranded x86 clones lacking stable Linux kernel driver support.
- **Storage allocation for 24/7 logging** — While basic setups run on 64 GB, a 2 TB drive is strongly recommended for schools running the kiosk continuously (24/7/365), to store the local SQLite database, attendance archives, daily snapshot image folders, and system updates.

---

## ⚠️ Crucial System Warnings: What NOT To Do

> **Do not manually edit `CVA_Database/cva.sqlite3` while the server is running.**
> Use the built-in Database Manager web interface so student changes are validated and written transactionally.

> On the first startup after this migration, the application imports existing records from `data.csv` (or `backup-data.csv`) and existing daily attendance CSV files into SQLite. The CSV files are retained as a one-time migration source and are no longer updated.

> **Do not copy the `venv/` folder across different computers.**
> Python virtual environments are architecture- and path-specific. The master installer script automatically builds a fresh environment on each machine.

> **Do not expose your NTFY notification tokens.**
> Keep secret strings completely private to protect student data and secure parent/office alert channels.

> **Do not use wireless connections for server hardware.**
> Yes WIFI will work aslong is stable but for 24/7 or long use of this software use ETHERNET (wired) to ensure NTFY works and clocks are synced always

---

## 🐧 Debian & KDE Plasma Environment Notes

Standard clean installations of Debian (such as Netinst or minimal server ISOs) do **not** include a graphical desktop environment by default.

Select **KDE Plasma** during the Debian installation task selector, or install it post-installation with:

```bash
sudo apt update && sudo apt install -y task-kde-desktop
```

KDE Plasma is strongly recommended for its display scaling support, reliable power-state handling, and smooth kiosk window management out of the box.

---

## ⚡ Master Installer Setup

The core master script (`CVAFPI IDENTIFICATION SYSTEM.sh`) automates environment preparation:

- Performs system package updates (`apt update` and upgrades)
- Provisions and configures an isolated Python virtual environment (`venv`)
- Installs runtime dependencies (Chromium, unclutter, Flask modules)
- Handles repository updates and interactive prompts seamlessly

### Migrating a CSV Without the Terminal

1. Start the system from the desktop shortcut or configured startup entry.
2. Select **CSV to SQLite** on the launchpad.
3. Choose the existing student CSV and select **Preview CSV**.
4. Review the valid rows, new records, and updates.
5. Select **Import into SQLite**.

The default mode merges records by barcode. Use **Replace all current student records** only when the selected CSV is the complete master list. The original CSV is never deleted or modified.

---

## 🔑 Configured Passwordless Sudo (Required)

Because scanner command barcodes trigger hardware actions (such as emergency shutdowns) and background scripts require root privileges without human interaction, passwordless sudo must be configured for your kiosk user.

1. **Open the sudoers configuration file safely:**
   ```bash
   sudo visudo
   ```

2. **Scroll to the bottom of the file and append the following line** (replace `your-username` with your actual Debian login username):
   ```
   your-username ALL=(ALL) NOPASSWD: ALL
   ```

3. **Save and exit:** `Ctrl + O`, `Enter`, then `Ctrl + X`

> **🔒 Security note:** Passwordless sudo grants full root access to this account with no further prompts. Restrict physical and network (SSH) access to the kiosk accordingly, and never reuse this account's credentials elsewhere.

---

## 📥 Step-by-Step Deployment Guide

Copy and execute these commands in sequence to install and deploy the system:

1. **Install Git**
   ```bash
   sudo apt update && sudo apt install -y git
   ```

2. **Clone the repository**
   ```bash
   git clone https://github.com/CVAFPI/ID-BIO-Project.git
   ```

3. **Navigate to the project directory**
   ```bash
   cd ID-BIO-Project
   ```

4. **Grant execution permissions**
   ```bash
   chmod +x "CVAFPI IDENTIFICATION SYSTEM.sh" Startup
   ```

5. **Run the master installer & kiosk launcher**
   ```bash
   ./"CVAFPI IDENTIFICATION SYSTEM.sh"
   ```

---

## 📂 Project Directory Structure

```
ID-BIO-Project/
├── CVA_Database/                     # SQLite database, daily logs, and snapshots (logs auto-purged after 7 days)
├── ID-CODES FOR SYSTEM/              # Reference command barcodes for admin control
├── logs/                             # Real-time daily scan auxiliary paths
├── venv/                             # Python virtual environment (architecture-specific)
├── static/                           # Image assets (school logo & OS logos)
├── app.py                            # Core Flask REST API backend server
├── logger.py                         # Internal log processing & 7-day privacy cleanup utility
├── CVAFPI IDENTIFICATION SYSTEM.sh   # Master kiosk auto-launcher script
├── id_bio.desktop                    # KDE desktop shortcut entry
├── Startup                           # Autostart boot script trigger
├── CVA_Database/cva.sqlite3          # Local SQLite student, attendance, and settings database
├── jsbarcode.js                      # Offline JavaScript barcode SVG rendering engine
├── static/kiosk-dialog.css           # Theme-aware in-page security dialog styles
├── static/kiosk-dialog.js            # Alert, confirmation, PIN prompt, and keypad behavior
├── launchpad.html                    # Main dashboard launcher interface
├── scanner.html                      # Live attendance registry scanner interface
├── manager.html                      # Database manager interface
├── logs-manager.html                 # Log manager & visual snapshot viewer interface
├── README.md                         # Instructions and specifications
├── LICENSE                           # it's the official MIT open source license of CVAIDSYS
└── server.log                        # Auto-generated Flask server log
```

---

## 🖨️ Hardware Control Barcodes

Scanning any configured system barcode with a physical scanner starts the command flow, but system-level operations require the configured security PIN. The three values can be changed from **System settings**; the values below are only the initial defaults.

> **⚠️ Keep printed copies of these barcodes secured. A security PIN is still required, and the barcodes should be changed if they become known.**

| Action | Command Barcode | Description |
|---|---|---|
| **Close Kiosk Session** | Initial default: `CD=CLOSEBARCODESYS96%&@CVAFPI` | Terminates the active kiosk session after PIN verification |
| **OS Emergency Shutdown** | Initial default: `CD=EMERSHUTDOWNSYSSU62#9CVAFPI` | Executes an immediate system power-down after PIN verification |
| **Return to Main Menu** | Initial default: `CD=RETURNTOMNSYS8(*CVAFPI` | Redirects to `launchpad.html` after PIN verification |

---

## 🚀 Remote Management & System Administration

### Setting Up SSH Access

To manage the kiosk remotely over the network without plugging in a dedicated monitor:

1. **Install and enable the SSH service:**
   ```bash
   sudo apt update && sudo apt install -y openssh-server
   sudo systemctl enable --now ssh
   ```

2. **Connect securely from any workstation on the network:**
   ```bash
   ssh your-username@your-kiosk-ip-address
   ```

### Configuring Auto-Start on Boot (KDE Plasma)

To ensure the system boots straight into the attendance kiosk interface automatically after reboot:

**GUI method:**
Open **System Settings → Autostart → Add... → Add Application or Script...** and select `id_bio.desktop`.

**Terminal method:**
```bash
mkdir -p ~/.config/autostart
cp id_bio.desktop ~/.config/autostart/
```

---

## 🤝 100% Free & Open Source for ALL Schools

This software is built to empower educational institutions without costly licensing fees or SaaS subscriptions.

- **Zero licensing fees** — Download, deploy, and scale across unlimited machines for free.
- **100% local data privacy** — All attendance logs and snapshot images stay strictly on local school hardware, safeguarded by automated 7-day purging routines. No external cloud harvesting.
- **Runs on existing hardware** — Designed lean for Debian 13, enabling older school desktop PCs to be repurposed as hardware kiosks.

---

## 🛠️ Recommended PC Parts for New Builds

### Variant 1: Modern Value Platforms (DDR4) — Best Choice for New Hardware

| Component | AMD Platform (AM4) | Intel Platform (LGA 1200) |
|---|---|---|
| **CPU** | AMD Ryzen 5 4600G or Ryzen 3 3200G | Intel Core i3-10100 or i3-10105 |
| **Motherboard** | MSI A520M-A Pro or Gigabyte A520M S2H | MSI H510M-A Pro or Gigabyte H510M H |
| **RAM** | 8GB (1x8GB) DDR4 3200MHz | 8GB (1x8GB) DDR4 2666MHz/3200MHz |
| **Storage** | 256GB / 512GB 2.5" SATA SSD (+ optional 2TB HDD) | 256GB / 512GB 2.5" SATA SSD (+ optional 2TB HDD) |
| **Case & PSU** | Micro-ATX case with bundled 450W PSU | Micro-ATX case with bundled 450W PSU |

### Variant 2: Ultra-Budget / Legacy Platforms (DDR3 / Early DDR4)

| Component | AMD Platform (AM4 Entry) | Intel Platform (LGA 1150 Legacy) |
|---|---|---|
| **CPU** | AMD Athlon 3000G or Athlon 200GE | Intel Core i5-4570 or i5-4460 |
| **Motherboard** | Biostar A320MH or ASUS Prime A320M-K | H81M motherboard (ASUS / Gigabyte / Biostar) |
| **RAM** | 8GB (1x8GB) DDR4 2400MHz/2666MHz | 8GB (2x4GB or 1x8GB) DDR3 1600MHz |
| **Storage** | 240GB 2.5" SATA SSD | 240GB 2.5" SATA SSD |
| **Case & PSU** | Basic Micro-ATX office case with 450W PSU | Basic Micro-ATX office case with 450W PSU |

---

## 🎨 Custom Branding & Free Assistance

Free setup assistance and customization are available if you need help modifying the interface for your school:

- **Customization offered:** Official school logo/seal replacement, header text updates, custom accent color matching, and grade/section schema modifications.
- **Email assistance:** [allthingslinux2026@gmail.com](mailto:allthingslinux2026@gmail.com) — please attach your school logo (PNG/JPEG) and requested modifications.
- **GitHub Issues:** Open a ticket directly on the [GitHub Issues page](https://github.com/CVAFPI/ID-BIO-Project/issues).

(Note) In future update there will be a fork for schools for easy customizability, easy uploads and many more
---

<p align="center">
Made with ❤️ for schools everywhere — 100% free, 100% open source.
</p>
