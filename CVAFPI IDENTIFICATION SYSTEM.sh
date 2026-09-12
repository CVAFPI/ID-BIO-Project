#!/usr/bin/env bash

# ==============================================================================
#                 CVAFPI IDENTIFICATION SYSTEM - KIOSK LAUNCHER v2.0
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
REPO_URL="https://github.com/CVAFPI/ID-BIO-Project.git"

clear
echo -e "${CYAN}"
echo "======================================================================"
echo "                       CVAFPI IDENTIFICATION SYSTEM                   "
echo "                Kiosk Engine Auto-Launcher (v2.0 stable)              "
echo "======================================================================"
echo -e "${NC}"

# --- DISPLAY SYSTEM INFO (FASTFETCH / NEOFETCH) ---
if command -v fastfetch &> /dev/null; then
    fastfetch
elif command -v neofetch &> /dev/null; then
    neofetch
fi

echo -e "${GREEN}Welcome to CVAFPI ID SYSTEM v2.0${NC}\n"

cd "$APP_DIR" || { echo -e "${RED}[!] Failed to access directory: $APP_DIR${NC}"; exit 1; }

# Normal kiosk startup is graphical; keep diagnostics in a local file for IT.
exec >>"${APP_DIR}/launcher.log" 2>&1

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

        # Pull code updates without touching the local SQLite database.
        git pull origin "$BRANCH" 2>/dev/null || git pull origin main 2>/dev/null

        echo -e "${GREEN}[✓] Application successfully updated! Restarting launcher...${NC}"
        exec bash "$0" "$@"
    else
        echo -e "${GREEN}[✓] Application is already up to date.${NC}"
    fi
else
    echo -e "${YELLOW}[!] Git command missing. Skipping GitHub auto-update check.${NC}"
fi

# --- DEPENDENCY CHECK ---
echo -e "${CYAN}[0/4] Checking application dependencies...${NC}"
if ! command -v python3 >/dev/null 2>&1; then
    echo -e "${RED}[!] Python 3 is required. See launcher.log for details.${NC}"
    exit 1
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

# --- STEP 2: PYTHON VENV & SQLITE DATABASE INITIALIZATION ---
echo -e "${CYAN}[2/4] Initializing Python Backend Environment & Database Integrity Check...${NC}"
if [ -d "$VENV_DIR" ]; then
    source "${VENV_DIR}/bin/activate"
else
    python3 -m venv venv
    source "${VENV_DIR}/bin/activate"
fi
if ! python3 -c "import flask, PIL" >/dev/null 2>&1; then
    python3 -m pip install -r requirements.txt
fi
echo -e "${GREEN}[✓] Virtual environment ready.${NC}"

echo -e "${CYAN}[*] Initializing SQLite database and importing legacy CSV data if needed...${NC}"
python3 -c "import logger; print(f'[✓] SQLite database ready: {logger.DATABASE_FILE}')"

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
