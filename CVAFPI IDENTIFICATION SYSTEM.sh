#!/usr/bin/env bash

# ==============================================================================
#                  CVAFPI IDENTIFICATION SYSTEM - KIOSK LAUNCHER v1.5
# ==============================================================================

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

PORT=5000
SERVER_URL="http://127.0.0.1:${PORT}"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${APP_DIR}/venv"
CSV_PATH="${APP_DIR}/data.csv"
BACKUP_PATH="${APP_DIR}/backup-data.csv"
REPO_URL="https://github.com/CVAFPI/ID-BIO-Project.git"

clear
echo -e "${CYAN}"
echo "======================================================================"
echo "                     CVAFPI IDENTIFICATION SYSTEM                     "
echo "                 Kiosk Engine Auto-Launcher (v1.5 Beta)               "
echo "======================================================================"
echo -e "${NC}"

# --- DISPLAY SYSTEM INFO (FASTFETCH / NEOFETCH) ---
if command -v fastfetch &> /dev/null; then
    fastfetch
elif command -v neofetch &> /dev/null; then
    neofetch
fi

echo -e "${GREEN}Welcome to CVAFPI ID SYSTEM v1.5${NC}\n"

cd "$APP_DIR" || { echo -e "${RED}[!] Failed to access directory: $APP_DIR${NC}"; exit 1; }

# --- GITHUB AUTO-UPDATE CHECK (SAFEGUARDED AGAINST CSV & VENV LOSS) ---
echo -e "${CYAN}[*] Checking for updates from GitHub (${REPO_URL})...${NC}"
if command -v git &> /dev/null; then
    if [ ! -d "${APP_DIR}/.git" ]; then
        git init 2>/dev/null
        git remote add origin "$REPO_URL" 2>/dev/null
    else
        git remote set-url origin "$REPO_URL" 2>/dev/null
    fi

    # Fetch latest remote references
    git fetch origin main 2>/dev/null || git fetch origin master 2>/dev/null

    BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null || echo "main")
    LOCAL=$(git rev-parse HEAD 2>/dev/null)
    REMOTE=$(git rev-parse "origin/${BRANCH}" 2>/dev/null || git rev-parse "origin/main" 2>/dev/null)

    if [ "$LOCAL" != "$REMOTE" ] && [ -n "$REMOTE" ]; then
        echo -e "${GREEN}[✓] New update found on GitHub! Safely pulling latest changes...${NC}"

        # Safety backup of data files to /tmp before pulling code updates
        [ -f "$CSV_PATH" ] && cp "$CSV_PATH" "/tmp/data.csv.bak"
        [ -f "$BACKUP_PATH" ] && cp "$BACKUP_PATH" "/tmp/backup-data.csv.bak"

        # Pull code updates without touching untracked files (venv/ and local csv files are untouched)
        git pull origin "$BRANCH" 2>/dev/null || git pull origin main 2>/dev/null

        # Restore local data files just in case they were tracked or affected
        [ -f "/tmp/data.csv.bak" ] && cp "/tmp/data.csv.bak" "$CSV_PATH"
        [ -f "/tmp/backup-data.csv.bak" ] && cp "/tmp/backup-data.csv.bak" "$BACKUP_PATH"

        echo -e "${GREEN}[✓] Application successfully updated! Restarting launcher...${NC}"
        exec bash "$0" "$@"
    else
        echo -e "${GREEN}[✓] Application is already up to date.${NC}"
    fi
else
    echo -e "${YELLOW}[!] Git command missing. Skipping GitHub auto-update check.${NC}"
fi

# --- SYSTEM UPDATE & DEPENDENCY PROMPT ---
echo -e "${CYAN}[0/4] System & Package Check...${NC}"
read -p "Do you want to update the system and install required packages? (y/n): " update_choice
if [[ "$update_choice" =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}[*] Updating system packages...${NC}"
    sudo apt update -y && sudo apt upgrade -y
    echo -e "${YELLOW}[*] Installing required dependencies & system fetch tools...${NC}"
    sudo apt install -y curl lsof unclutter x11-utils python3-pip python3-venv git fastfetch 2>/dev/null || sudo apt install -y neofetch
    echo -e "${GREEN}[✓] System update and package installation complete.${NC}"
else
    echo -e "${YELLOW}[!] Skipping system update. Ensuring minimal tools are present...${NC}"
    sudo apt install -y curl lsof unclutter x11-utils git fastfetch 2>/dev/null || sudo apt install -y neofetch 2>/dev/null || true
fi

cleanup() {
    echo -e "\n${YELLOW}[!] Shutting down CVAFPI Identification System...${NC}"
    if [ -n "$FLASK_PID" ]; then
        kill "$FLASK_PID" 2>/dev/null
    fi
    pkill -f "cva_kiosk_profile" 2>/dev/null
    echo -e "${GREEN}[✓] Shutdown complete.${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# --- STEP 1: CONFIGURE DISPLAY ---
echo -e "${CYAN}[1/4] Configuring display settings...${NC}"
if command -v xset &> /dev/null; then
    xset s off 2>/dev/null
    xset -dpms 2>/dev/null
    xset s noblank 2>/dev/null
    echo -e "${GREEN}[✓] Screen sleep and DPMS disabled.${NC}"
fi

# --- STEP 2: PYTHON VENV & DATABASE SCHEMA CHECK WITH DUAL BACKUP ---
echo -e "${CYAN}[2/4] Initializing Python Backend Environment & Database Integrity Check...${NC}"
if [ -d "$VENV_DIR" ]; then
    source "${VENV_DIR}/bin/activate"
else
    python3 -m venv venv
    source "${VENV_DIR}/bin/activate"
    pip install flask
fi
echo -e "${GREEN}[✓] Virtual environment ready.${NC}"

# --- DUAL .CSV BACKUP SHADOW & SCHEMA VALIDATION ---
NEEDS_FIX=0

if [ ! -f "$CSV_PATH" ]; then
    if [ -f "$BACKUP_PATH" ]; then
        echo -e "${YELLOW}[!] data.csv is missing. Restoring instantly from shadow backup (backup-data.csv)...${NC}"
        cp "$BACKUP_PATH" "$CSV_PATH"
    else
        echo -e "${YELLOW}[!] Both data.csv and backup-data.csv are missing. A fresh baseline will be generated.${NC}"
        NEEDS_FIX=1
    fi
else
    # Check if backup-data.csv is in the same folder; if not, create it with exact prompt requested
    if [ ! -f "$BACKUP_PATH" ]; then
        echo -e "${YELLOW}[!] data.csv has no backup, making backup now!${NC}"
        cp "$CSV_PATH" "$BACKUP_PATH"
    fi

    # Check if headers match the expected schema via Python and verify file health
    HEADER_CHECK=$(python3 -c "
import csv, os
try:
    if os.path.getsize('$CSV_PATH') == 0:
        print('DIFFERENT')
        exit()
    with open('$CSV_PATH', mode='r', encoding='utf-8', errors='ignore') as f:
        reader = csv.reader(f)
        header = next(reader)
        expected = ['BARCODE', 'NAME', 'GRADE', 'SECTION', 'ACCESS', 'COLOR', 'NTFY_TOPIC']
        actual = [h.strip().upper() for h in header[:7]]
        if actual != expected:
            print('DIFFERENT')
        else:
            print('OK')
except Exception:
    print('DIFFERENT')
")
    if [ "$HEADER_CHECK" = "DIFFERENT" ]; then
        NEEDS_FIX=1
    fi
fi

if [ "$NEEDS_FIX" -eq 1 ]; then
    echo -e "${YELLOW}[!] data.csv seems to be different or missing required headers.${NC}"
    echo -e "${YELLOW}[!] Do you like to fix it? (20 seconds before proceeding) y/n:${NC}"

    FIX_CHOICE="y" # Default to auto-fix on timeout
    for i in {20..1}; do
        echo -ne "\r[?] Proceeding in ${i}s [y/N]: "
        read -t 1 -r response
        if [ $? -eq 0 ]; then
            if [[ "$response" =~ ^[Yy]$ ]]; then
                FIX_CHOICE="y"
            elif [[ "$response" =~ ^[Nn]$ ]]; then
                FIX_CHOICE="n"
            fi
            break
        fi
    done
    echo ""

    if [[ "$FIX_CHOICE" =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}[*] Executing Database Recovery & Synchronization...${NC}"
        python3 -c "
import csv, os

file_path = '$CSV_PATH'
backup_path = '$BACKUP_PATH'
rows = []

source_to_read = file_path
if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
    source_to_read = file_path
elif os.path.exists(backup_path) and os.path.getsize(backup_path) > 0:
    source_to_read = backup_path

if os.path.exists(source_to_read):
    try:
        with open(source_to_read, mode='r', encoding='utf-8', errors='ignore') as f:
            reader = list(csv.reader(f))
            if len(reader) > 1:
                header = [h.strip().upper() for h in reader[0]]
                for r in reader[1:]:
                    if not r or not any(r): continue
                    row_dict = {header[i]: r[i] for i in range(min(len(header), len(r)))}
                    barcode = row_dict.get('BARCODE', row_dict.get('ID', ''))
                    name = row_dict.get('NAME', row_dict.get('STUDENT NAME', 'UNKNOWN STUDENT'))
                    if not barcode:
                        continue
                    grade = row_dict.get('GRADE', 'GRADE 12')
                    section = row_dict.get('SECTION', 'ICT-SIMEON')
                    access = row_dict.get('ACCESS', 'REGULAR')
                    color = row_dict.get('COLOR', '#059669')
                    ntfy = row_dict.get('NTFY_TOPIC', 'None')
                    rows.append([barcode, name, grade, section, access, color, ntfy])
    except Exception as e:
        print(f'[!] Error parsing data source: {e}')

for target in [file_path, backup_path]:
    with open(target, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['BARCODE', 'NAME', 'GRADE', 'SECTION', 'ACCESS', 'COLOR', 'NTFY_TOPIC'])
        if rows:
            writer.writerows(rows)

print('${GREEN}[✓] data.csv fixed and dual backup synchronized successfully!${NC}')
"
    else
        echo -e "${RED}[!] Skipping fix. Proceeding with existing data.csv...${NC}"
    fi
else
    echo -e "${GREEN}[✓] data.csv schema is valid and synchronized with backup.${NC}"
fi

# --- STEP 3: START FLASK ---
echo -e "${CYAN}[3/4] Launching CVAFPI Core Server (app.py)...${NC}"
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    echo -e "${YELLOW}[!] Port $PORT is active. Reusing existing instance.${NC}"
else
    python3 app.py > server.log 2>&1 &
    FLASK_PID=$!
    echo -e "${GREEN}[✓] Server process started (PID: $FLASK_PID).${NC}"
    echo -n "Waiting for server to respond on port ${PORT}"
    until curl -s "${SERVER_URL}" > /dev/null; do
        echo -n "."
        sleep 1
    done
    echo -e "\n${GREEN}[✓] Server is live and operational!${NC}"
fi

# --- STEP 4: KIOSK BROWSER ---
echo -e "${CYAN}[4/4] Starting Kiosk Browser Interface...${NC}"
BROWSER=""
if command -v chromium-browser &> /dev/null; then
    BROWSER="chromium-browser"
elif command -v google-chrome &> /dev/null; then
    BROWSER="google-chrome"
elif command -v chromium &> /dev/null; then
    BROWSER="chromium"
else
    echo -e "${RED}[!] No supported browser found!${NC}"
    exit 1
fi

pkill -f "cva_kiosk_profile" 2>/dev/null
sleep 0.5

if command -v unclutter &> /dev/null; then
    unclutter -idle 0.5 -root &
fi

$BROWSER \
    --kiosk \
    --user-data-dir="/tmp/cva_kiosk_profile" \
    --disable-gpu \
    --disable-gpu-compositing \
    --disable-dev-shm-usage \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --disable-translate \
    --disable-features=Translate \
    --check-for-update-interval=31536000 \
    --overscroll-history-navigation=0 \
    --autoplay-policy=no-user-gesture-required \
    "${SERVER_URL}/" &

if [ -n "$FLASK_PID" ]; then
    wait "$FLASK_PID" 2>/dev/null
else
    wait
fi
