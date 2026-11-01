import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class DatabaseBackupTests(unittest.TestCase):
    def test_backup_can_be_replaced_repeatedly(self):
        project_root = Path(__file__).resolve().parents[1]

        with tempfile.TemporaryDirectory(prefix='cvafpi-backup-test-') as data_dir:
            environment = os.environ.copy()
            environment['CVAFPI_DATA_DIR'] = data_dir
            script = (
                'import sqlite3, logger; '
                'assert logger.backup_database(); '
                'assert logger.backup_database(); '
                'connection = sqlite3.connect(logger.DATABASE_BACKUP_FILE); '
                "assert connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'; "
                'connection.close()'
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


if __name__ == '__main__':
    unittest.main()