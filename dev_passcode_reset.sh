#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SETTINGS_FILE="$SCRIPT_DIR/settings.json"

if [[ ! -f "$SETTINGS_FILE" ]]; then
  echo "settings.json not found at $SETTINGS_FILE" >&2
  exit 1
fi

show_title() {
  cat <<'ASCII'
  ____  _   _ _   _ ____   ____   ____  ____  _  _  ____  ____  ____  ____   _____ 
 |  _ \| | | | \ | |  _ \ / ___| |  _ \|  _ \| || |/ ___|/ ___||  _ \|  _ \ / ___|
 | | | | | | |  \| | |_) | |     | |_) | |_) | || |\___ \\___ \| |_) | |_) | |    
 | |_| | |_| | |\  |  __/| |___  |  __/|  __/|__   _|___) |___) |  __/|  _ <| |___ 
 |____/ \___/|_| \_|_|    \_____| |_|   |_|      |_| |____/|____/|_|   |_| \_\\_____|
ASCII
  echo
  echo "      DEV PASSCODE RECOVERY TOOL"
  echo "      local dev only - no public sharing"
  echo
}

show_status() {
  python3 - "$SETTINGS_FILE" <<'PY'
import json, os, sqlite3, sys

settings_path = os.path.abspath(sys.argv[1])
settings_dir = os.path.dirname(settings_path)
with open(settings_path, 'r', encoding='utf-8') as f:
  settings = json.load(f)

database_path = os.path.join(settings_dir, 'CVA_Database', 'cva.sqlite3')
if os.path.exists(database_path):
  try:
    with sqlite3.connect(f'file:{database_path}?mode=ro', uri=True) as connection:
      stored = connection.execute(
        "SELECT setting_key, setting_value FROM app_settings "
        "WHERE setting_key IN ('pin_hash', 'pin_salt', 'security_question')"
      ).fetchall()
    settings.update(dict(stored))
  except sqlite3.DatabaseError:
    pass

configured = bool(settings.get('pin_hash') and settings.get('pin_salt'))
print("Current status:")
print(f"  passcode configured: {configured}")
print(f"  security question: {settings.get('security_question', '') or '(none)'}")
print(f"  pin_hash set: {bool(settings.get('pin_hash'))}")
PY
}

apply_reset() {
  local mode="$1"
  local pin="${2:-}"
  local question="${3:-}"
  local answer="${4:-}"

  python3 - "$SETTINGS_FILE" "$mode" "$pin" "$question" "$answer" <<'PY'
import hashlib
import json
import os
import re
import secrets
import sqlite3
import sys

settings_path, mode, new_pin, question, answer = sys.argv[1:6]
pattern = re.compile(r'^\S{4,12}$')


def hash_secret(value, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', value.encode('utf-8'), salt.encode('utf-8'), 200000)
    return salt, digest.hex()

with open(settings_path, 'r', encoding='utf-8') as f:
    settings = json.load(f)

if mode == 'clear':
    settings['pin_hash'] = ''
    settings['pin_salt'] = ''
    settings['security_question'] = ''
    settings['security_answer_hash'] = ''
    settings['security_answer_salt'] = ''
elif mode == 'set':
    pin = str(new_pin or '').strip()
    if not pin:
        raise SystemExit('Password cannot be blank.')
    if not pattern.fullmatch(pin):
        raise SystemExit('Password must be 4 to 12 non-space characters.')

    question_text = str(question or settings.get('security_question', '')).strip()[:200]
    answer_text = str(answer or '').strip().lower()

    if question_text and not answer_text:
        raise SystemExit('If you set a security question, you must also set the answer.')
    if answer_text and not question_text:
        raise SystemExit('If you set a security answer, you must also set the question.')

    settings['pin_salt'], settings['pin_hash'] = hash_secret(pin)
    settings['security_question'] = question_text
    if question_text and answer_text:
        settings['security_answer_salt'], settings['security_answer_hash'] = hash_secret(answer_text)
    else:
        settings['security_answer_hash'] = ''
        settings['security_answer_salt'] = ''
else:
    raise SystemExit(f'Unsupported mode: {mode}')

with open(settings_path, 'w', encoding='utf-8') as f:
    json.dump(settings, f, indent=4)
    f.write('\n')

database_dir = os.path.join(os.path.dirname(settings_path), 'CVA_Database')
database_path = os.path.join(database_dir, 'cva.sqlite3')
if os.path.exists(database_path):
  security_settings = {
    key: str(settings.get(key, ''))
    for key in (
      'pin_hash', 'pin_salt', 'security_question',
      'security_answer_hash', 'security_answer_salt'
    )
  }
  with sqlite3.connect(database_path) as connection:
    connection.executemany(
      '''INSERT INTO app_settings (setting_key, setting_value)
         VALUES (?, ?)
         ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value''',
      security_settings.items()
    )

  backup_path = os.path.join(database_dir, 'cva.sqlite3.backup')
  temporary_backup = os.path.join(database_dir, 'cva.sqlite3.reset-backup')
  try:
    with sqlite3.connect(database_path) as source:
      with sqlite3.connect(temporary_backup) as destination:
        source.backup(destination)
    os.replace(temporary_backup, backup_path)
  finally:
    if os.path.exists(temporary_backup):
      os.remove(temporary_backup)

print(f'Updated settings for mode={mode}')
PY
}

show_title

while true; do
  echo "[1] Set password"
  echo "[2] Set password + security Q/A"
  echo "[3] Clear password"
  echo "[4] Show current status"
  echo "[5] Exit"
  echo
  read -r -p "Select option: " choice
  echo

  case "$choice" in
    1)
      read -r -p "Password: " new_pin
      apply_reset "set" "$new_pin" "" ""
      ;;
    2)
      read -r -p "Password: " new_pin
      read -r -p "Security Question: " question
      read -r -p "Security Answer: " answer
      apply_reset "set" "$new_pin" "$question" "$answer"
      ;;
    3)
      echo "Clearing password and recovery info..."
      apply_reset "clear" "" "" ""
      ;;
    4)
      show_status
      ;;
    5)
      echo "Goodbye."
      exit 0
      ;;
    *)
      echo "Invalid option. Choose 1-5."
      ;;
  esac

  echo
done
