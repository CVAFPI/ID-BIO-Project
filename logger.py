import os
import csv
import io
import random
import string
import sqlite3
import shutil
import json
import re
import tempfile
import threading
import time
from datetime import datetime, timedelta

BASE_DIR = os.path.abspath(os.environ.get(
    'CVAFPI_DATA_DIR', os.path.dirname(os.path.abspath(__file__))
))
DB_DIR = os.path.join(BASE_DIR, 'CVA_Database')
DATABASE_FILE = os.path.join(DB_DIR, 'cva.sqlite3')
DATABASE_BACKUP_FILE = os.path.join(DB_DIR, 'cva.sqlite3.backup')
DOUBLE_SCAN_WINDOW_SECONDS = 3
database_startup_error = None
_backup_lock = threading.Lock()

os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)


def get_connection():
    connection = sqlite3.connect(DATABASE_FILE, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    connection.execute('PRAGMA busy_timeout = 15000')
    connection.execute('PRAGMA journal_mode = WAL')
    connection.execute('PRAGMA synchronous = NORMAL')
    return connection


def initialize_database():
    global database_startup_error
    schema = '''
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
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                message TEXT NOT NULL,
                barcode TEXT NOT NULL DEFAULT '',
                details TEXT NOT NULL DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp
                ON audit_events(timestamp);
            CREATE TABLE IF NOT EXISTS recent_scans (
                barcode TEXT PRIMARY KEY,
                scanned_at REAL NOT NULL
            );
    '''
    try:
        with get_connection() as connection:
            connection.executescript(schema)
        database_startup_error = None
    except sqlite3.DatabaseError as error:
        if not os.path.exists(DATABASE_BACKUP_FILE):
            database_startup_error = f'Database could not be opened: {error}'
            return
        try:
            damaged_copy = DATABASE_FILE + '.damaged'
            if os.path.exists(DATABASE_FILE):
                shutil.copy2(DATABASE_FILE, damaged_copy)
            shutil.copy2(DATABASE_BACKUP_FILE, DATABASE_FILE)
            with get_connection() as connection:
                connection.executescript(schema)
            database_startup_error = None
            record_event('database_recovery', 'Database restored automatically from backup.')
        except (OSError, sqlite3.DatabaseError) as recovery_error:
            database_startup_error = f'Database recovery failed: {recovery_error}'


def backup_database():
    if database_startup_error or not os.path.exists(DATABASE_FILE):
        return False
    temporary_backup = None
    try:
        with _backup_lock:
            fd, temporary_backup = tempfile.mkstemp(
                prefix='cva.sqlite3.', suffix='.backup', dir=DB_DIR
            )
            os.close(fd)
            source = get_connection()
            try:
                destination = sqlite3.connect(temporary_backup)
                try:
                    source.backup(destination)
                finally:
                    destination.close()
            finally:
                source.close()
            os.replace(temporary_backup, DATABASE_BACKUP_FILE)
            temporary_backup = None
        return True
    except (OSError, sqlite3.DatabaseError) as error:
        if temporary_backup and os.path.exists(temporary_backup):
            os.unlink(temporary_backup)
        print(f'[Database Backup Error]: {error}')
        return False


def record_event(event_type, message, barcode='', details=''):
    try:
        with get_connection() as connection:
            connection.execute(
                '''INSERT INTO audit_events
                   (timestamp, event_type, message, barcode, details)
                   VALUES (?, ?, ?, ?, ?)''',
                (datetime.now().strftime('%m/%d/%Y %I:%M:%S %p'),
                 str(event_type)[:80], str(message)[:500],
                 str(barcode)[:100], str(details)[:1000])
            )
        backup_database()
    except sqlite3.DatabaseError as error:
        print(f'[Audit Log Error]: {error}')


def get_audit_events(limit=500):
    with get_connection() as connection:
        rows = connection.execute(
            '''SELECT timestamp, event_type, message, barcode, details
               FROM audit_events ORDER BY id DESC LIMIT ?''',
            (max(1, min(int(limit), 2000)),)
        ).fetchall()
    return [list(row) for row in rows]


def _serialize_setting(value):
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if value is None:
        return ''
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _deserialize_setting(value):
    if value == 'true':
        return True
    if value == 'false':
        return False
    if isinstance(value, str) and value.startswith(('{', '[')):
        try:
            decoded = json.loads(value)
            if isinstance(decoded, (dict, list)):
                return decoded
        except (json.JSONDecodeError, TypeError):
            pass
    return value


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


def parse_student_csv(file_object):
    file_object.stream.seek(0)
    text_stream = io.TextIOWrapper(
        file_object.stream, encoding='utf-8-sig', newline=''
    )
    try:
        reader = csv.DictReader(text_stream)
        original_headers = reader.fieldnames or []
        header_map = {
            header.strip().upper(): header
            for header in original_headers
            if header
        }
        aliases = {
            'BARCODE': ('BARCODE', 'ID', 'STUDENT ID', 'STUDENT_ID'),
            'NAME': ('NAME', 'STUDENT NAME', 'STUDENT_NAME', 'FULL NAME'),
            'GRADE': ('GRADE', 'YEAR LEVEL', 'YEAR_LEVEL'),
            'SECTION': ('SECTION', 'CLASS'),
            'ACCESS': ('ACCESS', 'ACCESS LEVEL', 'ACCESS_LEVEL'),
            'COLOR': ('COLOR', 'BADGE COLOR', 'BADGE_COLOR'),
            'TOPIC': ('NTFY_TOPIC', 'TOPIC', 'NOTIFICATION TOPIC', 'NOTIFICATION_TOPIC')
        }
        selected = {
            field: next(
                (header_map[name] for name in names if name in header_map),
                None
            )
            for field, names in aliases.items()
        }
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

            oversized_fields = [
                field for field in (
                    'barcode', 'name', 'grade', 'section', 'access', 'topic'
                )
                if len(values[field]) > 100
            ]
            if oversized_fields:
                errors.append(
                    f"Row {line_number}: {', '.join(oversized_fields)} "
                    'must be 100 characters or fewer.'
                )
                continue

            if not re.fullmatch(r'#[0-9a-fA-F]{6}', values['color']):
                errors.append(
                    f'Row {line_number}: color must be a valid hexadecimal color.'
                )
                continue
            records.append(values)

        headers = [
            header.strip().upper() for header in original_headers if header
        ]
        return headers, records, errors
    finally:
        try:
            text_stream.detach()
        except (ValueError, UnboundLocalError):
            pass


def preview_student_csv(file_object):
    headers, records, errors = parse_student_csv(file_object)
    preview_errors = errors[:20]
    if not records and not errors:
        preview_errors = ['The CSV must contain at least one student record.']
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
        'errors': preview_errors,
        'sample': records[:5]
    }


def import_student_csv(file_object, replace_existing=False):
    _, records, errors = parse_student_csv(file_object)
    if errors:
        raise ValueError('Fix the invalid rows before importing: ' + ' '.join(errors[:3]))
    if not records:
        raise ValueError('The CSV must contain at least one student record.')
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
    backup_database()
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

# Run cleanup and initialize the local SQLite database automatically on startup.
cleanup_old_logs(7)
initialize_database()

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
    backup_database()

def delete_student(barcode):
    with get_connection() as connection:
        connection.execute('DELETE FROM students WHERE barcode = ?', (barcode,))
    backup_database()

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
    date_str = base_name.removeprefix('logs_')
    datetime.strptime(date_str, '%Y-%m-%d')
    return get_logs_by_date(date_str)

def log_attendance(barcode):
    with get_connection() as connection:
        connection.execute('BEGIN IMMEDIATE')
        now = time.time()
        connection.execute(
            'DELETE FROM recent_scans WHERE scanned_at <= ?',
            (now - DOUBLE_SCAN_WINDOW_SECONDS,)
        )
        row = connection.execute(
            'SELECT * FROM students WHERE barcode = ?', (barcode,)
        ).fetchone()
        if row is None:
            return {'status': 'error', 'message': 'Student not found'}

        last_scan = connection.execute(
            'SELECT scanned_at FROM recent_scans WHERE barcode = ?',
            (barcode,)
        ).fetchone()
        if last_scan and now - last_scan['scanned_at'] < DOUBLE_SCAN_WINDOW_SECONDS:
            return {
                'status': 'duplicate',
                'message': 'Dual scan detected. Same ID scanned within 3 seconds.'
            }

        student = dict(row)
        existing_ids = {
            item['image_id']
            for item in connection.execute('SELECT image_id FROM attendance')
        }
        filename_id = f'{generate_unique_id(existing_ids)}.jpg'
        timestamp_str = datetime.now().strftime('%m/%d/%Y %I:%M:%S %p')

        connection.execute('''
            INSERT INTO attendance
            (timestamp, barcode, name, grade, section, access, color, image_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp_str, student['barcode'], student['name'], student['grade'],
            student['section'], student['access'], student['color'], filename_id
        ))
        connection.execute(
            '''INSERT INTO recent_scans (barcode, scanned_at)
               VALUES (?, ?)
               ON CONFLICT(barcode) DO UPDATE SET scanned_at = excluded.scanned_at''',
            (barcode, now)
        )

    backup_database()
    return {
        'status': 'success',
        'data': student,
        'image_id': filename_id
    }
