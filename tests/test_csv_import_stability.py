import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CsvImportStabilityTests(unittest.TestCase):
    def run_isolated(self, script, prefix):
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix=prefix) as data_dir:
            environment = os.environ.copy()
            environment['CVAFPI_DATA_DIR'] = data_dir
            result = subprocess.run(
                [sys.executable, '-c', script],
                cwd=project_root,
                env=environment,
                capture_output=True,
                text=True,
                check=False
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_invalid_and_empty_imports_preserve_existing_students(self):
        script = '''
import io
import logger

logger.save_student('KEEP-1', 'Keep Student', '', '', 'REGULAR', '#059669', 'None')
csv_data = (
    b'BARCODE,NAME,COLOR\\nBAD-COLOR,Student,red\\nLONG-NAME,'
    + b'N' * 101 + b',#059669\\n'
)
preview = logger.preview_student_csv(io.BytesIO(csv_data))
assert preview['valid_rows'] == 0 and preview['invalid_rows'] == 2, preview

for content in (csv_data, b'BARCODE,NAME\\n'):
    try:
        logger.import_student_csv(io.BytesIO(content), replace_existing=True)
    except ValueError:
        pass
    else:
        raise AssertionError('Invalid or empty import should fail')

assert set(logger.get_all_students()) == {'KEEP-1'}
'''
        self.run_isolated(script, 'cvafpi-csv-import-test-')

    def test_duplicate_scan_is_not_logged_twice(self):
        script = (
            'import logger; '
            "logger.save_student('KEEP-1', 'Keep Student', '', '', 'REGULAR', '#059669', 'None'); "
            "assert logger.log_attendance('KEEP-1')['status'] == 'success'; "
            "assert logger.log_attendance('KEEP-1')['status'] == 'duplicate'; "
            "assert len(logger.get_todays_logs_raw()) == 2"
        )
        self.run_isolated(script, 'cvafpi-duplicate-scan-test-')


if __name__ == '__main__':
    unittest.main()