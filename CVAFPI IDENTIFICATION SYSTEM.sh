#!/usr/bin/env bash

# ==============================================================================
#                  CVA FPI IDENTIFICATION SYSTEM - KIOSK LAUNCHER
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

clear
echo -e "${CYAN}"
echo "======================================================================"
echo "                     CVAFPI IDENTIFICATION SYSTEM                     "
echo "                      Kiosk Engine Auto-Launcher                      "
echo "======================================================================"
echo -e "${NC}"

cd "$APP_DIR" || { echo -e "${RED}[!] Failed to access directory: $APP_DIR${NC}"; exit 1; }

# --- SYSTEM UPDATE & DEPENDENCY PROMPT ---
echo -e "${CYAN}[0/4] System & Package Check...${NC}"
read -p "Do you want to update the system and install required packages? (y/n): " update_choice
if [[ "$update_choice" =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}[*] Updating system packages...${NC}"
    sudo apt update -y && sudo apt upgrade -y
    echo -e "${YELLOW}[*] Installing required dependencies...${NC}"
    sudo apt install -y curl lsof unclutter x11-utils python3-pip python3-venv
    echo -e "${GREEN}[✓] System update and package installation complete.${NC}"
else
    echo -e "${YELLOW}[!] Skipping system update. Ensuring minimal tools are present...${NC}"
    sudo apt install -y curl lsof unclutter x11-utils 2>/dev/null || true
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

# --- STEP 2: PYTHON VENV ---
echo -e "${CYAN}[2/4] Initializing Python Backend Environment...${NC}"
if [ -d "$VENV_DIR" ]; then
    source "${VENV_DIR}/bin/activate"
else
    python3 -m venv venv
    source "${VENV_DIR}/bin/activate"
    pip install flask
fi
echo -e "${GREEN}[✓] Virtual environment ready.${NC}"

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

# Wait specifically for Flask PID so exit API closes the script instantly without hanging
if [ -n "$FLASK_PID" ]; then
    wait "$FLASK_PID" 2>/dev/null
else
    wait
fi
