import os
import csv
import io
import random
import re
import string
import shutil
import threading
import time
from datetime import datetime, timedelta

BASE_DIR = os.environ.get('CVAFPI_DATA_DIR', os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, 'CVA_Database')
DATA_CSV = os.path.join(BASE_DIR, 'data.csv')
BACKUP_CSV = os.path.join(BASE_DIR, 'backup-data.csv')
AUDIT_LOG_FILE = os.path.join(BASE_DIR, 'logs', 'audit_events.csv')
DOUBLE_SCAN_WINDOW_SECONDS = 3
_last_scan_deadlines = {}
_scan_lock = threading.Lock()

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
                pass


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


def record_event(event_type, message, barcode='', details=''):
    try:
        file_exists = os.path.exists(AUDIT_LOG_FILE)
        with open(AUDIT_LOG_FILE, 'a', newline='', encoding='utf-8') as f:
            if not file_exists:
                writer = csv.writer(f)
                writer.writerow(['Timestamp', 'Event Type', 'Message', 'Barcode', 'Details'])
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime('%m/%d/%Y %I:%M:%S %p'),
                str(event_type)[:80],
                str(message)[:500],
                str(barcode)[:100],
                str(details)[:1000],
            ])
    except Exception as error:
        print(f'[Audit Log Error]: {error}')


def get_audit_events(limit=500):
    rows = []
    if not os.path.exists(AUDIT_LOG_FILE):
        return rows
    try:
        with open(AUDIT_LOG_FILE, 'r', encoding='utf-8', errors='ignore', newline='') as f:
            reader = csv.reader(f)
            header = True
            for row in reader:
                if header:
                    header = False
                    continue
                rows.append(row)
    except Exception as error:
        print(f'[Audit Read Error]: {error}')
        return []

    return rows[-max(1, min(int(limit), 2000)):]


def get_all_students():
    """Reads all students from data.csv using exact header: BARCODE,NAME,GRADE,SECTION,ACCESS,COLOR,NTFY_TOPIC"""
    students = {}
    if not os.path.exists(DATA_CSV):
        return students

    try:
        with open(DATA_CSV, 'r', encoding='utf-8', errors='ignore') as f:
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
                color = row[5].strip() if len(row) > 5 else '#059669'
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
    except Exception as e:
        print(f"Error reading data.csv: {e}")

    return students


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

    for target_file in [DATA_CSV, BACKUP_CSV]:
        try:
            with open(target_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerows(rows)
        except Exception as e:
            print(f"Error writing to {target_file}: {e}")


def _read_student_csv(uploaded_file):
    content = uploaded_file.read()
    text = content.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError('The CSV file must include a header row.')

    header_map = {header.strip().upper(): header for header in reader.fieldnames if header}
    aliases = {
        'BARCODE': ('BARCODE', 'ID', 'STUDENT ID', 'STUDENT_ID'),
        'NAME': ('NAME', 'STUDENT NAME', 'STUDENT_NAME', 'FULL NAME'),
        'GRADE': ('GRADE', 'YEAR LEVEL', 'YEAR_LEVEL'),
        'SECTION': ('SECTION', 'CLASS'),
        'ACCESS': ('ACCESS', 'ACCESS LEVEL', 'ACCESS_LEVEL'),
        'COLOR': ('COLOR', 'BADGE COLOR', 'BADGE_COLOR'),
        'TOPIC': ('NTFY_TOPIC', 'TOPIC', 'NOTIFICATION TOPIC', 'NOTIFICATION_TOPIC')
    }
    columns = {
        field: next((header_map[name] for name in names if name in header_map), None)
        for field, names in aliases.items()
    }
    if not columns['BARCODE'] or not columns['NAME']:
        raise ValueError('The CSV must include BARCODE and NAME columns.')

    rows = []
    errors = []
    for row_number, source in enumerate(reader, start=2):
        values = {
            'barcode': (source.get(columns['BARCODE']) or '').strip(),
            'name': (source.get(columns['NAME']) or '').strip(),
            'grade': (source.get(columns['GRADE']) or '').strip() if columns['GRADE'] else '',
            'section': (source.get(columns['SECTION']) or '').strip() if columns['SECTION'] else '',
            'access': (source.get(columns['ACCESS']) or 'REGULAR').strip() if columns['ACCESS'] else 'REGULAR',
            'color': (source.get(columns['COLOR']) or '#059669').strip() if columns['COLOR'] else '#059669',
            'topic': (source.get(columns['TOPIC']) or 'None').strip() if columns['TOPIC'] else 'None'
        }
        if not values['barcode'] or not values['name']:
            errors.append(f'Row {row_number}: barcode and name are required.')
            continue
        oversized_fields = [
            field for field in ('barcode', 'name', 'grade', 'section', 'access', 'topic')
            if len(values[field]) > 100
        ]
        if oversized_fields:
            errors.append(
                f"Row {row_number}: {', '.join(oversized_fields)} must be 100 characters or fewer."
            )
            continue
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', values['color']):
            errors.append(f'Row {row_number}: color must be a valid hexadecimal color.')
            continue
        rows.append(values)

    if not rows and not errors:
        errors.append('The CSV must contain at least one student record.')
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
        raise ValueError('Fix the invalid rows before importing: ' + ' '.join(errors[:3]))
    if not rows:
        raise ValueError('The CSV must contain at least one student record.')
    students = {} if replace_existing else get_all_students()
    for row in rows:
        students[row['barcode']] = row
    save_all_students_to_csv(students)
    return {
        'imported': len(rows),
        'mode': 'replace' if replace_existing else 'merge'
    }


def save_student(b, n, g, s, a, c, t):
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
    base_name = filename.replace('.csv', '')
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
    with _scan_lock:
        students = get_all_students()
        if barcode not in students:
            return {'status': 'error', 'message': 'Student not found'}

        now_monotonic = time.monotonic()
        expired_barcodes = [
            scanned_barcode for scanned_barcode, deadline in _last_scan_deadlines.items()
            if now_monotonic >= deadline
        ]
        for scanned_barcode in expired_barcodes:
            del _last_scan_deadlines[scanned_barcode]
        if now_monotonic < _last_scan_deadlines.get(barcode, 0.0):
            return {
                'status': 'duplicate',
                'message': 'Dual scan detected. Same ID scanned within 3 seconds.'
            }

        student = students[barcode]
        file_path = get_todays_log_filepath()
        existing_ids = set()
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) > 7:
                        existing_ids.add(row[7])

        filename_id = f"{generate_unique_id(existing_ids)}.jpg"
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

        _last_scan_deadlines[barcode] = now_monotonic + DOUBLE_SCAN_WINDOW_SECONDS
        return {'status': 'success', 'data': student, 'image_id': filename_id}
