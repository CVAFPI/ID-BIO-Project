import os
import subprocess
import sys
import tempfile
import time
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

    def test_concurrent_process_scans_only_record_once(self):
        project_root = Path(__file__).resolve().parents[1]

        with tempfile.TemporaryDirectory(prefix='cvafpi-scan-test-') as data_dir:
            environment = os.environ.copy()
            environment['CVAFPI_DATA_DIR'] = data_dir
            setup = subprocess.run(
                [
                    sys.executable,
                    '-c',
                    "import logger; logger.save_student('SCAN-1', 'Scan Student', '', '', 'REGULAR', '#059669', 'None')"
                ],
                cwd=project_root,
                env=environment,
                capture_output=True,
                text=True,
                check=False
            )
            self.assertEqual(setup.returncode, 0, setup.stdout + setup.stderr)

            start_path = Path(data_dir) / 'start-scans'
            workers = []
            script = '''
import os
import time
import logger

open(os.environ['READY_PATH'], 'w').close()
start = os.environ['START_PATH']
deadline = time.monotonic() + 15
while not os.path.exists(start) and time.monotonic() < deadline:
    time.sleep(0.01)
print(logger.log_attendance('SCAN-1')['status'])
'''
            try:
                for index in range(2):
                    worker_environment = environment.copy()
                    worker_environment['READY_PATH'] = str(
                        Path(data_dir) / f'worker-{index}-ready'
                    )
                    worker_environment['START_PATH'] = str(start_path)
                    workers.append(subprocess.Popen(
                        [sys.executable, '-c', script],
                        cwd=project_root,
                        env=worker_environment,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    ))

                ready_paths = [
                    Path(data_dir) / f'worker-{index}-ready'
                    for index in range(2)
                ]
                deadline = time.monotonic() + 20
                while not all(path.exists() for path in ready_paths):
                    if time.monotonic() >= deadline:
                        self.fail('Scan worker processes did not become ready.')
                    time.sleep(0.01)

                start_path.touch()
                results = [worker.communicate(timeout=30) for worker in workers]
            finally:
                for worker in workers:
                    if worker.poll() is None:
                        worker.kill()
                        worker.communicate()

        for worker, (stdout, stderr) in zip(workers, results):
            self.assertEqual(worker.returncode, 0, stdout + stderr)
        self.assertEqual(
            sorted(stdout.strip() for stdout, _ in results),
            ['duplicate', 'success']
        )


if __name__ == '__main__':
    unittest.main()