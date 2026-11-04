
from flask import Flask, render_template, request, jsonify, send_file
import logger
import csv
import os
import json
import threading
import urllib.request
import base64
import re
import hashlib
import hmac
import secrets
import shutil
from datetime import datetime
import sys
from urllib.parse import quote

SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.environ.get('CVAFPI_DATA_DIR', SOURCE_DIR))
RESOURCE_DIR = getattr(sys, '_MEIPASS', SOURCE_DIR)

app = Flask(
    __name__,
    template_folder=os.path.join(RESOURCE_DIR, 'templates'),
    static_folder=os.path.join(RESOURCE_DIR, 'static')
)

DB_DIR = os.path.join(BASE_DIR, 'CVA_Database')
CUSTOM_LOGO = os.path.join(BASE_DIR, 'static', 'custom-logo.png')
os.makedirs(os.path.dirname(CUSTOM_LOGO), exist_ok=True)

PACKAGED_LOGO = os.path.join(app.static_folder, 'custom-logo.png')
if (
    os.path.abspath(CUSTOM_LOGO) != os.path.abspath(PACKAGED_LOGO)
    and os.path.exists(CUSTOM_LOGO)
):
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
    "accent_color": "#4da3ff",
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

PUBLIC_SETTINGS = {
    key for key in DEFAULT_SETTINGS
    if key not in {
        'pin_hash',
        'pin_salt',
        'security_answer_hash',
        'security_answer_salt'
    }
}

PASSCODE_PATTERN = re.compile(r'^\S{4,12}$')
BOOLEAN_SETTING_KEYS = (
    'camera_enabled',
    'parent_notifications_enabled',
    'office_alerts_enabled',
    'blocked_camera_alerts_enabled'
)
VALID_THEMES = {'night', 'light', 'grassy', 'ocean', 'sunset'}


def hash_secret(value, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        'sha256',
        value.encode('utf-8'),
        salt.encode('utf-8'),
        200000
    )
    return salt, digest.hex()


def secret_matches(value, salt, expected_hash):
    if not value or not salt or not expected_hash:
        return False
    _, actual_hash = hash_secret(value, salt)
    return hmac.compare_digest(actual_hash, expected_hash)


def dispatch_parent_notification(student, timestamp, settings):
    if not settings.get('parent_notifications_enabled'):
        return

    topic = str(student.get('topic') or '').strip()
    if not topic or topic.lower() == 'none':
        return

    topic_path = quote(topic, safe='')
    url = f'https://ntfy.sh/{topic_path}'
    message = f"{student.get('name', 'Student')} checked in at {timestamp}."

    def _push():
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
            urllib.request.urlopen(req, timeout=5)
        except Exception as error:
            print(f'[ntfy Parent Error]: {error}')

    threading.Thread(target=_push, daemon=True).start()


def pin_is_configured(settings=None):
    settings = settings or load_system_settings()
    return bool(settings.get('pin_hash') and settings.get('pin_salt'))


def verify_pin(pin, settings=None):
    settings = settings or load_system_settings()
    return secret_matches(
        str(pin or '').strip(),
        settings.get('pin_salt'),
        settings.get('pin_hash')
    )


def protected_response(action='perform this action'):
    data = request.get_json(silent=True) or request.form
    settings = load_system_settings()

    if not pin_is_configured(settings):
        logger.record_event(
            'security_error',
            f'Blocked attempt to {action} because no passcode is configured.'
        )
        return jsonify({
            'status': 'error',
            'message': 'A security passcode must be configured first.'
        }), 403

    if not verify_pin(data.get('pin'), settings):
        logger.record_event(
            'security_error',
            f'Invalid passcode while attempting to {action}.'
        )
        return jsonify({
            'status': 'error',
            'message': f'Invalid passcode. Cannot {action}.'
        }), 401

    return None


def public_settings(settings):
    return {
        key: settings.get(key, DEFAULT_SETTINGS[key])
        for key in PUBLIC_SETTINGS
    }


def derive_notification_topic_prefix(institution_name):
    words = re.findall(
        r"[A-Za-z0-9]+",
        str(institution_name or "").upper()
    )
    initials = ''.join(word[0] for word in words)

    if len(words) == 1:
        return words[0][:3] or 'CVA'

    return initials[:3] or 'CVA'


def get_today_folder():
    date_str = datetime.now().strftime('%Y-%m-%d')
    folder_name = f"logs_{date_str}"
    folder_path = os.path.join(DB_DIR, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    return folder_path


# ----------------------------------------------------------------------
# SETTINGS
# SQLite database: CVA_Database/cva.sqlite3
# Settings table: app_settings
# settings.json is no longer read or written.
# ----------------------------------------------------------------------

def load_system_settings():
    """Load settings exclusively from SQLite."""
    settings = dict(DEFAULT_SETTINGS)
    stored_settings = logger.get_app_settings()
    legacy_settings_path = os.path.join(BASE_DIR, 'settings.json')
    missing_keys = set(DEFAULT_SETTINGS).difference(stored_settings)

    if missing_keys and os.path.isfile(legacy_settings_path):
        with open(legacy_settings_path, 'r', encoding='utf-8') as settings_file:
            legacy_settings = json.load(settings_file)
        if not isinstance(legacy_settings, dict):
            raise ValueError('Legacy settings file must contain a JSON object.')

        migrated_settings = {
            key: value
            for key, value in legacy_settings.items()
            if key in missing_keys
            and key in DEFAULT_SETTINGS
        }
        if migrated_settings:
            logger.save_app_settings(migrated_settings)
            logger.record_event(
                'settings_migrated',
                f'Migrated {len(migrated_settings)} legacy settings to SQLite.'
            )
            stored_settings.update(migrated_settings)

    # SQLite stores values as text. Convert known boolean values.
    for key in BOOLEAN_SETTING_KEYS:
        if key in stored_settings:
            stored_settings[key] = (
                str(stored_settings[key]).strip().lower()
                in {'1', 'true', 'yes', 'on'}
            )

    # Ignore unknown keys so unrelated database entries cannot affect settings.
    settings.update({
        key: value
        for key, value in stored_settings.items()
        if key in DEFAULT_SETTINGS
    })

    for key in BOOLEAN_SETTING_KEYS:
        value = settings.get(key, False)
        if isinstance(value, str):
            settings[key] = value.strip().lower() in {
                '1', 'true', 'yes', 'on'
            }
        else:
            settings[key] = bool(value)

    if settings.get('theme') not in VALID_THEMES:
        settings['theme'] = DEFAULT_SETTINGS['theme']

    if not re.fullmatch(
        r'#[0-9a-fA-F]{6}',
        str(settings.get('accent_color', ''))
    ):
        settings['accent_color'] = DEFAULT_SETTINGS['accent_color']

    return settings


def save_system_settings(data):
    """Validate and save settings to SQLite only.

    Database errors intentionally propagate to the API route so the client
    receives a JSON error instead of silently receiving a false success.
    """
    normalized = dict(data)

    for key in BOOLEAN_SETTING_KEYS:
        if key in normalized:
            value = normalized[key]
            if isinstance(value, str):
                normalized[key] = value.strip().lower() in {
                    '1', 'true', 'yes', 'on'
                }
            else:
                normalized[key] = bool(value)

    if (
        'theme' in normalized
        and normalized['theme'] not in VALID_THEMES
    ):
        normalized['theme'] = DEFAULT_SETTINGS['theme']

    if (
        'accent_color' in normalized
        and not re.fullmatch(
            r'#[0-9a-fA-F]{6}',
            str(normalized['accent_color'])
        )
    ):
        normalized['accent_color'] = DEFAULT_SETTINGS['accent_color']

    if 'institution_name' in normalized:
        normalized['institution_name'] = (
            str(normalized['institution_name']).strip()[:100]
        )

    if 'notification_topic_prefix' in normalized:
        normalized['notification_topic_prefix'] = (
            str(normalized['notification_topic_prefix']).strip()[:32]
        )

    string_limits = {
        'office_ntfy_topic': 200,
        'close_kiosk_barcode': 100,
        'shutdown_barcode': 100,
        'launchpad_barcode': 100,
        'database_manager_barcode': 100,
        'log_manager_barcode': 100,
        'settings_barcode': 100,
        'security_question': 200
    }

    for key, limit in string_limits.items():
        if key in normalized:
            normalized[key] = str(normalized[key]).strip()[:limit]

    safe_data = {
        key: normalized[key]
        for key in DEFAULT_SETTINGS
        if key in normalized
    }

    # logger.save_app_settings writes the values into SQLite.
    # Do not catch or suppress its exceptions here.
    logger.save_app_settings(safe_data)

    return load_system_settings()


@app.context_processor
def inject_branding():
    settings = load_system_settings()

    return {
        'institution_name': settings.get(
            'institution_name',
            DEFAULT_SETTINGS['institution_name']
        ),
        'notification_topic_prefix': (
            settings.get('notification_topic_prefix')
            or derive_notification_topic_prefix(
                settings.get('institution_name')
            )
        ),
        'theme': settings.get('theme', DEFAULT_SETTINGS['theme']),
        'accent_color': settings.get(
            'accent_color',
            DEFAULT_SETTINGS['accent_color']
        ),
        'logo_url': (
            '/static/custom-logo.png'
            if os.path.exists(CUSTOM_LOGO)
            else '/static/CVAFPI-LOGO.png'
        )
    }


@app.before_request
def database_startup_guard():
    if not logger.database_startup_error:
        return None

    message = logger.database_startup_error

    if request.path.startswith('/api/'):
        return jsonify({
            'status': 'error',
            'message': message
        }), 503

    return f'''<!doctype html><html><head><title>Database error</title></head>
        <body><script>alert({json.dumps(message)});</script>
        <h1>Database error</h1><p>{message}</p></body></html>''', 503


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


@app.route('/migration.html')
def migration():
    return render_template('migration.html')


# --- SETTINGS API ---

@app.route('/api/settings', methods=['GET'])
def get_settings_api():
    try:
        return jsonify(public_settings(load_system_settings()))
    except Exception:
        app.logger.exception('Failed to read settings from SQLite')
        return jsonify({
            'status': 'error',
            'message': 'Could not load settings from SQLite.'
        }), 500


@app.route('/api/settings', methods=['POST'])
def save_settings_api():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            'status': 'error',
            'message': 'Expected a JSON object.'
        }), 400

    try:
        current = load_system_settings()
    except Exception:
        app.logger.exception('Failed to read settings before saving')
        return jsonify({
            'status': 'error',
            'message': 'Could not load existing settings from SQLite.'
        }), 500

    if pin_is_configured(current) and not verify_pin(
        data.get('current_pin'),
        current
    ):
        logger.record_event(
            'security_error',
            'Settings save rejected because the current passcode was invalid.'
        )
        return jsonify({
            'status': 'error',
            'message': 'Current passcode is required.'
        }), 401

    new_pin = str(data.get('new_pin', '')).strip()

    if new_pin and not PASSCODE_PATTERN.fullmatch(new_pin):
        logger.record_event(
            'settings_error',
            'Settings save rejected because the new passcode was invalid.'
        )
        return jsonify({
            'status': 'error',
            'message': 'Passcode must be 4 to 12 characters with no spaces.'
        }), 400

    question = str(
        data.get(
            'security_question',
            current.get('security_question', '')
        )
    ).strip()[:200]

    answer = str(data.get('security_answer', '')).strip().lower()

    security_change_requested = (
        bool(new_pin)
        or bool(answer)
        or question != current.get('security_question', '')
    )

    if security_change_requested and (
        not new_pin or not question or not answer
    ):
        logger.record_event(
            'settings_error',
            'Settings save rejected because passcode recovery fields were incomplete.'
        )
        return jsonify({
            'status': 'error',
            'message': (
                'Passcode, security question, and answer are all required.'
            )
        }), 400

    # Only accept recognized public settings from the submitted request.
    current.update({
        key: data[key]
        for key in PUBLIC_SETTINGS
        if key in data
    })

    if new_pin:
        current['pin_salt'], current['pin_hash'] = hash_secret(new_pin)
        current['security_question'] = question
        (
            current['security_answer_salt'],
            current['security_answer_hash']
        ) = hash_secret(answer)

    for key in ('current_pin', 'new_pin', 'security_answer'):
        current.pop(key, None)

    try:
        saved_settings = save_system_settings(current)
    except Exception as error:
        app.logger.exception('Failed to save system settings to SQLite')
        return jsonify({
            'status': 'error',
            'message': f'Could not save settings to SQLite: {error}'
        }), 500

    logger.record_event(
        'settings_saved',
        'System settings were saved.'
    )

    return jsonify({
        'status': 'success',
        'settings': public_settings(saved_settings)
    })


@app.route('/api/security/config', methods=['GET'])
def security_config_api():
    settings = load_system_settings()

    return jsonify({
        'pin_configured': pin_is_configured(settings),
        'security_question': settings.get('security_question', '')
    })


@app.route('/api/security/recover', methods=['POST'])
def security_recover_api():
    data = request.get_json(silent=True) or {}
    settings = load_system_settings()

    answer = str(data.get('security_answer', '')).strip().lower()
    new_pin = str(data.get('new_pin', '')).strip()

    if (
        not settings.get('security_question')
        or not secret_matches(
            answer,
            settings.get('security_answer_salt'),
            settings.get('security_answer_hash')
        )
    ):
        return jsonify({
            'status': 'error',
            'message': 'Security answer is incorrect.'
        }), 401

    if not PASSCODE_PATTERN.fullmatch(new_pin):
        return jsonify({
            'status': 'error',
            'message': 'Passcode must be 4 to 12 characters with no spaces.'
        }), 400

    settings['pin_salt'], settings['pin_hash'] = hash_secret(new_pin)

    try:
        save_system_settings(settings)
    except Exception:
        app.logger.exception('Failed to save recovered passcode to SQLite')
        return jsonify({
            'status': 'error',
            'message': 'Could not save passcode to SQLite.'
        }), 500

    logger.record_event(
        'passcode_recovered',
        'The security passcode was reset using the recovery answer.'
    )
    return jsonify({'status': 'success'})


# --- BRANDING ---

@app.route('/api/branding/logo', methods=['POST'])
def upload_branding_logo():
    authorization_error = protected_response('upload the logo')
    if authorization_error:
        return authorization_error

    uploaded_file = request.files.get('logo')

    if not uploaded_file or not uploaded_file.filename:
        return jsonify({
            'status': 'error',
            'message': 'Please choose a logo image.'
        }), 400

    try:
        from PIL import Image

        image = Image.open(uploaded_file.stream)
        image.convert('RGBA').save(
            CUSTOM_LOGO,
            'PNG',
            optimize=True
        )

        if os.path.abspath(CUSTOM_LOGO) != os.path.abspath(PACKAGED_LOGO):
            shutil.copyfile(CUSTOM_LOGO, PACKAGED_LOGO)

        return jsonify({
            'status': 'success',
            'logo_url': '/static/custom-logo.png'
        })

    except Exception as error:
        return jsonify({
            'status': 'error',
            'message': f'Logo conversion failed: {error}'
        }), 400


# --- CAMERA ALERTS ---

@app.route('/api/camera/blocked', methods=['POST'])
def camera_blocked_api():
    data = request.get_json(silent=True) or {}
    image_data = str(data.get('image', '')).strip()
    snapshot_details = ''

    if image_data:
        try:
            snapshot_date = datetime.now().strftime('%Y-%m-%d')
            folder = os.path.join(DB_DIR, f'logs_{snapshot_date}')
            os.makedirs(folder, exist_ok=True)

            import string
            import random

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

            snapshot_details = (
                f'snapshot_date={snapshot_date};snapshot_id={filename}'
            )

        except Exception as error:
            app.logger.exception(
                'Blocked camera photo could not be saved'
            )

    logger.record_event(
        'camera_blocked',
        'Scanner camera is blocked or appears unavailable.',
        details=snapshot_details
    )

    settings = load_system_settings()

    if (
        settings.get('office_alerts_enabled')
        and settings.get('blocked_camera_alerts_enabled')
    ):
        topic = settings.get('office_ntfy_topic', '').strip()

        if topic:
            url = f"https://ntfy.sh/{quote(topic, safe='')}"
            message = (
                'Scanner camera blocked or not working, please check the camera'
            )

            def _push():
                try:
                    req = urllib.request.Request(
                        url,
                        data=message.encode('utf-8'),
                        headers={
                            'Title': 'CVA Camera Alert',
                            'Priority': 'high',
                            'Tags': 'warning,camera'
                        }
                    )
                    urllib.request.urlopen(req, timeout=5)
                except Exception as error:
                    print(f'[ntfy Office Error]: {error}')

            threading.Thread(target=_push, daemon=True).start()

    return jsonify({'status': 'alert_dispatched'})


# --- STUDENT DATA ---

@app.route('/api/data', methods=['GET'])
def get_data():
    students_dict = logger.get_all_students()
    rows = []

    for barcode, student in students_dict.items():
        rows.append([
            student.get('barcode', barcode),
            student.get('name', ''),
            student.get('grade', ''),
            student.get('section', ''),
            student.get('access', 'REGULAR'),
            student.get('color', '#059669'),
            student.get('topic', 'None')
        ])

    return jsonify(rows)


@app.route('/api/migration/status', methods=['GET'])
def migration_status():
    return jsonify({
        'students': len(logger.get_all_students()),
        'database': logger.DATABASE_FILE
    })


@app.route('/api/migration/preview', methods=['POST'])
def migration_preview():
    uploaded_file = request.files.get('file')

    if (
        not uploaded_file
        or not uploaded_file.filename.lower().endswith('.csv')
    ):
        return jsonify({
            'status': 'error',
            'message': 'Please choose a CSV file.'
        }), 400

    try:
        return jsonify({
            'status': 'success',
            **logger.preview_student_csv(uploaded_file)
        })
    except (UnicodeDecodeError, csv.Error, ValueError) as error:
        return jsonify({
            'status': 'error',
            'message': str(error)
        }), 400


@app.route('/api/migration/import', methods=['POST'])
def migration_import():
    authorization_error = protected_response('import student records')
    if authorization_error:
        return authorization_error

    uploaded_file = request.files.get('file')
    replace_existing = request.form.get('replace_existing') == 'true'

    if (
        not uploaded_file
        or not uploaded_file.filename.lower().endswith('.csv')
    ):
        return jsonify({
            'status': 'error',
            'message': 'Please choose a CSV file.'
        }), 400

    try:
        result = logger.import_student_csv(
            uploaded_file,
            replace_existing
        )
        logger.record_event(
            'database_import',
            f"Imported {result['imported']} student records."
        )
        return jsonify({
            'status': 'success',
            **result,
            'students': len(logger.get_all_students())
        })
    except (UnicodeDecodeError, csv.Error, ValueError) as error:
        return jsonify({
            'status': 'error',
            'message': str(error)
        }), 400


# --- LOGS AND AUDIT ---

@app.route('/api/logs/list', methods=['GET'])
def api_logs_list():
    return jsonify(logger.get_available_log_files())


@app.route('/api/logs/today', methods=['GET'])
def api_logs_today():
    return jsonify(logger.get_todays_logs_raw())


@app.route('/api/logs/view', methods=['GET'])
def api_logs_view():
    filename = request.args.get('file', '').strip()

    try:
        logs = logger.get_logs_by_filename_raw(filename)
    except (TypeError, ValueError):
        return jsonify({
            'status': 'error',
            'message': 'Invalid log file.'
        }), 400

    return jsonify(logs)


@app.route('/api/audit/events', methods=['POST'])
def audit_events_api():
    authorization_error = protected_response('view audit events')
    if authorization_error:
        return authorization_error

    return jsonify(logger.get_audit_events())


@app.route('/api/logs/snapshot', methods=['GET'])
def get_log_snapshot():
    date_str = request.args.get('date', '').strip()
    image_id = request.args.get('id', '').strip()

    if not date_str or date_str.lower() == 'today':
        date_str = datetime.now().strftime('%Y-%m-%d')

    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date_str):
        return jsonify({
            'status': 'error',
            'message': 'Invalid log date.'
        }), 400

    if not image_id or image_id != os.path.basename(image_id):
        return jsonify({
            'status': 'error',
            'message': 'Invalid snapshot ID.'
        }), 400

    folder_path = os.path.join(DB_DIR, f'logs_{date_str}')

    if not os.path.exists(folder_path):
        return jsonify({
            'status': 'error',
            'message': 'Log folder not found'
        }), 404

    file_path = os.path.join(folder_path, image_id)

    if os.path.exists(file_path):
        return send_file(file_path, mimetype='image/jpeg')

    return jsonify({
        'status': 'error',
        'message': 'Snapshot not found'
    }), 404


# --- STUDENT MANAGEMENT ---

@app.route('/api/save_student', methods=['POST'])
def save_student_api():
    authorization_error = protected_response('save student records')
    if authorization_error:
        return authorization_error

    data = request.get_json(silent=True) or {}

    b = str(data.get('b', '')).strip()
    n = str(data.get('n', '')).strip()
    g = str(data.get('g', '')).strip()
    s = str(data.get('s', '')).strip()
    a = str(data.get('a', 'REGULAR')).strip()
    c = str(data.get('c', '#059669')).strip()
    t = str(data.get('t', 'None')).strip()

    if not b or not n:
        return jsonify({
            'status': 'error',
            'message': 'Barcode and Name are required'
        }), 400

    if any(len(value) > 100 for value in (b, n, g, s, a, t)):
        return jsonify({
            'status': 'error',
            'message': 'Student fields must be 100 characters or fewer.'
        }), 400

    if not re.fullmatch(r'#[0-9a-fA-F]{6}', c):
        return jsonify({
            'status': 'error',
            'message': 'Badge color must be a valid hexadecimal color.'
        }), 400

    logger.save_student(b, n, g, s, a, c, t)
    logger.record_event(
        'student_saved',
        'Student record added or updated.',
        b
    )

    return jsonify({'status': 'success'})


@app.route('/api/delete_student', methods=['POST'])
def delete_student_api():
    authorization_error = protected_response('delete student records')
    if authorization_error:
        return authorization_error

    data = request.get_json(silent=True) or {}
    barcode = str(data.get('barcode', '')).strip()

    if barcode:
        logger.delete_student(barcode)
        logger.record_event(
            'student_deleted',
            'Student record deleted.',
            barcode
        )
        return jsonify({'status': 'success'})

    return jsonify({
        'status': 'error',
        'message': 'Barcode missing'
    }), 400


# --- SCANNER ---

@app.route('/api/scan', methods=['POST'])
def scan_api():
    data = request.get_json(silent=True) or {}
    barcode = str(data.get('barcode') or '').strip()
    image_data = str(data.get('image') or '').strip()

    if not barcode:
        return jsonify({
            'status': 'error',
            'message': 'Barcode missing'
        }), 400

    settings = load_system_settings()

    command_map = {
        settings.get('close_kiosk_barcode'): 'close_kiosk',
        settings.get('shutdown_barcode'): 'shutdown',
        settings.get('launchpad_barcode'): 'launchpad',
        settings.get('database_manager_barcode'): 'database_manager',
        settings.get('log_manager_barcode'): 'log_manager',
        settings.get('settings_barcode'): 'settings'
    }

    if barcode in command_map:
        return jsonify({
            'status': 'system_command',
            'command': command_map[barcode]
        })

    result = logger.log_attendance(barcode)

    if result.get('status') == 'error':
        logger.record_event(
            'invalid_scan',
            result.get('message', 'Unknown barcode.'),
            barcode
        )
        return jsonify({
            **result,
            'message': f"Scan error: {result.get('message', 'Unknown barcode.')}"
        }), 404

    if result.get('status') == 'duplicate':
        logger.record_event(
            'dual_scan',
            result.get(
                'message',
                'Dual scan detected; attendance not logged.'
            ),
            barcode
        )

    if result.get('status') == 'success':
        timestamp = datetime.now().strftime('%m/%d/%Y %I:%M:%S %p')
        result['data']['timestamp'] = timestamp

        dispatch_parent_notification(
            result['data'],
            timestamp,
            settings
        )

        logger.record_event(
            'scan_logged',
            'Attendance scan logged.',
            barcode
        )

    if image_data and result.get('status') == 'success':
        try:
            folder = get_today_folder()
            image_id = result.get('image_id', 'unknown.jpg')
            file_path = os.path.join(folder, image_id)

            if ',' in image_data:
                _, encoded = image_data.split(',', 1)
            else:
                encoded = image_data

            image_bytes = base64.b64decode(encoded)

            with open(file_path, 'wb') as fh:
                fh.write(image_bytes)

        except Exception:
            app.logger.exception('Scan photo could not be saved')

    return jsonify(result)


# --- SYSTEM CONTROL ---

@app.route('/api/system/reboot', methods=['POST'])
def system_reboot():
    authorization_error = protected_response('restart the system')
    if authorization_error:
        return authorization_error

    os.system('shutdown /r /t 0')
    return jsonify({'status': 'rebooting'})


@app.route('/api/system/shutdown', methods=['POST'])
def system_shutdown():
    authorization_error = protected_response('shut down the system')
    if authorization_error:
        return authorization_error

    os.system('shutdown /s /t 0')
    return jsonify({'status': 'shutting down'})


@app.route('/api/exit', methods=['POST'])
def exit_api():
    authorization_error = protected_response('exit kiosk mode')
    if authorization_error:
        return authorization_error

    try:
        browser_pid = os.environ.get('CVAFPI_BROWSER_PID', '').strip()
        if browser_pid.isdigit():
            os.system(
                f'taskkill /PID {browser_pid} /T /F >NUL 2>&1'
            )
    except Exception as error:
        print(f'[Exit Error]: {error}')

    threading.Timer(0.5, lambda: os._exit(0)).start()
    return jsonify({'status': 'success'})


@app.route('/api/system/command', methods=['POST'])
def system_command_api():
    authorization_error = protected_response('run this system command')
    if authorization_error:
        return authorization_error

    command = (request.get_json(silent=True) or {}).get('command')

    if command == 'shutdown':
        os.system('shutdown /s /t 0')
        return jsonify({'status': 'shutting down'})

    if command == 'close_kiosk':
        try:
            browser_pid = os.environ.get('CVAFPI_BROWSER_PID', '').strip()
            if browser_pid.isdigit():
                os.system(
                    f'taskkill /PID {browser_pid} /T /F >NUL 2>&1'
                )
        except Exception as error:
            print(f'[Command Exit Error]: {error}')

        threading.Timer(0.5, lambda: os._exit(0)).start()
        return jsonify({'status': 'success'})

    if command == 'launchpad':
        return jsonify({
            'status': 'redirect',
            'location': '/launchpad.html'
        })

    if command == 'database_manager':
        return jsonify({
            'status': 'redirect',
            'location': '/manager.html'
        })

    if command == 'log_manager':
        return jsonify({
            'status': 'redirect',
            'location': '/logs-manager.html'
        })

    if command == 'settings':
        return jsonify({
            'status': 'redirect',
            'location': '/launchpad.html?settings=1'
        })

    return jsonify({
        'status': 'error',
        'message': 'Unknown system command.'
    }), 400


if __name__ == '__main__':
    from waitress import serve

    serve(
        app,
        host='127.0.0.1',
        port=int(os.environ.get('CVAFPI_PORT', '5000')),
        threads=4
    )
