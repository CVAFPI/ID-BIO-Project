from flask import Flask, render_template, request, jsonify, send_file
import logger
import csv
import os
import json
import hashlib
import hmac
import logging
import secrets
import tempfile
import subprocess
import threading
import urllib.request
import base64
import re
import shutil
import sys
from datetime import datetime
from urllib.parse import quote
from werkzeug.exceptions import RequestEntityTooLarge

APP_VERSION = "2.1.1"
MAX_REQUEST_SIZE = 10 * 1024 * 1024
SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.environ.get('CVAFPI_DATA_DIR', SOURCE_DIR)
RESOURCE_DIR = getattr(sys, '_MEIPASS', SOURCE_DIR)
CONTROL_TOKEN = secrets.token_urlsafe(32)
app_logger = logging.getLogger(__name__)
app = Flask(
    __name__,
    template_folder=os.path.join(RESOURCE_DIR, 'templates'),
    static_folder=os.path.join(RESOURCE_DIR, 'static')
)
app.config['MAX_CONTENT_LENGTH'] = MAX_REQUEST_SIZE
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
DB_DIR = os.path.join(BASE_DIR, 'CVA_Database')
CUSTOM_LOGO = os.path.join(BASE_DIR, 'static', 'custom-logo.png')
os.makedirs(os.path.dirname(CUSTOM_LOGO), exist_ok=True)
PACKAGED_LOGO = os.path.join(app.static_folder, 'custom-logo.png')
if os.path.abspath(CUSTOM_LOGO) != os.path.abspath(PACKAGED_LOGO) and os.path.exists(CUSTOM_LOGO):
    shutil.copyfile(CUSTOM_LOGO, PACKAGED_LOGO)
DEFAULT_SETTINGS = {
    "camera_enabled": False,
    "parent_notifications_enabled": True,
    "office_alerts_enabled": False,
    "office_ntfy_topic": "",
    "blocked_camera_alerts_enabled": True,
    "institution_name": "Christian Vision Academy Foundation Inc.",
    "notification_topic_prefix": "",
    "theme": "night",
    "accent_color": "#2563eb",
    "pin_hash": "",
    "pin_salt": "",
    "security_question": "",
    "security_answer_hash": "",
    "security_answer_salt": "",
    "close_kiosk_barcode": "CD=CLOSEBARCODESYS96%&@CVAFPI",
    "shutdown_barcode": "CD=EMERSHUTDOWNSYSSU62#9CVAFPI",
    "launchpad_barcode": "CD=RETURNTOMNSYS8(*CVAFPI",
    "database_manager_barcode": "DataManagerCVAFPI8%/?",
    "log_manager_barcode": "LogManagerCVAFPI34#%",
    "settings_barcode": "SettingsCVAFPI8&5?"
}
PRIVATE_SETTING_KEYS = {
    'pin_hash', 'pin_salt', 'security_answer_hash', 'security_answer_salt'
}
PUBLIC_SETTINGS = set(DEFAULT_SETTINGS) - PRIVATE_SETTING_KEYS
PASSCODE_PATTERN = re.compile(r'^\S{4,12}$')
VALID_THEMES = {'night', 'light', 'grassy', 'ocean', 'sunset'}

@app.context_processor
def inject_app_version():
    return {
        'app_version': APP_VERSION,
        'platform_name': 'Windows 11',
        'control_token': CONTROL_TOKEN
    }


@app.errorhandler(RequestEntityTooLarge)
def request_too_large(_error):
    return jsonify({'status': 'error', 'message': 'Upload is too large.'}), 413


@app.before_request
def require_control_token_for_mutations():
    if request.method == 'POST' and not _control_request_authorized():
        return jsonify({'status': 'error', 'message': 'Control token is missing or invalid.'}), 403


def get_today_folder():
    date_str = datetime.now().strftime('%Y-%m-%d')
    folder_name = f"logs_{date_str}"
    folder_path = os.path.join(DB_DIR, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    return folder_path


def hash_secret(value, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        'sha256', value.encode('utf-8'), salt.encode('utf-8'), 200000
    )
    return salt, digest.hex()


def secret_matches(value, salt, expected_hash):
    if not value or not salt or not expected_hash:
        return False
    _, actual_hash = hash_secret(value, salt)
    return hmac.compare_digest(actual_hash, expected_hash)


def pin_is_configured(settings=None):
    settings = settings or load_system_settings()
    return bool(settings.get('pin_hash') and settings.get('pin_salt'))


def verify_pin(pin, settings=None):
    settings = settings or load_system_settings()
    return secret_matches(
        str(pin or '').strip(), settings.get('pin_salt'), settings.get('pin_hash')
    )


def require_admin_pin(action, data=None):
    if data is None:
        data = request.get_json(silent=True) or request.form
    if not hasattr(data, 'get'):
        data = {}
    settings = load_system_settings()
    if not pin_is_configured(settings):
        logger.record_event(
            'security_error',
            f'Blocked attempt to {action} because no passcode is configured.'
        )
        return jsonify({
            'status': 'error',
            'message': 'Configure an administrator passcode in System Settings first.'
        }), 403
    if not verify_pin(data.get('pin'), settings):
        logger.record_event(
            'security_error', f'Invalid passcode while attempting to {action}.'
        )
        return jsonify({'status': 'error', 'message': 'Invalid passcode.'}), 401
    return None


def dispatch_parent_notification(student, timestamp):
    settings = load_system_settings()
    if not settings.get('parent_notifications_enabled'):
        return
    topic = str(student.get('topic') or '').strip()
    if not topic or topic.lower() == 'none':
        return

    url = f'https://ntfy.sh/{quote(topic, safe="")}'
    message = f"{student.get('name', 'Student')} checked in at {timestamp}."

    def send():
        try:
            req = urllib.request.Request(
                url,
                data=message.encode('utf-8'),
                headers={
                    'Title': 'CVA Student Attendance',
                    'Priority': 'default',
                    'Tags': 'school,attendance'
                }
            )
            with urllib.request.urlopen(req, timeout=5):
                pass
        except Exception:
            app_logger.exception('Unable to send parent attendance notification.')

    threading.Thread(target=send, daemon=True).start()

def load_system_settings():
    settings = dict(DEFAULT_SETTINGS)
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                stored_settings = json.load(f)
            if not isinstance(stored_settings, dict):
                raise ValueError('Settings file must contain a JSON object.')
            settings.update(stored_settings)
        except (OSError, json.JSONDecodeError, ValueError):
            app_logger.exception('Unable to load settings from %s', SETTINGS_FILE)
    if not isinstance(settings.get('theme'), str) or settings['theme'] not in VALID_THEMES:
        settings['theme'] = DEFAULT_SETTINGS['theme']
    if not isinstance(settings.get('accent_color'), str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', settings['accent_color']):
        settings['accent_color'] = DEFAULT_SETTINGS['accent_color']
    for key in ('camera_enabled', 'parent_notifications_enabled', 'office_alerts_enabled', 'blocked_camera_alerts_enabled'):
        if not isinstance(settings.get(key), bool):
            settings[key] = DEFAULT_SETTINGS[key]
    for key, default in (
        ('institution_name', DEFAULT_SETTINGS['institution_name']),
        ('office_ntfy_topic', DEFAULT_SETTINGS['office_ntfy_topic']),
        ('notification_topic_prefix', DEFAULT_SETTINGS['notification_topic_prefix'])
    ):
        if not isinstance(settings.get(key), str):
            settings[key] = default
    settings['institution_name'] = settings['institution_name'].strip()[:100]
    settings['office_ntfy_topic'] = settings['office_ntfy_topic'].strip()[:256]
    settings['notification_topic_prefix'] = settings['notification_topic_prefix'].strip().upper()
    if settings['notification_topic_prefix'] and not re.fullmatch(
        r'[A-Z0-9_-]{1,24}', settings['notification_topic_prefix']
    ):
        settings['notification_topic_prefix'] = ''
    for key in ('security_question', 'pin_hash', 'pin_salt', 'security_answer_hash', 'security_answer_salt'):
        if not isinstance(settings.get(key), str):
            settings[key] = ''
    for key in (
        'close_kiosk_barcode', 'shutdown_barcode', 'launchpad_barcode',
        'database_manager_barcode', 'log_manager_barcode', 'settings_barcode'
    ):
        if not isinstance(settings.get(key), str):
            settings[key] = DEFAULT_SETTINGS[key]
        settings[key] = settings[key].strip()[:100]
    return settings

def save_system_settings(data):
    data = dict(data)
    if not isinstance(data.get('theme'), str) or data['theme'] not in VALID_THEMES:
        data['theme'] = 'night'
    if not isinstance(data.get('accent_color'), str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', data['accent_color']):
        data['accent_color'] = DEFAULT_SETTINGS['accent_color']
    data['institution_name'] = str(data.get('institution_name', DEFAULT_SETTINGS['institution_name'])).strip()[:100]
    for key in ('camera_enabled', 'parent_notifications_enabled', 'office_alerts_enabled', 'blocked_camera_alerts_enabled'):
        if not isinstance(data.get(key), bool):
            data[key] = DEFAULT_SETTINGS[key]
    data['office_ntfy_topic'] = str(data.get('office_ntfy_topic', '')).strip()[:256]
    safe_data = {key: data.get(key, DEFAULT_SETTINGS[key]) for key in DEFAULT_SETTINGS}
    for key in (
        'close_kiosk_barcode', 'shutdown_barcode', 'launchpad_barcode',
        'database_manager_barcode', 'log_manager_barcode', 'settings_barcode'
    ):
        safe_data[key] = str(safe_data[key]).strip()[:100]
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w',
            encoding='utf-8',
            dir=BASE_DIR,
            delete=False
        ) as f:
            temp_path = f.name
            json.dump({**load_system_settings(), **safe_data}, f, indent=4)
        os.replace(temp_path, SETTINGS_FILE)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

@app.context_processor
def inject_customization():
    settings = load_system_settings()
    prefix = settings['notification_topic_prefix'] or derive_notification_topic_prefix(
        settings['institution_name']
    )
    return {
        'institution_name': settings['institution_name'],
        'theme': settings['theme'],
        'accent_color': settings['accent_color'],
        'logo_url': '/static/custom-logo.png' if os.path.exists(CUSTOM_LOGO) else '/static/CVAFPI-LOGO.png',
        'notification_topic_prefix': prefix
    }

def derive_notification_topic_prefix(institution_name):
    words = re.findall(r'[A-Za-z0-9]+', str(institution_name).upper())
    if len(words) == 1:
        return words[0][:3] or 'CVA'
    return ''.join(word[0] for word in words)[:3] or 'CVA'

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

@app.route('/audit-manager.html')
def audit_manager():
    return render_template('audit-manager.html')

@app.route('/migration')
@app.route('/migration.html')
def migration():
    return render_template('migration.html')

@app.route('/jsbarcode.js')
def jsbarcode_library():
    return send_file(
        os.path.join(app.static_folder, 'JsBarcode.all.min.js'),
        mimetype='application/javascript'
    )


# --- API ROUTES ---

@app.route('/api/settings', methods=['GET'])
def get_settings_api():
    settings = load_system_settings()
    return jsonify({key: settings[key] for key in PUBLIC_SETTINGS})

@app.route('/api/ping', methods=['GET'])
def api_ping():
    return jsonify({'status': 'ok'})

@app.route('/api/settings', methods=['POST'])
def save_settings_api():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'status': 'error', 'message': 'Settings must be a JSON object.'}), 400
    current = load_system_settings()
    if pin_is_configured(current) and not verify_pin(data.get('current_pin'), current):
        logger.record_event('security_error', 'Settings save rejected because the current passcode was invalid.')
        return jsonify({'status': 'error', 'message': 'Current passcode is required.'}), 401

    new_pin = str(data.get('new_pin', '')).strip()
    question = str(data.get('security_question', current.get('security_question', ''))).strip()[:200]
    answer = str(data.get('security_answer', '')).strip().lower()
    notification_prefix = str(data.get(
        'notification_topic_prefix',
        current.get('notification_topic_prefix', '')
    )).strip().upper()
    if notification_prefix and not re.fullmatch(r'[A-Z0-9_-]{1,24}', notification_prefix):
        return jsonify({
            'status': 'error',
            'message': 'Notification topic prefix must contain 1–24 letters, numbers, underscores, or hyphens.'
        }), 400
    security_changed = bool(new_pin) or question != current.get('security_question', '') or bool(answer)

    if not pin_is_configured(current) and not new_pin:
        return jsonify({'status': 'error', 'message': 'Set an administrator passcode before saving settings.'}), 400
    if new_pin and not PASSCODE_PATTERN.fullmatch(new_pin):
        return jsonify({'status': 'error', 'message': 'Passcode must be 4 to 12 characters with no spaces.'}), 400
    if security_changed and (not new_pin or not question or not answer):
        return jsonify({'status': 'error', 'message': 'A new passcode, recovery question, and answer are all required.'}), 400

    current.update({
        key: data[key]
        for key in PUBLIC_SETTINGS
        if key in data and key not in {'security_question'}
    })
    current['notification_topic_prefix'] = notification_prefix
    if security_changed:
        current['security_question'] = question
        current['pin_salt'], current['pin_hash'] = hash_secret(new_pin)
        current['security_answer_salt'], current['security_answer_hash'] = hash_secret(answer)
    try:
        save_system_settings(current)
    except (OSError, ValueError):
        app_logger.exception('Unable to save settings to %s', SETTINGS_FILE)
        return jsonify({'status': 'error', 'message': 'Settings could not be saved.'}), 500
    logger.record_event('settings_saved', 'System settings were saved.')
    return jsonify({'status': 'success', 'settings': {
        key: current[key] for key in PUBLIC_SETTINGS
    }})


@app.route('/api/security/config', methods=['GET'])
def security_config_api():
    settings = load_system_settings()
    return jsonify({
        'pin_configured': pin_is_configured(settings),
        'security_question': settings.get('security_question', '')
    })


@app.route('/api/security/recover', methods=['POST'])
def security_recover_api():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'status': 'error', 'message': 'Recovery data must be a JSON object.'}), 400
    settings = load_system_settings()
    answer = str(data.get('security_answer', '')).strip().lower()
    new_pin = str(data.get('new_pin', '')).strip()
    if not secret_matches(
        answer,
        settings.get('security_answer_salt'),
        settings.get('security_answer_hash')
    ):
        logger.record_event('security_error', 'Passcode recovery failed.')
        return jsonify({'status': 'error', 'message': 'Security answer is incorrect.'}), 401
    if not PASSCODE_PATTERN.fullmatch(new_pin):
        return jsonify({'status': 'error', 'message': 'Passcode must be 4 to 12 characters with no spaces.'}), 400

    settings['pin_salt'], settings['pin_hash'] = hash_secret(new_pin)
    try:
        save_system_settings(settings)
    except OSError:
        app_logger.exception('Unable to save recovered passcode to %s', SETTINGS_FILE)
        return jsonify({'status': 'error', 'message': 'Passcode could not be saved.'}), 500
    logger.record_event('security_recovered', 'Administrator passcode was recovered.')
    return jsonify({'status': 'success'})

@app.route('/api/branding/logo', methods=['POST'])
def upload_branding_logo():
    authorization_error = require_admin_pin('change institution branding')
    if authorization_error:
        return authorization_error
    uploaded_file = request.files.get('logo')
    if not uploaded_file or not uploaded_file.filename:
        return jsonify({'status': 'error', 'message': 'Please choose an image file.'}), 400
    try:
        from PIL import Image
        image = Image.open(uploaded_file.stream)
        if image.width > 4096 or image.height > 4096:
            return jsonify({'status': 'error', 'message': 'Logo dimensions must not exceed 4096 by 4096 pixels.'}), 400
        image.verify()
        uploaded_file.stream.seek(0)
        image = Image.open(uploaded_file.stream)
        image.thumbnail((2048, 2048))
        image.convert('RGBA').save(CUSTOM_LOGO, 'PNG', optimize=True)
        if os.path.abspath(CUSTOM_LOGO) != os.path.abspath(PACKAGED_LOGO):
            shutil.copyfile(CUSTOM_LOGO, PACKAGED_LOGO)
        logger.record_event('branding_updated', 'Institution logo was updated.')
        return jsonify({'status': 'success', 'logo_url': '/static/custom-logo.png'})
    except Exception as error:
        return jsonify({'status': 'error', 'message': f'Logo conversion failed: {error}'}), 400

@app.route('/api/migration/status', methods=['GET'])
def migration_status():
    return jsonify({'students': len(logger.get_all_students()), 'database': 'CSV'})

@app.route('/api/migration/preview', methods=['POST'])
def migration_preview():
    uploaded_file = request.files.get('file')
    if not uploaded_file or not uploaded_file.filename.lower().endswith('.csv'):
        return jsonify({'status': 'error', 'message': 'Please choose a CSV file.'}), 400
    try:
        return jsonify({'status': 'success', **logger.preview_student_csv(uploaded_file)})
    except (UnicodeDecodeError, csv.Error, ValueError) as error:
        return jsonify({'status': 'error', 'message': str(error)}), 400

@app.route('/api/migration/import', methods=['POST'])
def migration_import():
    authorization_error = require_admin_pin('import student records')
    if authorization_error:
        return authorization_error
    uploaded_file = request.files.get('file')
    replace_existing = request.form.get('replace_existing') == 'true'
    if not uploaded_file or not uploaded_file.filename.lower().endswith('.csv'):
        return jsonify({'status': 'error', 'message': 'Please choose a CSV file.'}), 400
    try:
        result = logger.import_student_csv(uploaded_file, replace_existing)
        logger.record_event(
            'database_import',
            f"Imported {result['imported']} student records ({result['mode']} mode)."
        )
        return jsonify({'status': 'success', **result, 'students': len(logger.get_all_students())})
    except (UnicodeDecodeError, csv.Error, ValueError) as error:
        return jsonify({'status': 'error', 'message': str(error)}), 400

@app.route('/api/camera/blocked', methods=['POST'])
def camera_blocked_api():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get('image', ''), str):
        return jsonify({'status': 'error', 'message': 'Camera alert data is invalid.'}), 400
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

            image_bytes = base64.b64decode(encoded, validate=True)
            with open(file_path, 'wb') as fh:
                fh.write(image_bytes)
            snapshot_details = f'snapshot_date={datetime.now():%Y-%m-%d};snapshot_id={filename}'
        except (OSError, ValueError):
            app_logger.exception('Unable to save blocked-camera snapshot.')
            snapshot_details = ''
    else:
        snapshot_details = ''

    settings = load_system_settings()
    logger.record_event(
        'camera_blocked',
        'Scanner camera is blocked or appears unavailable.',
        details=snapshot_details
    )
    if settings.get('office_alerts_enabled') and settings.get('blocked_camera_alerts_enabled'):
        topic = settings.get('office_ntfy_topic', '').strip()
        if topic:
            url = f"https://ntfy.sh/{quote(topic, safe='')}"
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
                    with urllib.request.urlopen(req, timeout=5):
                        pass
                except Exception:
                    app_logger.exception('Unable to send office camera alert.')
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
    try:
        logs = logger.get_logs_by_filename_raw(filename)
    except ValueError as error:
        return jsonify({'status': 'error', 'message': str(error)}), 400
    return jsonify(logs)

@app.route('/api/audit/events', methods=['POST'])
def audit_events_api():
    authorization_error = require_admin_pin('view audit events')
    if authorization_error:
        return authorization_error
    try:
        return jsonify(logger.get_audit_events())
    except (OSError, csv.Error):
        app_logger.exception('Unable to read the CSV audit trail.')
        return jsonify({'status': 'error', 'message': 'Audit events could not be loaded.'}), 500

@app.route('/api/logs/snapshot', methods=['GET'])
def get_log_snapshot():
    date_str = request.args.get('date', '').strip()
    image_id = request.args.get('id', '').strip()

    if not date_str or date_str.lower() == 'today':
        date_str = datetime.now().strftime('%Y-%m-%d')
    try:
        parsed_date = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid log date.'}), 400
    if parsed_date.strftime('%Y-%m-%d') != date_str or not re.fullmatch(r'(?:[A-Za-z0-9]{6}|BLOCKED_[A-Za-z0-9]{6})\.jpg', image_id):
        return jsonify({'status': 'error', 'message': 'Invalid snapshot identifier.'}), 400

    folder_path = os.path.join(DB_DIR, f"logs_{date_str}")
    if not os.path.exists(folder_path):
        return jsonify({'status': 'error', 'message': 'Log folder not found'}), 404

    file_path = os.path.join(folder_path, image_id)
    if os.path.exists(file_path):
        return send_file(file_path, mimetype='image/jpeg')

    return jsonify({'status': 'error', 'message': 'Snapshot not found'}), 404

@app.route('/api/save_student', methods=['POST'])
def save_student_api():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'status': 'error', 'message': 'Student data must be a JSON object.'}), 400
    authorization_error = require_admin_pin('save student records', data)
    if authorization_error:
        return authorization_error
    values = {key: data.get(key, default) for key, default in {
        'b': '', 'n': '', 'g': '', 's': '', 'a': 'REGULAR', 'c': '#059669', 't': 'None'
    }.items()}
    if any(not isinstance(value, str) for value in values.values()):
        return jsonify({'status': 'error', 'message': 'Student fields must be text.'}), 400
    b, n, g, s, a, c, t = (values[key].strip() for key in ('b', 'n', 'g', 's', 'a', 'c', 't'))

    identity_error = logger.validate_student_identity(b, n)
    if identity_error:
        return jsonify({'status': 'error', 'message': identity_error}), 400
    if not re.fullmatch(r'#[0-9a-fA-F]{6}', c):
        return jsonify({'status': 'error', 'message': 'Color must be a six-digit hex value.'}), 400

    logger.save_student(b, n, g, s, a, c, t)
    logger.record_event('student_saved', 'Student record added or updated.', b)
    return jsonify({'status': 'success'})

@app.route('/api/delete_student', methods=['POST'])
def delete_student_api():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get('barcode'), str):
        return jsonify({'status': 'error', 'message': 'Barcode is required.'}), 400
    authorization_error = require_admin_pin('delete student records', data)
    if authorization_error:
        return authorization_error
    barcode = data['barcode'].strip()

    if barcode:
        logger.delete_student(barcode)
        logger.record_event('student_deleted', 'Student record deleted.', barcode)
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Barcode missing'}), 400

@app.route('/api/scan', methods=['POST'])
def scan_api():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get('barcode', ''), str):
        return jsonify({'status': 'error', 'message': 'Barcode must be text.'}), 400
    image_data = data.get('image')
    if image_data is not None and not isinstance(image_data, str):
        return jsonify({'status': 'error', 'message': 'Scan data must contain text fields.'}), 400
    barcode = data.get('barcode', '').strip()
    image_data = (image_data or '').strip()

    if barcode:
        settings = load_system_settings()
        command_map = {
            settings.get('close_kiosk_barcode'): 'close_kiosk',
            settings.get('shutdown_barcode'): 'shutdown',
            settings.get('launchpad_barcode'): 'launchpad',
            settings.get('database_manager_barcode'): 'database_manager',
            settings.get('log_manager_barcode'): 'log_manager',
            settings.get('settings_barcode'): 'settings'
        }
        command = command_map.get(barcode)
        if command:
            return jsonify({'status': 'system_command', 'command': command})

        res = logger.log_attendance(barcode)
        if res.get('status') == 'success':
            timestamp = res['data']['timestamp']
            dispatch_parent_notification(res.get('data', {}), timestamp)
            logger.record_event('scan_logged', 'Attendance scan logged.', barcode)
        elif res.get('status') == 'duplicate':
            logger.record_event(
                'dual_scan',
                res.get('message', 'Duplicate attendance scan was rejected.'),
                barcode
            )
        else:
            logger.record_event(
                'invalid_scan',
                res.get('message', 'Unknown barcode.'),
                barcode
            )

        if image_data and res.get('status') == 'success':
            try:
                folder = get_today_folder()
                image_id = res.get('image_id', 'unknown.jpg')
                file_path = os.path.join(folder, image_id)

                if ',' in image_data:
                    _, encoded = image_data.split(',', 1)
                else:
                    encoded = image_data

                image_bytes = base64.b64decode(encoded, validate=True)
                with open(file_path, 'wb') as fh:
                    fh.write(image_bytes)
            except (OSError, ValueError) as error:
                app_logger.exception('Unable to save scan snapshot: %s', error)

        return jsonify(res)
    return jsonify({'status': 'error', 'message': 'Barcode missing'}), 400


@app.route('/api/system/command', methods=['POST'])
def system_command_api():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get('command'), str):
        return jsonify({'status': 'error', 'message': 'System command is invalid.'}), 400
    command = data['command']
    allowed_commands = {
        'launchpad', 'database_manager', 'log_manager', 'settings',
        'close_kiosk', 'shutdown'
    }
    if command not in allowed_commands:
        return jsonify({'status': 'error', 'message': 'System command is not supported.'}), 400
    authorization_error = require_admin_pin(f'run system command {command}', data)
    if authorization_error:
        return authorization_error

    if command == 'close_kiosk':
        browser = app.config.get('KIOSK_BROWSER_PROCESS')
        if browser is not None and browser.poll() is None:
            threading.Timer(0.25, browser.terminate).start()
        logger.record_event('system_command', 'Kiosk was closed.')
        return jsonify({'status': 'success', 'action': 'close_kiosk'})
    if command == 'shutdown':
        try:
            subprocess.Popen(['shutdown', '/s', '/t', '0'])
        except OSError:
            app_logger.exception('Unable to request system shutdown.')
            return jsonify({'status': 'error', 'message': 'System shutdown could not be started.'}), 500
        logger.record_event('system_command', 'System shutdown was requested.')
        return jsonify({'status': 'success', 'action': 'shutdown'})

    destinations = {
        'launchpad': '/launchpad.html',
        'database_manager': '/manager.html',
        'log_manager': '/logs-manager.html',
        'settings': '/launchpad.html?openSettings=1'
    }
    logger.record_event('system_command', f'Opened {command.replace("_", " ")}.')
    return jsonify({'status': 'success', 'action': destinations[command]})

def _control_request_authorized():
    token = request.headers.get('X-CVAFPI-Control-Token', '')
    return bool(token) and hmac.compare_digest(token, CONTROL_TOKEN)


@app.route('/api/system/reboot', methods=['POST'])
def system_reboot():
    data = request.get_json(silent=True) or {}
    authorization_error = require_admin_pin('restart the system', data)
    if authorization_error:
        return authorization_error
    try:
        subprocess.Popen(['shutdown', '/r', '/t', '0'])
    except OSError:
        app_logger.exception('Unable to request system reboot.')
        return jsonify({'status': 'error', 'message': 'System reboot could not be started.'}), 500
    logger.record_event('system_command', 'System restart was requested.')
    return jsonify({'status': 'rebooting'})

@app.route('/api/system/shutdown', methods=['POST'])
def system_shutdown():
    data = request.get_json(silent=True) or {}
    authorization_error = require_admin_pin('shut down the system', data)
    if authorization_error:
        return authorization_error
    try:
        subprocess.Popen(['shutdown', '/s', '/t', '0'])
    except OSError:
        app_logger.exception('Unable to request system shutdown.')
        return jsonify({'status': 'error', 'message': 'System shutdown could not be started.'}), 500
    logger.record_event('system_command', 'System shutdown was requested.')
    return jsonify({'status': 'shutting down'})

@app.route('/api/exit', methods=['POST'])
def exit_api():
    data = request.get_json(silent=True) or {}
    authorization_error = require_admin_pin('close the kiosk', data)
    if authorization_error:
        return authorization_error
    browser = app.config.get('KIOSK_BROWSER_PROCESS')
    if browser is not None and browser.poll() is None:
        threading.Timer(0.25, browser.terminate).start()
    logger.record_event('system_command', 'Kiosk was closed.')
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
