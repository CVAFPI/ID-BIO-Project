#!/usr/bin/env bash

# ==============================================================================
#                 CVAFPI IDENTIFICATION SYSTEM - KIOSK LAUNCHER
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
echo "                    CVAFPI IDENTIFICATION SYSTEM                      "
echo "                      Kiosk Engine Auto-Launcher                      "
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

# --- STEP 1: SYSTEM UPDATES & DEPENDENCIES ---
echo -e "${CYAN}[1/5] Checking System Dependencies...${NC}"

# Optional System Update Prompt
read -p "Do you want whole system to be updated? (Recommended) [y/n]: " -n 1 -r REPLY
echo # Move to a new line

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}[*] Updating system repositories and packages...${NC}"
    sudo apt update && sudo apt upgrade -y
else
    echo -e "${GREEN}[✓] Skipping full system update.${NC}"
fi

# Ensure required packages are present without forcing a full distro upgrade
REQUIRED_PACKAGES=(python3-pip chromium-browser fonts-noto-color-emoji unclutter x11-xserver-utils curl lsof)

echo -e "${YELLOW}[*] Verifying required packages...${NC}"
sudo apt install -y "${REQUIRED_PACKAGES[@]}"

# --- STEP 2: DISABLE SCREEN SAVER & POWER SAVING ---
echo -e "${CYAN}[2/5] Configuring display settings...${NC}"
if command -v xset &> /dev/null; then
    xset s off 2>/dev/null
    xset -dpms 2>/dev/null
    xset s noblank 2>/dev/null
    echo -e "${GREEN}[✓] Screen sleep and DPMS disabled.${NC}"
else
    echo -e "${YELLOW}[!] 'xset' not found, skipping screen sleep configuration.${NC}"
fi

# --- STEP 3: INITIALIZE & AUTO-UPDATE PYTHON ENVIRONMENT (PIP/VENV) ---
echo -e "${CYAN}[3/5] Setting up Python Virtual Environment & Packages...${NC}"

# Create virtualenv automatically if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}[!] Virtual environment not found. Creating a new one at ${VENV_DIR}...${NC}"
    python3 -m venv "$VENV_DIR"
fi

source "${VENV_DIR}/bin/activate"
echo -e "${GREEN}[✓] Virtual environment activated.${NC}"

# Auto-install or upgrade Flask and Python dependencies
echo -e "${CYAN}[*] Auto-updating Python libraries (Flask, etc.)...${NC}"
pip install --upgrade pip setuptools wheel --quiet

if [ -f "${APP_DIR}/requirements.txt" ]; then
    pip install -r "${APP_DIR}/requirements.txt" --upgrade --quiet
    echo -e "${GREEN}[✓] Requirements updated from requirements.txt.${NC}"
else
    pip install flask --upgrade --quiet
    echo -e "${GREEN}[✓] Flask updated to latest version.${NC}"
fi

# --- STEP 4: START FLASK BACKEND SERVER ---
echo -e "${CYAN}[4/5] Launching CVAFPI Core Server (app.py)...${NC}"

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

# --- STEP 5: LAUNCH CHROMIUM IN FULL KIOSK LOCKDOWN ---
echo -e "${CYAN}[5/5] Starting Kiosk Browser Interface...${NC}"

# Find browser executable
BROWSER=""
if command -v chromium &> /dev/null; then
    BROWSER="chromium"
elif command -v chromium-browser &> /dev/null; then
    BROWSER="chromium-browser"
elif command -v google-chrome &> /dev/null; then
    BROWSER="google-chrome"
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
