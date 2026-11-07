import os
import tempfile
import unittest
from io import BytesIO
from werkzeug.datastructures import FileStorage

import logger


class StudentCsvTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_paths = (logger.BASE_DIR, logger.DB_DIR, logger.DATA_CSV, logger.BACKUP_CSV)
        logger.BASE_DIR = self.temp_dir.name
        logger.DB_DIR = os.path.join(self.temp_dir.name, 'CVA_Database')
        logger.DATA_CSV = os.path.join(self.temp_dir.name, 'data.csv')
        logger.BACKUP_CSV = os.path.join(self.temp_dir.name, 'backup-data.csv')
        os.makedirs(logger.DB_DIR)

    def tearDown(self):
        logger.BASE_DIR, logger.DB_DIR, logger.DATA_CSV, logger.BACKUP_CSV = self.original_paths
        self.temp_dir.cleanup()

    def test_reads_utf8_bom_header_without_treating_it_as_a_student(self):
        with open(logger.DATA_CSV, 'w', encoding='utf-8-sig', newline='') as csv_file:
            csv_file.write('BARCODE,NAME\n123,Student\n')

        self.assertEqual(list(logger.get_all_students()), ['123'])

    def test_recovers_students_when_primary_csv_is_missing(self):
        with open(logger.BACKUP_CSV, 'w', encoding='utf-8', newline='') as csv_file:
            csv_file.write('BARCODE,NAME\n123,Student\n')

        self.assertEqual(list(logger.get_all_students()), ['123'])

    def test_recovers_students_when_primary_csv_is_empty(self):
        open(logger.DATA_CSV, 'w', encoding='utf-8').close()
        with open(logger.BACKUP_CSV, 'w', encoding='utf-8', newline='') as csv_file:
            csv_file.write('BARCODE,NAME\n123,Student\n')

        self.assertEqual(list(logger.get_all_students()), ['123'])

    def test_student_writes_update_primary_and_backup(self):
        logger.save_student('123', 'Student', '', '', 'REGULAR', '#059669', 'None')

        with open(logger.DATA_CSV, encoding='utf-8') as primary:
            primary_content = primary.read()
        with open(logger.BACKUP_CSV, encoding='utf-8') as backup:
            backup_content = backup.read()

        self.assertEqual(primary_content, backup_content)
        self.assertIn('123,Student', primary_content)

    def test_rejects_log_path_traversal(self):
        with self.assertRaises(ValueError):
            logger.get_logs_by_filename_raw('../../outside')

    def test_import_rejects_duplicate_barcodes(self):
        uploaded_file = FileStorage(
            stream=BytesIO(b'BARCODE,NAME\n123,First\n123,Duplicate\n'),
            filename='students.csv'
        )

        with self.assertRaisesRegex(ValueError, 'duplicates barcode'):
            logger.import_student_csv(uploaded_file)


if __name__ == '__main__':
    unittest.main()
