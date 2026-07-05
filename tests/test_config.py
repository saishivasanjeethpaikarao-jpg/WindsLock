from database import EncryptedDatabase
import os
import tempfile
import unittest

import config


class ConfigTests(unittest.TestCase):
    def setUp(self):
        from database import EncryptedDatabase
        EncryptedDatabase.reset_cache()
        self.tempdir = tempfile.TemporaryDirectory()
        os.environ[config.ENV_APP_DIR] = self.tempdir.name
        self.old_iterations = config.ITERATIONS
        config.ITERATIONS = 1000

    def tearDown(self):
        config.ITERATIONS = self.old_iterations
        self.tempdir.cleanup()
        os.environ.pop(config.ENV_APP_DIR, None)

    def test_password_verification_and_encrypted_config_roundtrip(self):
        recovery_codes = config.set_master_password("correct horse")
        self.assertEqual(len(recovery_codes), config.RECOVERY_CODE_COUNT)
        self.assertTrue(config.verify_password("correct horse"))
        self.assertFalse(config.verify_password("wrong horse"))

        data = EncryptedDatabase("correct horse")._data
        data["blocked_sites"].append("example.com")
        EncryptedDatabase("correct horse").save_dict(data)

        loaded = EncryptedDatabase("correct horse")._data
        self.assertIn("example.com", loaded["blocked_sites"])
        raw = config.get_config_path().read_bytes()
        self.assertNotIn(b"example.com", raw)

    def test_recovery_code_resets_password_and_rotates_codes(self):
        recovery_codes = config.set_master_password("old password")
        new_codes = config.reset_password_with_recovery(recovery_codes[0], "new password")

        self.assertFalse(config.verify_password("old password"))
        self.assertTrue(config.verify_password("new password"))
        self.assertEqual(len(new_codes), config.RECOVERY_CODE_COUNT)
        with self.assertRaises(Exception):
            config.reset_password_with_recovery(recovery_codes[0], "another password")


if __name__ == "__main__":
    unittest.main()
