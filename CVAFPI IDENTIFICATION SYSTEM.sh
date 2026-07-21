#!/usr/bin/env bash

# ==============================================================================
#                 CVA FPI IDENTIFICATION SYSTEM - KIOSK LAUNCHER
# ==============================================================================

# --- COLOR DEFINITIONS ---
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# --- CONFIGURATION ---
PORT=5000
SERVER_URL="http://127.0.0.1:${PORT}"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${APP_DIR}/venv"

clear
echo -e "${CYAN}"
echo "======================================================================"
echo "                   CVAFPI IDENTIFICATION SYSTEM                       "
echo "                     Kiosk Engine Auto-Launcher                       "
echo "======================================================================"
echo -e "${NC}"

# Navigate to application directory
cd "$APP_DIR" || { echo -e "${RED}[!] Failed to access directory: $APP_DIR${NC}"; exit 1; }

# --- CLEANUP TRAP ---
cleanup() {
    echo -e "\n${YELLOW}[!] Shutting down CVAFPI Identification System...${NC}"
    if [ -n "$FLASK_PID" ]; then
        kill "$FLASK_PID" 2>/dev/null
    fi
    pkill -f "cva-kiosk-profile" 2>/dev/null
    echo -e "${GREEN}[✓] Shutdown complete.${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# --- STEP 1: DISABLE SCREEN SAVER & POWER SAVING ---
echo -e "${CYAN}[1/4] Configuring display settings...${NC}"
if command -v xset &> /dev/null; then
    xset s off 2>/dev/null
    xset -dpms 2>/dev/null
    xset s noblank 2>/dev/null
    echo -e "${GREEN}[✓] Screen sleep and DPMS disabled.${NC}"
else
    echo -e "${YELLOW}[!] 'xset' not found, skipping screen sleep configuration.${NC}"
fi

# --- STEP 2: ACTIVATE PYTHON VIRTUAL ENVIRONMENT ---
echo -e "${CYAN}[2/4] Initializing Python Backend Environment...${NC}"
if [ -d "$VENV_DIR" ]; then
    source "${VENV_DIR}/bin/activate"
    echo -e "${GREEN}[✓] Virtual environment activated.${NC}"
else
    echo -e "${YELLOW}[!] Virtual environment not found at ${VENV_DIR}. Using system Python.${NC}"
fi

# --- STEP 3: START FLASK BACKEND SERVER ---
echo -e "${CYAN}[3/4] Launching CVAFPI Core Server (app.py)...${NC}"

if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    echo -e "${YELLOW}[!] Port $PORT is already active. Reusing existing server instance.${NC}"
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

# --- STEP 4: LAUNCH CHROMIUM IN FULL KIOSK LOCKDOWN ---
echo -e "${CYAN}[4/4] Starting Kiosk Browser Interface...${NC}"

# Find browser executable
BROWSER=""
if command -v chromium-browser &> /dev/null; then
    BROWSER="chromium-browser"
elif command -v google-chrome &> /dev/null; then
    BROWSER="google-chrome"
elif command -v chromium &> /dev/null; then
    BROWSER="chromium"
else
    echo -e "${RED}[!] No supported browser (Chromium/Chrome) found!${NC}"
    exit 1
fi

# Kill any existing kiosk instances
pkill -f "cva-kiosk-profile" 2>/dev/null
sleep 0.5

# Hide mouse cursor if unclutter is installed
if command -v unclutter &> /dev/null; then
    unclutter -idle 0.5 -root &
fi

# Launch full-screen true Kiosk Mode with GPU Fallbacks
$BROWSER \
    --kiosk \
    --user-data-dir="/tmp/cva-kiosk-profile" \
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
    "${SERVER_URL}/launchpad.html"

wait
