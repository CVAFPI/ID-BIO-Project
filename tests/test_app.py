import os
import tempfile
import unittest

import app as app_module
import logger
from app import CONTROL_TOKEN, app


class ApiBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_log_view_rejects_path_traversal(self):
        response = self.client.get('/api/logs/view?file=../../outside')

        self.assertEqual(response.status_code, 400)

    def test_snapshot_rejects_path_traversal(self):
        response = self.client.get('/api/logs/snapshot?date=2026-01-01&id=../../outside')

        self.assertEqual(response.status_code, 400)

    def test_all_write_endpoints_require_a_token(self):
        response = self.client.post('/api/migration/import')

        self.assertEqual(response.status_code, 403)

    def test_launchpad_receives_a_per_run_control_token(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertIn(CONTROL_TOKEN.encode(), response.data)

    def test_all_application_pages_render(self):
        for path in (
            '/launchpad.html',
            '/manager.html',
            '/scanner.html',
            '/logs-manager.html',
            '/audit-manager.html',
            '/migration.html'
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'cvafpi-control-token', response.data)
                self.assertIn(b'/static/control-token.js', response.data)

    def test_local_connectivity_check_has_no_external_dependency(self):
        response = self.client.get('/api/ping')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': 'ok'})

    def test_system_controls_require_per_run_token(self):
        response = self.client.post('/api/system/shutdown')

        self.assertEqual(response.status_code, 403)
        self.assertTrue(CONTROL_TOKEN)

    def test_barcode_library_is_served_locally(self):
        response = self.client.get('/jsbarcode.js')

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'JsBarcode', response.data)
        response.close()


class AttendanceFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_logger_paths = (
            logger.BASE_DIR, logger.DB_DIR, logger.DATA_CSV, logger.BACKUP_CSV,
            logger.AUDIT_CSV
        )
        self.original_app_paths = (app_module.DB_DIR, app_module.SETTINGS_FILE)
        logger.BASE_DIR = self.temp_dir.name
        logger.DB_DIR = os.path.join(self.temp_dir.name, 'CVA_Database')
        logger.DATA_CSV = os.path.join(self.temp_dir.name, 'data.csv')
        logger.BACKUP_CSV = os.path.join(self.temp_dir.name, 'backup-data.csv')
        logger.AUDIT_CSV = os.path.join(self.temp_dir.name, 'audit.csv')
        app_module.DB_DIR = logger.DB_DIR
        app_module.SETTINGS_FILE = os.path.join(self.temp_dir.name, 'settings.json')
        os.makedirs(logger.DB_DIR)
        self.client = app.test_client()

    def tearDown(self):
        (
            logger.BASE_DIR, logger.DB_DIR, logger.DATA_CSV,
            logger.BACKUP_CSV, logger.AUDIT_CSV
        ) = self.original_logger_paths
        app_module.DB_DIR, app_module.SETTINGS_FILE = self.original_app_paths
        self.temp_dir.cleanup()

    def configure_passcode(self):
        response = self.client.post(
            '/api/settings',
            headers={'X-CVAFPI-Control-Token': CONTROL_TOKEN},
            json={
                'new_pin': '2468',
                'security_question': 'What is the test word?',
                'security_answer': 'sample'
            }
        )
        self.assertEqual(response.status_code, 200)

    def test_student_save_and_scan_persist_attendance(self):
        headers = {'X-CVAFPI-Control-Token': CONTROL_TOKEN}
        self.configure_passcode()
        saved = self.client.post('/api/save_student', headers=headers, json={
            'b': 'TEST-123',
            'n': 'Test Student',
            'g': 'Grade 7',
            's': 'Faith',
            'a': 'REGULAR',
            'c': '#059669',
            't': 'None',
            'pin': '2468'
        })
        self.assertEqual(saved.status_code, 200)

        scanned = self.client.post(
            '/api/scan',
            headers=headers,
            json={'barcode': 'TEST-123', 'image': None},
        )
        self.assertEqual(scanned.status_code, 200)
        scan_result = scanned.get_json()
        self.assertEqual(scan_result['status'], 'success')

        logs = self.client.get('/api/logs/today').get_json()
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[1][1:3], ['TEST-123', 'Test Student'])
        self.assertEqual(scan_result['data']['timestamp'], logs[1][0])

    def test_duplicate_scan_within_cooldown_does_not_add_attendance(self):
        headers = {'X-CVAFPI-Control-Token': CONTROL_TOKEN}
        self.configure_passcode()
        saved = self.client.post('/api/save_student', headers=headers, json={
            'b': 'DOUBLE-SCAN-1',
            'n': 'Test Student',
            'pin': '2468'
        })
        self.assertEqual(saved.status_code, 200)

        first = self.client.post(
            '/api/scan',
            headers=headers,
            json={'barcode': 'DOUBLE-SCAN-1', 'image': None},
        )
        duplicate = self.client.post(
            '/api/scan',
            headers=headers,
            json={'barcode': 'DOUBLE-SCAN-1', 'image': None},
        )

        self.assertEqual(first.get_json()['status'], 'success')
        self.assertEqual(duplicate.get_json()['status'], 'duplicate')
        self.assertEqual(len(self.client.get('/api/logs/today').get_json()), 2)

    def test_student_changes_require_administrator_passcode(self):
        headers = {'X-CVAFPI-Control-Token': CONTROL_TOKEN}
        payload = {'b': 'TEST-1', 'n': 'Student', 'pin': '2468'}
        self.assertEqual(self.client.post('/api/save_student', headers=headers, json=payload).status_code, 403)
        self.configure_passcode()
        payload['pin'] = 'wrong'
        self.assertEqual(self.client.post('/api/save_student', headers=headers, json=payload).status_code, 401)
        payload['pin'] = '2468'
        self.assertEqual(self.client.post('/api/save_student', headers=headers, json=payload).status_code, 200)

    def test_settings_never_expose_passcode_hashes(self):
        self.configure_passcode()
        settings = self.client.get('/api/settings').get_json()
        self.assertNotIn('pin_hash', settings)
        self.assertNotIn('pin_salt', settings)
        self.assertNotIn('security_answer_hash', settings)
        self.assertEqual(settings['security_question'], 'What is the test word?')

    def test_notification_topic_prefix_is_saved_and_validated(self):
        headers = {'X-CVAFPI-Control-Token': CONTROL_TOKEN}
        self.configure_passcode()
        saved = self.client.post('/api/settings', headers=headers, json={
            'current_pin': '2468',
            'notification_topic_prefix': 'CVA-OPS'
        })
        self.assertEqual(saved.status_code, 200)
        settings = self.client.get('/api/settings').get_json()
        self.assertEqual(settings['notification_topic_prefix'], 'CVA-OPS')

        rejected = self.client.post('/api/settings', headers=headers, json={
            'current_pin': '2468',
            'notification_topic_prefix': 'CVA!'
        })
        self.assertEqual(rejected.status_code, 400)

    def test_audit_history_requires_passcode_and_records_changes(self):
        headers = {'X-CVAFPI-Control-Token': CONTROL_TOKEN}
        denied = self.client.post('/api/audit/events', headers=headers, json={'pin': '2468'})
        self.assertEqual(denied.status_code, 403)
        self.configure_passcode()
        unauthorized = self.client.post('/api/audit/events', headers=headers, json={'pin': 'wrong'})
        self.assertEqual(unauthorized.status_code, 401)
        response = self.client.post('/api/audit/events', headers=headers, json={'pin': '2468'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(row[1] == 'settings_saved' for row in response.get_json()))

    def test_security_answer_can_recover_passcode(self):
        headers = {'X-CVAFPI-Control-Token': CONTROL_TOKEN}
        self.configure_passcode()
        response = self.client.post('/api/security/recover', headers=headers, json={
            'security_answer': 'sample',
            'new_pin': '1357'
        })
        self.assertEqual(response.status_code, 200)
        saved = self.client.post('/api/save_student', headers=headers, json={
            'b': 'TEST-2', 'n': 'Student', 'pin': '1357'
        })
        self.assertEqual(saved.status_code, 200)

    def test_system_control_barcode_is_detected_without_logging_attendance(self):
        settings = app_module.load_system_settings()
        response = self.client.post(
            '/api/scan',
            headers={'X-CVAFPI-Control-Token': CONTROL_TOKEN},
            json={'barcode': settings['database_manager_barcode'], 'image': None}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {
            'status': 'system_command',
            'command': 'database_manager'
        })


if __name__ == '__main__':
    unittest.main()
