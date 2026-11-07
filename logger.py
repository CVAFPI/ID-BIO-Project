import os
import csv
import io
import random
import re
import string
import shutil
import tempfile
import threading
import logging
import time
from datetime import datetime, timedelta

DATA_LOCK = threading.RLock()
_SCAN_LOCK = threading.Lock()
_LAST_SCAN_DEADLINES = {}
_DOUBLE_SCAN_WINDOW_SECONDS = 3.0
BASE_DIR = os.environ.get(
    'CVAFPI_DATA_DIR', os.path.dirname(os.path.abspath(__file__))
)
DB_DIR = os.path.join(BASE_DIR, 'CVA_Database')
DATA_CSV = os.path.join(BASE_DIR, 'data.csv')
BACKUP_CSV = os.path.join(BASE_DIR, 'backup-data.csv')
AUDIT_CSV = os.path.join(BASE_DIR, 'audit.csv')
LOGGER = logging.getLogger(__name__)

os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)

def cleanup_old_logs(days=7):
    """Automatically deletes log folders and snapshots older than the specified days for privacy compliance."""
    if not os.path.exists(DB_DIR):
        return

    cutoff_date = datetime.now().date() - timedelta(days=days)

    for name in os.listdir(DB_DIR):
        if name.startswith('logs_'):
            date_str = name.replace('logs_', '')
            try:
                log_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                if log_date < cutoff_date:
                    folder_path = os.path.join(DB_DIR, name)
                    if os.path.isdir(folder_path):
                        shutil.rmtree(folder_path)
                        print(f"[Privacy Cleanup] Purged expired log folder: {name}")
            except ValueError:
                pass # Skip if folder name format doesn't match date

# Run cleanup automatically on startup
cleanup_old_logs(7)

def generate_unique_id(existing_ids):
    while True:
        chars = string.ascii_letters + string.digits
        uid = ''.join(random.choices(chars, k=6))
        if uid not in existing_ids:
            return uid

def get_todays_log_filepath():
    date_str = datetime.now().strftime('%Y-%m-%d')
    folder_name = f"logs_{date_str}"
    folder_path = os.path.join(DB_DIR, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    file_path = os.path.join(folder_path, f"{folder_name}.csv")

    if not os.path.exists(file_path):
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Timestamp', 'Barcode', 'Name', 'Grade', 'Section', 'Access', 'Color', 'ID-MATCHER'])
    return file_path

def get_all_students():
    """Reads all students from data.csv using exact header: BARCODE,NAME,GRADE,SECTION,ACCESS,COLOR,NTFY_TOPIC"""
    students = {}
    with DATA_LOCK:
        source_file = DATA_CSV
        if not os.path.isfile(source_file) or os.path.getsize(source_file) == 0:
            source_file = BACKUP_CSV
        if not os.path.exists(source_file):
            return students

        with open(source_file, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or len(row) < 1:
                    continue
                if row[0].strip().upper() == 'BARCODE':
                    continue

                barcode = row[0].strip()
                name = row[1].strip() if len(row) > 1 else ''
                grade = row[2].strip() if len(row) > 2 else ''
                section = row[3].strip() if len(row) > 3 else ''
                access = row[4].strip() if len(row) > 4 else 'REGULAR'
                color = _safe_color(row[5].strip()) if len(row) > 5 else '#059669'
                topic = row[6].strip() if len(row) > 6 else 'None'

                if barcode:
                    students[barcode] = {
                        'barcode': barcode,
                        'name': name,
                        'grade': grade,
                        'section': section,
                        'access': access,
                        'color': color,
                        'topic': topic
                    }
    return students


def _write_csv_atomically(target_file, rows):
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w',
            newline='',
            encoding='utf-8',
            dir=os.path.dirname(target_file),
            delete=False
        ) as f:
            temp_path = f.name
            csv.writer(f).writerows(rows)
        os.replace(temp_path, target_file)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def _safe_color(value):
    return value if re.fullmatch(r'#[0-9a-fA-F]{6}', value) else '#059669'


def validate_student_identity(barcode, name):
    if not barcode or not name:
        return 'Barcode and name are required.'
    if len(barcode) > 100:
        return 'Barcode must not exceed 100 characters.'
    if len(name) > 100:
        return 'Name must not exceed 100 characters.'
    return None


def record_event(event_type, message, barcode='', details=''):
    row = [
        datetime.now().strftime('%m/%d/%Y %I:%M:%S %p'),
        str(event_type)[:80],
        str(message)[:500],
        str(barcode)[:100],
        str(details)[:1000],
    ]
    with DATA_LOCK:
        try:
            needs_header = not os.path.isfile(AUDIT_CSV) or os.path.getsize(AUDIT_CSV) == 0
            with open(AUDIT_CSV, 'a', newline='', encoding='utf-8') as audit_file:
                writer = csv.writer(audit_file)
                if needs_header:
                    writer.writerow(['Timestamp', 'Type', 'Message', 'Barcode', 'Details'])
                writer.writerow(row)
                audit_file.flush()
                os.fsync(audit_file.fileno())
        except OSError:
            LOGGER.exception('Unable to append audit event to %s', AUDIT_CSV)


def get_audit_events(limit=500):
    try:
        limit = max(1, min(int(limit), 2000))
    except (TypeError, ValueError):
        limit = 500

    with DATA_LOCK:
        if not os.path.isfile(AUDIT_CSV):
            return []
        with open(AUDIT_CSV, 'r', newline='', encoding='utf-8-sig') as audit_file:
            rows = list(csv.reader(audit_file))

    if rows and rows[0] and rows[0][0].strip().lower() == 'timestamp':
        rows = rows[1:]
    return [row for row in reversed(rows[-limit:]) if row]


def save_all_students_to_csv(students_dict):
    """Writes dictionary to data.csv and backup-data.csv using the exact column format."""
    rows = [['BARCODE', 'NAME', 'GRADE', 'SECTION', 'ACCESS', 'COLOR', 'NTFY_TOPIC']]
    for barcode, s in students_dict.items():
        rows.append([
            s.get('barcode', barcode),
            s.get('name', ''),
            s.get('grade', ''),
            s.get('section', ''),
            s.get('access', 'REGULAR'),
            s.get('color', '#059669'),
            s.get('topic', 'None')
        ])

    with DATA_LOCK:
        for target_file in [DATA_CSV, BACKUP_CSV]:
            _write_csv_atomically(target_file, rows)

def _read_student_csv(uploaded_file):
    content = uploaded_file.read()
    text = content.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError('The CSV file must include a header row.')

    normalized_headers = [
        header.strip().upper() if header else ''
        for header in reader.fieldnames
    ]
    if any(not header for header in normalized_headers):
        raise ValueError('The CSV header row cannot contain empty column names.')
    if len(normalized_headers) != len(set(normalized_headers)):
        raise ValueError('The CSV header row contains duplicate column names.')
    headers = dict(zip(normalized_headers, reader.fieldnames))
    if 'BARCODE' not in headers or 'NAME' not in headers:
        raise ValueError('The CSV must include BARCODE and NAME columns.')

    rows = []
    errors = []
    seen_barcodes = set()
    for row_number, source in enumerate(reader, start=2):
        if None in source and any(value.strip() for value in source[None] if value):
            errors.append(f'Row {row_number} contains more values than the header.')
            continue
        barcode = (source.get(headers['BARCODE']) or '').strip()
        name = (source.get(headers['NAME']) or '').strip()
        identity_error = validate_student_identity(barcode, name)
        if identity_error:
            errors.append(f'Row {row_number}: {identity_error}')
            continue
        if barcode in seen_barcodes:
            errors.append(f'Row {row_number} duplicates barcode {barcode}.')
            continue
        color = (source.get(headers.get('COLOR', '')) or '').strip()
        if color and not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
            errors.append(f'Row {row_number} has an invalid color; use a six-digit hex value.')
            continue
        seen_barcodes.add(barcode)
        rows.append({
            'barcode': barcode,
            'name': name,
            'grade': (source.get(headers.get('GRADE', '')) or '').strip(),
            'section': (source.get(headers.get('SECTION', '')) or '').strip(),
            'access': (source.get(headers.get('ACCESS', '')) or 'REGULAR').strip(),
            'color': color or '#059669',
            'topic': (source.get(headers.get('NTFY_TOPIC', '')) or 'None').strip()
        })
    if not rows and not errors:
        errors.append('The CSV must include at least one student record.')
    return rows, errors

def preview_student_csv(uploaded_file):
    rows, errors = _read_student_csv(uploaded_file)
    existing = get_all_students()
    barcodes = {row['barcode'] for row in rows}
    return {
        'total_rows': len(rows) + len(errors),
        'valid_rows': len(rows),
        'invalid_rows': len(errors),
        'errors': errors[:10],
        'new_records': len(barcodes - existing.keys()),
        'updates': len(barcodes & existing.keys()),
        'sample': rows[:8]
    }

def import_student_csv(uploaded_file, replace_existing=False):
    rows, errors = _read_student_csv(uploaded_file)
    if errors:
        raise ValueError(' '.join(errors[:10]))
    if not rows:
        raise ValueError('The CSV must include at least one student record.')
    with DATA_LOCK:
        students = {} if replace_existing else get_all_students()
        for row in rows:
            students[row['barcode']] = row
        save_all_students_to_csv(students)
    return {
        'imported': len(rows),
        'mode': 'replace' if replace_existing else 'merge'
    }

def save_student(b, n, g, s, a, c, t):
    with DATA_LOCK:
        students = get_all_students()
        students[b] = {
            'barcode': b,
            'name': n,
            'grade': g,
            'section': s,
            'access': a,
            'color': c,
            'topic': t
        }
        save_all_students_to_csv(students)

def delete_student(barcode):
    with DATA_LOCK:
        students = get_all_students()
        if barcode in students:
            del students[barcode]
            save_all_students_to_csv(students)

def get_available_log_files():
    if not os.path.exists(DB_DIR):
        return []
    files = []
    for name in os.listdir(DB_DIR):
        if name.startswith('logs_') and os.path.isdir(os.path.join(DB_DIR, name)):
            csv_filename = f"{name}.csv"
            csv_path = os.path.join(DB_DIR, name, csv_filename)
            if os.path.exists(csv_path):
                files.append(csv_filename)
    return sorted(files, reverse=True)

def get_todays_logs_raw():
    file_path = get_todays_log_filepath()
    rows = []
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            for row in reader:
                if row:
                    rows.append(row)
    return rows

def get_logs_by_filename_raw(filename):
    if not filename or filename.lower() == 'today':
        return get_todays_logs_raw()
    if not re.fullmatch(r'logs_\d{4}-\d{2}-\d{2}\.csv', filename):
        raise ValueError('Invalid log file name.')
    base_name = filename[:-4]
    try:
        datetime.strptime(base_name[5:], '%Y-%m-%d')
    except ValueError as error:
        raise ValueError('Invalid log file date.') from error
    file_path = os.path.join(DB_DIR, base_name, f"{base_name}.csv")
    rows = []
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            for row in reader:
                if row:
                    rows.append(row)
    return rows

def log_attendance(barcode):
    with _SCAN_LOCK:
        with DATA_LOCK:
            students = get_all_students()
            if barcode not in students:
                return {'status': 'error', 'message': 'Student not found'}

            now_monotonic = time.monotonic()
            expired_barcodes = [
                scanned_barcode
                for scanned_barcode, deadline in _LAST_SCAN_DEADLINES.items()
                if now_monotonic >= deadline
            ]
            for scanned_barcode in expired_barcodes:
                del _LAST_SCAN_DEADLINES[scanned_barcode]

            if now_monotonic < _LAST_SCAN_DEADLINES.get(barcode, 0.0):
                return {
                    'status': 'duplicate',
                    'message': 'Dual scan detected. Same ID scanned within 3 seconds.'
                }

            student = students[barcode]
            file_path = get_todays_log_filepath()
            existing_ids = set()
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8-sig', newline='') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if len(row) > 7:
                            existing_ids.add(row[7])

            image_id = generate_unique_id(existing_ids)
            filename_id = f"{image_id}.jpg"
            timestamp_str = datetime.now().strftime('%m/%d/%Y %I:%M:%S %p')
            row_data = [
                timestamp_str,
                student.get('barcode', ''),
                student.get('name', ''),
                student.get('grade', ''),
                student.get('section', ''),
                student.get('access', 'REGULAR'),
                student.get('color', '#059669'),
                filename_id
            ]

            with open(file_path, 'a', newline='', encoding='utf-8') as f:
                csv.writer(f).writerow(row_data)
            _LAST_SCAN_DEADLINES[barcode] = (
                now_monotonic + _DOUBLE_SCAN_WINDOW_SECONDS
            )

    return {
        'status': 'success',
        'data': {**student, 'timestamp': timestamp_str},
        'image_id': filename_id
    }
