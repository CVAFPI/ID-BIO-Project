import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class LegacySettingsMigrationTests(unittest.TestCase):
    def test_missing_settings_are_imported_without_overwriting_sqlite(self):
        project_root = Path(__file__).resolve().parents[1]

        with tempfile.TemporaryDirectory(prefix='cvafpi-settings-test-') as data_dir:
            environment = os.environ.copy()
            environment['CVAFPI_DATA_DIR'] = data_dir
            script = '''
import json
import os
import logger

with open(
    os.path.join(logger.BASE_DIR, 'settings.json'),
    'w',
    encoding='utf-8'
) as settings_file:
    json.dump({
        'theme': 'ocean',
        'camera_enabled': True,
        'institution_name': 'Legacy Academy'
    }, settings_file)

logger.save_app_settings({'theme': 'sunset'})
import app
settings = app.load_system_settings()
assert settings['theme'] == 'sunset'
assert settings['camera_enabled'] is True
assert settings['institution_name'] == 'Legacy Academy'
assert any(
    event[1] == 'settings_migrated'
    for event in logger.get_audit_events()
)
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
