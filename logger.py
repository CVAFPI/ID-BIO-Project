import os
import csv
import random
import string
import shutil
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, 'CVA_Database')
DATA_CSV = os.path.join(BASE_DIR, 'data.csv')
BACKUP_CSV = os.path.join(BASE_DIR, 'backup-data.csv')

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
    if not os.path.exists(DATA_CSV):
        return students

    try:
        with open(DATA_CSV, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or len(row) < 1:
                    continue
                # Skip header row safely
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
    students = get_all_students()
    if barcode not in students:
        return {'status': 'error', 'message': 'Student not found'}

    student = students[barcode]
    file_path = get_todays_log_filepath()

    existing_ids = set()
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) > 7:
                    existing_ids.add(row[7])

    image_id = generate_unique_id(existing_ids)
    filename_id = f"{image_id}.jpg"

    now = datetime.now()
    timestamp_str = now.strftime('%m/%d/%Y %I:%M:%S %p')

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
        writer = csv.writer(f)
        writer.writerow(row_data)

    return {
        'status': 'success',
        'data': student,
        'image_id': filename_id
    }
