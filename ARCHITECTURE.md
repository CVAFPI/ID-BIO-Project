# CSV Edition Architecture

## Runtime

```text
Barcode scanner / kiosk browser
              |
              v
      Flask application
       /           \
      v             v
  CSV logger     JSON settings
      |
      +-- data.csv and backup-data.csv
      +-- dated attendance CSVs and snapshots
      +-- audit.csv
```

The application runs locally on `127.0.0.1`. The Windows launcher starts the
Waitress server, opens the kiosk browser, and keeps application data under
`%LOCALAPPDATA%\CVAFPI-IDSYS` for packaged installs. It seeds the student list
from the installation only when no user copy exists.

## Storage

- `data.csv` is the authoritative student list; `backup-data.csv` is its
  recovery copy. Imports validate the complete file before updating records.
- Attendance rows and optional camera snapshots are stored in dated folders
  under `CVA_Database`.
- `audit.csv` records security, settings, student, scan, and system events.
- `settings.json` stores local preferences and salted passcode/recovery hashes.

The installer is built from `data.example.csv`, which contains only the CSV
header. It never packages the workstation's student records, audit history, or
settings.

## Request and authorization flow

Pages receive a per-run control token. The shared browser helper adds it to
mutating API requests. Administrator-only operations additionally verify the
configured passcode; passcode recovery uses the saved recovery answer.

Student scans are serialized and protected by a short duplicate-scan window.
Successful scans append one row to the daily attendance CSV and return that
row's timestamp to the scanner page.
