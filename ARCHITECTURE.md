# Architecture

## Overview

ID Bio System is a local kiosk web application. Flask renders the browser
interface and exposes the JSON APIs; SQLite is the system of record. The
browser and server communicate over HTTP on the local machine. The barcode
renderer and other frontend assets are served locally from `static/`.

```text
┌─────────────────────┐       HTTP        ┌──────────────────────────┐
│ Kiosk browser       │ ────────────────> │ Gunicorn                 │
│ templates + static/ │ <──────────────── │ Flask application (app.py)│
└─────────────────────┘                   └────────────┬─────────────┘
                                                       │
                                    ┌──────────────────┴──────────────┐
                                    │                                 │
                             ┌──────▼───────┐                 ┌───────▼────────┐
                             │ logger.py    │                 │ Local files    │
                             │ SQLite/WAL   │                 │ snapshots/logs │
                             └──────────────┘                 └────────────────┘
```

## Components

- **`app.py`** creates the Flask application, renders pages in `templates/`,
  serves `static/`, and defines the settings, student, scan, migration, audit,
  logs, branding, and system-action endpoints.
- **`logger.py`** owns SQLite connections and the data operations for students,
  attendance, application settings, and audit events. It enables WAL and
  foreign-key enforcement, initializes the schema, maintains the database
  backup, and handles CSV import and log cleanup.
- **`templates/`** contains the launchpad, scanner, database manager, migration,
  logs manager, and audit manager pages.
- **`static/`** contains the JsBarcode renderer, CSS, browser-side scripts, and
  image assets. These are served by Flask under `/static/`.
- **`wsgi.py`** exports the Flask application for the production WSGI server.
  The kiosk launchers run Gunicorn with `app:app`.
- **`build-deb.sh` and `packaging/deb/`** assemble the Debian package with its
  control metadata, desktop entry, and executable launcher.

## Request and data flow

1. The kiosk browser loads a page from Flask and downloads its local CSS,
   JavaScript, and image assets from `/static/`.
2. The scanner submits barcode scans and page actions to Flask API endpoints.
3. Flask validates requests and authorization, then calls `logger.py` for
   persistent student, attendance, setting, or audit operations.
4. `logger.py` opens SQLite connections in WAL mode. Attendance snapshots and
   other filesystem data are kept alongside the database in the configured
   data directory.
5. Flask returns rendered HTML, JSON results, or requested log snapshots to the
   browser.

## Runtime and data locations

### Repository launcher

`CVAFPI IDENTIFICATION SYSTEM.sh` starts the app from the repository, prepares
its Python virtual environment, initializes the database, and launches Gunicorn
for the kiosk browser. By default, `CVAFPI_DATA_DIR` is unset, so the app stores
its database and related data under the repository directory.

### Debian package

The `.deb` installs application resources under `/usr/share/idbiosys` and the
launcher at `/usr/bin/idbiosys-kiosk`. At launch, the script copies packaged
resources into the current user's data area and sets `CVAFPI_DATA_DIR` to
`${XDG_DATA_HOME:-~/.local/share}/idbiosys`. The application then uses:

```text
~/.local/share/idbiosys/
├── CVA_Database/
│   ├── cva.sqlite3
│   └── cva.sqlite3.backup
├── logs/
├── static/
└── app/                 # Runtime copy of templates, static assets, and Python files
```

The user data directory is separate from the system-installed package files,
so database records and uploaded branding are not stored in the package
installation tree.

## Database and recovery

SQLite stores students, attendance, app settings, audit events, and recent scan
state in `CVA_Database/cva.sqlite3`. Connections enable WAL mode, a busy
timeout, and foreign-key enforcement. The logger refreshes a SQLite backup
after successful writes and attempts to recover from that backup if startup
cannot open the primary database. The application also performs its configured
cleanup of old logs and snapshots.

For manual backups or restores, stop the application first and preserve the
SQLite database and its associated WAL files consistently. See the backup and
restore instructions in the README.
