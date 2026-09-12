import os
import csv
import io
import random
import string
import sqlite3
import shutil
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, 'CVA_Database')
DATABASE_FILE = os.path.join(DB_DIR, 'cva.sqlite3')
DATA_CSV = os.path.join(BASE_DIR, 'data.csv')
BACKUP_CSV = os.path.join(BASE_DIR, 'backup-data.csv')

os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)


def get_connection():
    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    connection.execute('PRAGMA journal_mode = WAL')
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.executescript('''
            CREATE TABLE IF NOT EXISTS students (
                barcode TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                grade TEXT NOT NULL DEFAULT '',
                section TEXT NOT NULL DEFAULT '',
                access TEXT NOT NULL DEFAULT 'REGULAR',
                color TEXT NOT NULL DEFAULT '#059669',
                topic TEXT NOT NULL DEFAULT 'None'
            );

            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                barcode TEXT NOT NULL,
                name TEXT NOT NULL,
                grade TEXT NOT NULL,
                section TEXT NOT NULL,
                access TEXT NOT NULL,
                color TEXT NOT NULL,
                image_id TEXT NOT NULL UNIQUE
            );

            CREATE INDEX IF NOT EXISTS idx_attendance_timestamp
                ON attendance(timestamp);
            CREATE INDEX IF NOT EXISTS idx_attendance_barcode
                ON attendance(barcode);

            CREATE TABLE IF NOT EXISTS app_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL
            );
        ''')


def get_app_settings():
    with get_connection() as connection:
        rows = connection.execute(
            'SELECT setting_key, setting_value FROM app_settings'
        ).fetchall()
    return {row['setting_key']: row['setting_value'] for row in rows}


def save_app_settings(settings):
    with get_connection() as connection:
        for key, value in settings.items():
            connection.execute('''
                INSERT INTO app_settings (setting_key, setting_value)
                VALUES (?, ?)
                ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value
            ''', (key, str(value)))


def migrate_csv_data():
    """Import legacy CSV data once without removing the original files."""
    with get_connection() as connection:
        sources = [source for source in (DATA_CSV, BACKUP_CSV) if os.path.exists(source)]
        for source in sources:
            with open(source, 'r', encoding='utf-8', errors='ignore') as file:
                reader = csv.reader(file)
                for row in reader:
                    if not row or row[0].strip().upper() == 'BARCODE':
                        continue
                    values = [value.strip() for value in row[:7]]
                    values += [''] * (7 - len(values))
                    if values[0]:
                        connection.execute('''
                            INSERT OR IGNORE INTO students
                            (barcode, name, grade, section, access, color, topic)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            values[0], values[1], values[2], values[3],
                            values[4] or 'REGULAR', values[5] or '#059669',
                            values[6] or 'None'
                        ))

        attendance_count = connection.execute(
            'SELECT COUNT(*) FROM attendance'
        ).fetchone()[0]
        if attendance_count == 0:
            for folder_name in os.listdir(DB_DIR):
                if not folder_name.startswith('logs_'):
                    continue
                file_path = os.path.join(DB_DIR, folder_name, f'{folder_name}.csv')
                if not os.path.exists(file_path):
                    continue
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                    for row in csv.reader(file):
                        if not row or row[0].strip().upper() == 'TIMESTAMP' or len(row) < 8:
                            continue
                        connection.execute('''
                            INSERT OR IGNORE INTO attendance
                            (timestamp, barcode, name, grade, section, access, color, image_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', tuple(value.strip() for value in row[:8]))


def parse_student_csv(file_object):
    file_object.stream.seek(0)
    text_stream = io.TextIOWrapper(
        file_object.stream, encoding='utf-8-sig', newline=''
    )
    reader = csv.DictReader(text_stream)
    original_headers = reader.fieldnames or []
    headers = [header.strip().upper() for header in original_headers]
    aliases = {
        'BARCODE': ('BARCODE', 'ID', 'STUDENT ID', 'STUDENT_ID'),
        'NAME': ('NAME', 'STUDENT NAME', 'STUDENT_NAME', 'FULL NAME'),
        'GRADE': ('GRADE', 'YEAR LEVEL', 'YEAR_LEVEL'),
        'SECTION': ('SECTION', 'CLASS'),
        'ACCESS': ('ACCESS', 'ACCESS LEVEL', 'ACCESS_LEVEL'),
        'COLOR': ('COLOR', 'BADGE COLOR', 'BADGE_COLOR'),
        'TOPIC': ('NTFY_TOPIC', 'TOPIC', 'NOTIFICATION TOPIC', 'NOTIFICATION_TOPIC')
    }
    header_map = {
        header.strip().upper(): header for header in original_headers
    }
    selected = {}
    for field, names in aliases.items():
        selected[field] = next((header_map[name] for name in names if name in header_map), None)

    if not selected['BARCODE'] or not selected['NAME']:
        raise ValueError('The CSV must contain BARCODE and NAME columns.')

    records = []
    errors = []
    for line_number, row in enumerate(reader, start=2):
        values = {
            'barcode': (row.get(selected['BARCODE']) or '').strip(),
            'name': (row.get(selected['NAME']) or '').strip(),
            'grade': (row.get(selected['GRADE']) or '').strip() if selected['GRADE'] else '',
            'section': (row.get(selected['SECTION']) or '').strip() if selected['SECTION'] else '',
            'access': (row.get(selected['ACCESS']) or '').strip() if selected['ACCESS'] else 'REGULAR',
            'color': (row.get(selected['COLOR']) or '').strip() if selected['COLOR'] else '#059669',
            'topic': (row.get(selected['TOPIC']) or '').strip() if selected['TOPIC'] else 'None'
        }
        if not values['barcode'] or not values['name']:
            errors.append(f'Row {line_number}: barcode and name are required.')
            continue
        records.append(values)
    return headers, records, errors


def preview_student_csv(file_object):
    headers, records, errors = parse_student_csv(file_object)
    with get_connection() as connection:
        existing = {
            row['barcode'] for row in connection.execute('SELECT barcode FROM students')
        }
    return {
        'headers': headers,
        'total_rows': len(records) + len(errors),
        'valid_rows': len(records),
        'invalid_rows': len(errors),
        'new_records': sum(record['barcode'] not in existing for record in records),
        'updates': sum(record['barcode'] in existing for record in records),
        'errors': errors[:20],
        'sample': records[:5]
    }


def import_student_csv(file_object, replace_existing=False):
    _, records, errors = parse_student_csv(file_object)
    if errors:
        raise ValueError('Fix the invalid rows before importing: ' + ' '.join(errors[:3]))
    with get_connection() as connection:
        if replace_existing:
            connection.execute('DELETE FROM students')
        for record in records:
            connection.execute('''
                INSERT INTO students (barcode, name, grade, section, access, color, topic)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(barcode) DO UPDATE SET
                    name = excluded.name, grade = excluded.grade,
                    section = excluded.section, access = excluded.access,
                    color = excluded.color, topic = excluded.topic
            ''', tuple(record[field] for field in (
                'barcode', 'name', 'grade', 'section', 'access', 'color', 'topic'
            )))
    return {'imported': len(records), 'mode': 'replace' if replace_existing else 'merge'}

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

# Run cleanup and initialize the local database automatically on startup.
cleanup_old_logs(7)
initialize_database()
migrate_csv_data()

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
    return os.path.join(folder_path, f"{folder_name}.csv")

def get_all_students():
    with get_connection() as connection:
        rows = connection.execute('SELECT * FROM students ORDER BY barcode').fetchall()
    return {row['barcode']: dict(row) for row in rows}

def save_student(b, n, g, s, a, c, t):
    with get_connection() as connection:
        connection.execute('''
            INSERT INTO students (barcode, name, grade, section, access, color, topic)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(barcode) DO UPDATE SET
                name = excluded.name, grade = excluded.grade,
                section = excluded.section, access = excluded.access,
                color = excluded.color, topic = excluded.topic
        ''', (b, n, g, s, a, c, t))

def delete_student(barcode):
    with get_connection() as connection:
        connection.execute('DELETE FROM students WHERE barcode = ?', (barcode,))

def get_available_log_files():
    with get_connection() as connection:
        dates = connection.execute('''
            SELECT DISTINCT substr(timestamp, 7, 4) || '-' ||
                substr(timestamp, 1, 2) || '-' || substr(timestamp, 4, 2) AS log_date
            FROM attendance ORDER BY log_date DESC
        ''').fetchall()
    return [f"logs_{row['log_date']}.csv" for row in dates]

def get_todays_logs_raw():
    return get_logs_by_date(datetime.now().strftime('%Y-%m-%d'))


def get_logs_by_date(date_str):
    display_date = datetime.strptime(date_str, '%Y-%m-%d').strftime('%m/%d/%Y')
    with get_connection() as connection:
        rows = connection.execute('''
            SELECT timestamp, barcode, name, grade, section, access, color, image_id
            FROM attendance WHERE timestamp LIKE ? ORDER BY id
        ''', (f'{display_date}%',)).fetchall()
    return [
        ['Timestamp', 'Barcode', 'Name', 'Grade', 'Section', 'Access', 'Color', 'ID-MATCHER']
    ] + [list(row) for row in rows]

def get_logs_by_filename_raw(filename):
    if not filename or filename.lower() == 'today':
        return get_todays_logs_raw()
    base_name = filename.removesuffix('.csv')
    if not base_name.startswith('logs_'):
        return []
    return get_logs_by_date(base_name.removeprefix('logs_'))

def log_attendance(barcode):
    with get_connection() as connection:
        row = connection.execute(
            'SELECT * FROM students WHERE barcode = ?', (barcode,)
        ).fetchone()
    if row is None:
        return {'status': 'error', 'message': 'Student not found'}

    student = dict(row)
    with get_connection() as connection:
        existing_ids = {
            item[0] for item in connection.execute('SELECT image_id FROM attendance')
        }
    image_id = generate_unique_id(existing_ids)
    filename_id = f"{image_id}.jpg"

    now = datetime.now()
    timestamp_str = now.strftime('%m/%d/%Y %I:%M:%S %p')

    with get_connection() as connection:
        connection.execute('''
            INSERT INTO attendance
            (timestamp, barcode, name, grade, section, access, color, image_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp_str, student['barcode'], student['name'], student['grade'],
            student['section'], student['access'], student['color'], filename_id
        ))

    return {
        'status': 'success',
        'data': student,
        'image_id': filename_id
    }
