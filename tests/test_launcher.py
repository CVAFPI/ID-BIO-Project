import os
import socket
import tempfile
import unittest
from unittest.mock import patch

import windows_launcher


class DataDirectoryTests(unittest.TestCase):
    def test_frozen_app_seeds_writable_user_data_once(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = os.path.join(temp_dir, 'program')
            local_app_data = os.path.join(temp_dir, 'user')
            os.makedirs(app_dir)
            with open(os.path.join(app_dir, 'data.csv'), 'w', encoding='utf-8') as file:
                file.write('BARCODE,NAME\n123,Student\n')
            with open(os.path.join(app_dir, 'backup-data.csv'), 'w', encoding='utf-8') as file:
                file.write('BARCODE,NAME\n123,Student\n')
            with open(os.path.join(app_dir, 'settings.json'), 'w', encoding='utf-8') as file:
                file.write('{}')

            old_data_dir = os.environ.pop('CVAFPI_DATA_DIR', None)
            try:
                with patch.object(windows_launcher, 'APP_DIR', app_dir), \
                        patch.object(windows_launcher.sys, 'frozen', True, create=True), \
                        patch.dict(os.environ, {'LOCALAPPDATA': local_app_data}):
                    windows_launcher.configure_data_directory()

                    self.assertEqual(os.environ['CVAFPI_DATA_DIR'], os.path.join(local_app_data, 'CVAFPI-IDSYS'))
                    for name in ('data.csv', 'backup-data.csv'):
                        self.assertTrue(os.path.isfile(os.path.join(os.environ['CVAFPI_DATA_DIR'], name)))
                    self.assertFalse(os.path.exists(
                        os.path.join(os.environ['CVAFPI_DATA_DIR'], 'settings.json')
                    ))
            finally:
                os.environ.pop('CVAFPI_DATA_DIR', None)
                if old_data_dir is not None:
                    os.environ['CVAFPI_DATA_DIR'] = old_data_dir

    def test_existing_port_is_reported(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen()
            port = listener.getsockname()[1]

            with self.assertRaisesRegex(RuntimeError, 'already in use'):
                windows_launcher.ensure_port_available(port=port)


if __name__ == '__main__':
    unittest.main()
