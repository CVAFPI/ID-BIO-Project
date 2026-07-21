import csv
import os
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify

app = Flask(__name__, static_folder='.', static_url_path='')

DB_FILE = 'data.csv'
LOGS_DIR = 'CVA-Database'
os.makedirs(LOGS_DIR, exist_ok=True)

def get_pht_time():
    pht = timezone(timedelta(hours=8))
    now = datetime.now(pht)
    return now.strftime("%m/%d/%Y %I:%M:%S %p"), now.strftime("%Y-%m-%d")

# --- STATIC PAGE ROUTES ---
@app.route('/')
@app.route('/launchpad.html')
def launchpad():
    return app.send_static_file('launchpad.html')

@app.route('/manager.html')
def manager():
    return app.send_static_file('manager.html')

@app.route('/logs-manager.html')
def logs_manager():
    return app.send_static_file('logs-manager.html')

@app.route('/scanner.html')
def scanner():
    return app.send_static_file('scanner.html')

# --- DATA API ---
@app.route('/api/data', methods=['GET'])
def get_data():
    data = []
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            data = [row for row in reader if row and row[0].strip().upper() != 'BARCODE']
    return jsonify(data)

@app.route('/api/save_student', methods=['POST'])
def save_student():
    item = request.json
    b = item.get('b', '').strip()
    n = item.get('n', '').strip()
    g = item.get('g', '').strip()
    s = item.get('s', '').strip()
    a = item.get('a', 'REGULAR').strip()
    c = item.get('c', '#059669').strip()

    rows = []
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8-sig') as f:
            rows = list(csv.reader(f))
    
    found = False
    for i, row in enumerate(rows):
        if len(row) > 0 and row[0] == b:
            rows[i] = [b, n, g, s, a, c]
            found = True
            break
    if not found:
        rows.append([b, n, g, s, a, c])
    
    with open(DB_FILE, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    return jsonify({"status": "success"})

@app.route('/api/delete_student', methods=['POST'])
def delete_student():
    barcode = request.json.get('barcode')
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8-sig') as f:
            rows = list(csv.reader(f))
        new_rows = [row for row in rows if len(row) > 0 and row[0] != barcode]
        with open(DB_FILE, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerows(new_rows)
    return jsonify({"status": "success"})

# --- SCANNER API ---
@app.route('/api/scan', methods=['POST'])
def scan_barcode():
    data = request.json
    barcode = data.get('barcode', '').strip()
    if not barcode:
        return jsonify({"status": "error", "message": "Empty barcode"})

    # Interceptors
    if barcode == 'CD=CLOSEBARCODESYS96%&@CVAFPI':
        os.system('pkill -f "cva-kiosk-profile"')
        os._exit(0)
    elif barcode == 'CD=EMERSHUTDOWNSYSSU62#9CVAFPI':
        os.system('sudo shutdown now')
        return jsonify({"status": "command", "action": "shutdown"})
    elif barcode == 'CD=RETURNTOMNSYS8(*CVAFPI':
        return jsonify({"status": "command", "action": "menu"})

    barcode_upper = barcode.upper()
    timestamp_str, date_str = get_pht_time()
    log_filename = os.path.join(LOGS_DIR, f"logs_{date_str}.csv")

    student_data = None
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) > 0 and row[0].strip().upper() == barcode_upper:
                    student_data = row
                    break

    if student_data:
        name = student_data[1] if len(student_data) > 1 else "UNKNOWN"
        grade = student_data[2] if len(student_data) > 2 else "N/A"
        section = student_data[3] if len(student_data) > 3 else "N/A"
        access = student_data[4] if len(student_data) > 4 else "REGULAR"
        color = student_data[5] if len(student_data) > 5 else "#059669" # Default Green
        access_val = access.strip().upper() if access.strip() else "REGULAR"
    else:
        name = "UNKNOWN"
        grade = "N/A"
        section = "N/A"
        access_val = "DENIED"
        color = "#dc2626" # Red for Denied/Unknown

    # Append to daily log CSV: TIMESTAMP, BARCODE, NAME, GRADE, SECTION, ACCESS, COLOR
    file_exists = os.path.exists(log_filename)
    with open(log_filename, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['Timestamp', 'Barcode', 'Name', 'Grade', 'Section', 'Access', 'Color'])
        writer.writerow([timestamp_str, barcode_upper, name, grade, section, access_val, color])

    return jsonify({
        "status": "success",
        "data": {
            "timestamp": timestamp_str,
            "barcode": barcode_upper,
            "name": name,
            "grade": grade,
            "section": section,
            "access": access_val,
            "color": color
        }
    })

@app.route('/api/logs/today', methods=['GET'])
def get_today_logs():
    _, date_str = get_pht_time()
    filename = os.path.join(LOGS_DIR, f"logs_{date_str}.csv")
    data = []
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            data = [row for row in reader if row]
    return jsonify(data)

# --- SYSTEM CONTROL API ---
@app.route('/api/system', methods=['POST'])
def system_command():
    command = request.json.get('cmd')
    if command == 'shutdown':
        os.system('sudo shutdown now')
    elif command == 'reboot':
        os.system('sudo reboot')
    elif command == 'exit':
        os.system('pkill -f "cva-kiosk-profile"')
        os._exit(0)
    return jsonify({"status": "command sent"})

# --- LOGS ARCHIVE API ---
@app.route('/api/logs/list', methods=['GET'])
def list_logs():
    files = []
    if os.path.exists(LOGS_DIR):
        files = [f for f in os.listdir(LOGS_DIR) if f.startswith('logs_') and f.endswith('.csv')]
        files.sort(reverse=True) # Newest date first
    return jsonify(files)

@app.route('/api/logs/view', methods=['GET'])
def view_log():
    filename = request.args.get('file', '')
    filepath = os.path.join(LOGS_DIR, filename)
    data = []
    if filename and os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            data = [row for row in reader if row]
    return jsonify(data)
    
if __name__ == '__main__':
    app.run(port=5000, debug=True)
