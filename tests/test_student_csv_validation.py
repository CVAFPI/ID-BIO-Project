import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class StudentCsvValidationTests(unittest.TestCase):
    def test_invalid_rows_are_rejected_without_partial_import(self):
        project_root = Path(__file__).resolve().parents[1]

        with tempfile.TemporaryDirectory(prefix='cvafpi-csv-test-') as data_dir:
            environment = os.environ.copy()
            environment['CVAFPI_DATA_DIR'] = data_dir
            script = (
                'import csv, io, app, logger; '
                'client = app.app.test_client(); '
                "assert client.post('/api/settings', json={'new_pin':'test1234','security_question':'Color?','security_answer':'blue'}).status_code == 200; "
                'stream = io.StringIO(); '
                "csv.writer(stream).writerows([['BARCODE','NAME','COLOR'],['BAD-COLOR','Student','red'],['LONG-NAME','N'*101,'#059669']]); "
                'payload = stream.getvalue().encode(); '
                "preview = client.post('/api/migration/preview', data={'file':(io.BytesIO(payload),'students.csv')}); "
                "assert preview.status_code == 200 and preview.json['valid_rows'] == 0 and preview.json['invalid_rows'] == 2; "
                "result = client.post('/api/migration/import', data={'pin':'test1234','file':(io.BytesIO(payload),'students.csv')}); "
                "assert result.status_code == 400 and logger.get_all_students() == {}"
            )
            result = subprocess.run(
                [sys.executable, '-c', script],
                cwd=project_root,
                env=environment,
                capture_output=True,
                text=True,
                check=False
            )

        self.assertEqual(
            result.returncode,
            0,
            result.stdout + result.stderr
        )

    def test_empty_replace_import_preserves_existing_students(self):
        project_root = Path(__file__).resolve().parents[1]

        with tempfile.TemporaryDirectory(prefix='cvafpi-empty-csv-test-') as data_dir:
            environment = os.environ.copy()
            environment['CVAFPI_DATA_DIR'] = data_dir
            script = (
                'import io, app, logger; '
                'client = app.app.test_client(); '
                "assert client.post('/api/settings', json={'new_pin':'test1234','security_question':'Color?','security_answer':'blue'}).status_code == 200; "
                "assert client.post('/api/save_student', json={'pin':'test1234','b':'KEEP-1','n':'Keep Student'}).status_code == 200; "
                'empty_csv = b\'BARCODE,NAME\' + bytes([10]); '
                "preview = client.post('/api/migration/preview', data={'file':(io.BytesIO(empty_csv),'empty.csv')}); "
                "assert preview.status_code == 200 and preview.json['valid_rows'] == 0 and preview.json['errors']; "
                "result = client.post('/api/migration/import', data={'pin':'test1234','replace_existing':'true','file':(io.BytesIO(empty_csv),'empty.csv')}); "
                "assert result.status_code == 400 and set(logger.get_all_students()) == {'KEEP-1'}"
            )
            result = subprocess.run(
                [sys.executable, '-c', script],
                cwd=project_root,
                env=environment,
                capture_output=True,
                text=True,
                check=False
            )

        self.assertEqual(
            result.returncode,
            0,
            result.stdout + result.stderr
        )

    def test_recovered_passcode_is_audited_and_backed_up(self):
        project_root = Path(__file__).resolve().parents[1]

        with tempfile.TemporaryDirectory(prefix='cvafpi-recovery-test-') as data_dir:
            environment = os.environ.copy()
            environment['CVAFPI_DATA_DIR'] = data_dir
            script = '''
import sqlite3
import app
import logger

client = app.app.test_client()
setup = client.post('/api/settings', json={
    'new_pin': 'oldpin1',
    'security_question': 'Color?',
    'security_answer': 'blue'
})
assert setup.status_code == 200, setup.get_json()

recovery = client.post('/api/security/recover', json={
    'security_answer': 'blue',
    'new_pin': 'newpin2'
})
assert recovery.status_code == 200, recovery.get_json()

primary = sqlite3.connect(logger.DATABASE_FILE)
backup = sqlite3.connect(logger.DATABASE_BACKUP_FILE)
primary_hash = primary.execute(
    "SELECT setting_value FROM app_settings WHERE setting_key='pin_hash'"
).fetchone()[0]
backup_hash = backup.execute(
    "SELECT setting_value FROM app_settings WHERE setting_key='pin_hash'"
).fetchone()[0]
assert primary_hash == backup_hash
assert backup.execute(
    "SELECT 1 FROM audit_events WHERE event_type='passcode_recovered'"
).fetchone()
primary.close()
backup.close()

assert client.post(
    '/api/settings', json={'current_pin': 'oldpin1'}
).status_code == 401
assert client.post(
    '/api/settings', json={'current_pin': 'newpin2'}
).status_code == 200
'''
            result = subprocess.run(
                [sys.executable, '-c', script],
                cwd=project_root,
                env=environment,
                capture_output=True,
                text=True,
                check=False
            )

        self.assertEqual(
            result.returncode,
            0,
            result.stdout + result.stderr
        )


if __name__ == '__main__':
    unittest.main()