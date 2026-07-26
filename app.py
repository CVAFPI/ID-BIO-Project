from flask import Flask, render_template, request, jsonify
import logger
import os
import threading

app = Flask(__name__)

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

@app.route('/api/data', methods=['GET'])
def get_data():
    students = logger.get_all_students()
    return jsonify(students)

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

@app.route('/api/logs', methods=['GET'])
@app.route('/api/get_logs', methods=['GET'])
def get_logs_api():
    filename = request.args.get('file', '').strip()
    if filename:
        logs = logger.get_logs_by_filename_raw(filename)
    else:
        logs = logger.get_todays_logs_raw()
    return jsonify(logs)

@app.route('/api/log_files', methods=['GET'])
@app.route('/api/files', methods=['GET'])
def get_log_files_api():
    files = logger.get_available_log_files()
    return jsonify(files)

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
    if barcode:
        res = logger.log_attendance(barcode)
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
        # Kills only the specific kiosk browser window, leaving other chromium windows/tabs alone
        os.system("pkill -f cva_kiosk_profile")
    except Exception as e:
        print(f"[Exit Error]: {e}")

    # Shuts down the local Flask server gracefully after sending response
    threading.Timer(0.5, lambda: os._exit(0)).start()
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
