# /home/hoyoverseedit/ID Bio HTML Project/logger.py
import datetime
import os

def save_log(entry_data):
    today = datetime.date.today().isoformat()
    log_filename = f"/home/hoyoverseedit/ID Bio HTML Project/logs_{today}.csv"
    with open(log_filename, "a") as f:
        f.write(f"{entry_data}\n")
    return f"Saved to {log_filename}"
