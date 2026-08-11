from flask import Flask, render_template, request, jsonify, send_file
import logger
import os
import json
import threading
import urllib.request
import base64
from datetime import datetime

app = Flask(__name__)
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, 'CVA_Database')

def get_today_folder():
    date_str = datetime.now().strftime('%Y-%m-%d')
    folder_name = f"logs_{date_str}"
    folder_path = os.path.join(DB_DIR, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    return folder_path

def load_system_settings():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {
        "camera_enabled": False,
        "parent_notifications_enabled": True,
        "office_alerts_enabled": False,
        "office_ntfy_topic": "",
        "blocked_camera_alerts_enabled": True
    }

def save_system_settings(data):
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"[Settings Save Error]: {e}")

# --- PAGE ROUTES ---

@app.route('/')
def index():
    return render_template('launchpad.html')

@app.route('/launchpad.html')
def launchpad():
    return render_template('launchpad.html')

@app.route('/manager.html')
def manager():
    return render_template('manager.html')

@app.route('/scanner.html')
def scanner():
    return render_template('scanner.html')

@app.route('/logs-manager.html')
def logs_manager():
    return render_template('logs-manager.html')


# --- API ROUTES ---

@app.route('/api/settings', methods=['GET'])
def get_settings_api():
    return jsonify(load_system_settings())

@app.route('/api/settings', methods=['POST'])
def save_settings_api():
    data = request.json or {}
    current = load_system_settings()
    current.update(data)
    save_system_settings(current)
    return jsonify({'status': 'success'})

@app.route('/api/camera/blocked', methods=['POST'])
def camera_blocked_api():
    data = request.json or {}
    image_data = data.get('image', '').strip()

    if image_data:
        try:
            folder = get_today_folder()
            import string, random
            chars = string.ascii_letters + string.digits
            rand_id = ''.join(random.choices(chars, k=6))
            filename = f"BLOCKED_{rand_id}.jpg"
            file_path = os.path.join(folder, filename)

            if ',' in image_data:
                _, encoded = image_data.split(',', 1)
            else:
                encoded = image_data

            image_bytes = base64.b64decode(encoded)
            with open(file_path, 'wb') as fh:
                fh.write(image_bytes)
        except Exception as e:
            print(f"[Blocked Camera Photo Save Error]: {e}")

    settings = load_system_settings()
    if settings.get('office_alerts_enabled') and settings.get('blocked_camera_alerts_enabled'):
        topic = settings.get('office_ntfy_topic', '').strip()
        if topic:
            url = f"https://ntfy.sh/{topic}"
            message = "Scanner camera blocked or not working, please check the camera"
            def _push():
                try:
                    req = urllib.request.Request(
                        url,
                        data=message.encode('utf-8'),
                        headers={
                            "Title": "CVA Camera Alert",
                            "Priority": "high",
                            "Tags": "warning,camera"
                        }
                    )
                    urllib.request.urlopen(req, timeout=5)
                except Exception as e:
                    print(f"[ntfy Office Error]: {e}")
            threading.Thread(target=_push, daemon=True).start()
    return jsonify({'status': 'alert_dispatched'})

@app.route('/api/data', methods=['GET'])
def get_data():
    students_dict = logger.get_all_students()
    rows = []
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
    return jsonify(rows)

@app.route('/api/logs/list', methods=['GET'])
def api_logs_list():
    files = logger.get_available_log_files()
    return jsonify(files)

@app.route('/api/logs/today', methods=['GET'])
def api_logs_today():
    logs = logger.get_todays_logs_raw()
    return jsonify(logs)

@app.route('/api/logs/view', methods=['GET'])
def api_logs_view():
    filename = request.args.get('file', '').strip()
    logs = logger.get_logs_by_filename_raw(filename)
    return jsonify(logs)

@app.route('/api/logs/snapshot', methods=['GET'])
def get_log_snapshot():
    date_str = request.args.get('date', '').strip()
    image_id = request.args.get('id', '').strip()

    if not date_str or date_str.lower() == 'today':
        date_str = datetime.now().strftime('%Y-%m-%d')

    folder_path = os.path.join(DB_DIR, f"logs_{date_str}")
    if not os.path.exists(folder_path):
        return jsonify({'status': 'error', 'message': 'Log folder not found'}), 404

    file_path = os.path.join(folder_path, image_id)
    if os.path.exists(file_path):
        return send_file(file_path, mimetype='image/jpeg')

    return jsonify({'status': 'error', 'message': 'Snapshot not found'}), 404

@app.route('/api/save_student', methods=['POST'])
def save_student_api():
    data = request.json or {}
    b = data.get('b', '').strip()
    n = data.get('n', '').strip()
    g = data.get('g', '').strip()
    s = data.get('s', '').strip()
    a = data.get('a', 'REGULAR').strip()
    c = data.get('c', '#059669').strip()
    t = data.get('t', 'None').strip()

    if not b or not n:
        return jsonify({'status': 'error', 'message': 'Barcode and Name are required'}), 400

    logger.save_student(b, n, g, s, a, c, t)
    return jsonify({'status': 'success'})

@app.route('/api/delete_student', methods=['POST'])
def delete_student_api():
    data = request.json or {}
    barcode = data.get('barcode', '').strip()

    if barcode:
        logger.delete_student(barcode)
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Barcode missing'}), 400

@app.route('/api/scan', methods=['POST'])
def scan_api():
    data = request.json or {}
    barcode = data.get('barcode', '').strip()
    image_data = data.get('image', '').strip()

    if barcode:
        res = logger.log_attendance(barcode)

        if image_data and res.get('status') == 'success':
            try:
                folder = get_today_folder()
                image_id = res.get('image_id', 'unknown.jpg')
                file_path = os.path.join(folder, image_id)

                if ',' in image_data:
                    _, encoded = image_data.split(',', 1)
                else:
                    encoded = image_data

                image_bytes = base64.b64decode(encoded)
                with open(file_path, 'wb') as fh:
                    fh.write(image_bytes)
            except Exception as e:
                print(f"[Scan Photo Save Error]: {e}")

        return jsonify(res)
    return jsonify({'status': 'error', 'message': 'Barcode missing'}), 400

@app.route('/api/system/reboot', methods=['POST'])
def system_reboot():
    os.system('sudo reboot')
    return jsonify({'status': 'rebooting'})

@app.route('/api/system/shutdown', methods=['POST'])
def system_shutdown():
    os.system('sudo shutdown now')
    return jsonify({'status': 'shutting down'})

@app.route('/api/exit', methods=['POST'])
def exit_api():
    try:
        os.system("pkill -f cva_kiosk_profile")
    except Exception as e:
        print(f"[Exit Error]: {e}")

    threading.Timer(0.5, lambda: os._exit(0)).start()
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
