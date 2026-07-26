import datetime
import os
import csv
import urllib.request
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FOLDER = os.path.join(BASE_DIR, "CVA_Database")
os.makedirs(DB_FOLDER, exist_ok=True)

DATA_CSV = os.path.join(BASE_DIR, "data.csv")
REQUIRED_HEADER = ['BARCODE', 'NAME', 'GRADE', 'SECTION', 'ACCESS', 'COLOR', 'NTFY_TOPIC']

def notify_parent(topic, student_name, grade, section, timestamp):
    """Sends a push notification to ntfy.sh."""
    if not topic or str(topic).strip().lower() in ['none', '', 'null']:
        return

    url = f"https://ntfy.sh/{topic.strip()}"
    message = f"Hello! {student_name} ({grade} - {section}) scanned ID at {timestamp}."

    def _push():
        try:
            req = urllib.request.Request(
                url,
                data=message.encode('utf-8'),
                headers={
                    "Title": f"CVA Attendance: {student_name}",
                    "Priority": "high",
                    "Tags": "school,id"
                }
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            print(f"[ntfy Error]: {e}")

    threading.Thread(target=_push, daemon=True).start()

def get_student_by_barcode(barcode):
    """Searches data.csv for student record."""
    if not os.path.exists(DATA_CSV):
        return None

    target = str(barcode).strip().lower()
    with open(DATA_CSV, mode='r', encoding='utf-8-sig', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cleaned = {str(k).strip().upper(): str(v).strip() for k, v in row.items() if k}
            row_barcode = (cleaned.get('BARCODE') or cleaned.get('CODE') or cleaned.get('ID') or '').strip().lower()
            if row_barcode == target:
                if 'NTFY_TOPIC' not in cleaned:
                    cleaned['NTFY_TOPIC'] = 'None'
                return cleaned
    return None

def log_attendance(barcode):
    """Intercepts system command barcodes or logs student attendance."""
    bc_upper = str(barcode).strip().upper()

    # --- SYSTEM COMMAND INTERCEPTION ---
    if "CLOSEBARCODESYS" in bc_upper:
        try:
            os.system("pkill -f cva_kiosk_profile")
        except Exception as e:
            print(f"[Command Error]: {e}")
        return {'status': 'command', 'action': 'close', 'message': 'Kiosk closed'}

    if "EMERSHUTDOWNSYSS" in bc_upper:
        try:
            os.system("sudo shutdown now")
        except Exception as e:
            print(f"[Command Error]: {e}")
        return {'status': 'command', 'action': 'shutdown', 'message': 'System shutting down'}

    if "RETURNTOMNSYS" in bc_upper:
        return {'status': 'command', 'action': 'launchpad', 'message': 'Returning to launchpad'}
    # -----------------------------------

    student = get_student_by_barcode(barcode)

    today_str = datetime.date.today().isoformat()
    log_filename = os.path.join(DB_FOLDER, f"logs_{today_str}.csv")
    timestamp = datetime.datetime.now().strftime('%m/%d/%Y %I:%M:%S %p')

    file_exists = os.path.exists(log_filename)

    with open(log_filename, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists or os.path.getsize(log_filename) == 0:
            writer.writerow(['Timestamp', 'Barcode', 'Name', 'Grade', 'Section', 'Access', 'Color'])

        if student:
            row_data = [
                timestamp,
                student.get('BARCODE', barcode),
                student.get('NAME', 'UNKNOWN'),
                student.get('GRADE', ''),
                student.get('SECTION', ''),
                student.get('ACCESS', 'REGULAR'),
                student.get('COLOR', '#059669')
            ]
            ntfy_topic = student.get('NTFY_TOPIC', 'None')
        else:
            row_data = [
                timestamp,
                barcode,
                'UNKNOWN BARCODE',
                'N/A',
                'N/A',
                'UNREGISTERED',
                '#dc2626'
            ]
            ntfy_topic = 'None'

        writer.writerow(row_data)

        if ntfy_topic:
            notify_parent(
                topic=ntfy_topic,
                student_name=row_data[2],
                grade=row_data[3],
                section=row_data[4],
                timestamp=row_data[0]
            )

        return {
            'status': 'success',
            'data': {
                'timestamp': row_data[0],
                'barcode': row_data[1],
                'name': row_data[2],
                'grade': row_data[3],
                'section': row_data[4],
                'access': row_data[5],
                'color': row_data[6]
            }
        }

def read_log_file_as_arrays(filepath):
    """Reads CSV log file and returns raw array rows expected by logs-manager.html."""
    if not os.path.exists(filepath):
        return []

    rows = []
    with open(filepath, mode='r', encoding='utf-8-sig', errors='ignore') as f:
        reader = csv.reader(f)
        for row in reader:
            if row and any(row):
                while len(row) < 7:
                    row.append('')
                rows.append(row[:7])
    return rows

def get_todays_logs_raw():
    today_str = datetime.date.today().isoformat()
    log_filename = os.path.join(DB_FOLDER, f"logs_{today_str}.csv")
    return read_log_file_as_arrays(log_filename)

def get_logs_by_filename_raw(filename):
    safe_name = os.path.basename(filename)
    log_path = os.path.join(DB_FOLDER, safe_name)
    return read_log_file_as_arrays(log_path)

def get_available_log_files():
    """Scans CVA_Database folder and returns all log filenames for the dropdown."""
    if not os.path.exists(DB_FOLDER):
        return []
    files = [f for f in os.listdir(DB_FOLDER) if f.startswith("logs_") and f.endswith(".csv")]
    files.sort(reverse=True)
    return files

def get_all_students():
    if not os.path.exists(DATA_CSV):
        return []

    rows = []
    with open(DATA_CSV, mode='r', encoding='utf-8-sig', errors='ignore') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if row and any(row):
                while len(row) < 7:
                    row.append('None')
                rows.append(row[:7])
    return rows

def save_student(b, n, g, s, a, c, t="None"):
    if not t or not str(t).strip():
        t = "None"
    else:
        t = str(t).strip()

    rows = []
    updated = False

    if os.path.exists(DATA_CSV):
        with open(DATA_CSV, mode='r', encoding='utf-8-sig', errors='ignore') as f:
            reader = csv.reader(f)
            header = next(reader, None)

            for row in reader:
                if row and any(row):
                    while len(row) < 7:
                        row.append('None')
                    if row[0].strip().lower() == str(b).strip().lower():
                        rows.append([b, n, g, s, a, c, t])
                        updated = True
                    else:
                        rows.append(row[:7])

    if not updated:
        rows.append([b, n, g, s, a, c, t])

    with open(DATA_CSV, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(REQUIRED_HEADER)
        writer.writerows(rows)

def delete_student(barcode):
    if not os.path.exists(DATA_CSV):
        return

    rows = []
    with open(DATA_CSV, mode='r', encoding='utf-8-sig', errors='ignore') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if row and any(row):
                if row[0].strip().lower() != str(barcode).strip().lower():
                    while len(row) < 7:
                        row.append('None')
                    rows.append(row[:7])

    with open(DATA_CSV, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(REQUIRED_HEADER)
        writer.writerows(rows)
