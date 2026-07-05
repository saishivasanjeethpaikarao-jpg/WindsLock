from database import EncryptedDatabase
import os
from pathlib import Path
import tempfile
import unittest

import config
import folder_locker


class FolderLockerTests(unittest.TestCase):
    def setUp(self):
        from database import EncryptedDatabase
        EncryptedDatabase.reset_cache()
        self.tempdir = tempfile.TemporaryDirectory()
        os.environ[config.ENV_APP_DIR] = os.path.join(self.tempdir.name, "appdata")
        self.old_iterations = config.ITERATIONS
        config.ITERATIONS = 1000
        self.old_folder_iterations = folder_locker.ITERATIONS
        folder_locker.ITERATIONS = 1000
        config.set_master_password("folder password")

    def tearDown(self):
        config.ITERATIONS = self.old_iterations
        folder_locker.ITERATIONS = self.old_folder_iterations
        self.tempdir.cleanup()
        os.environ.pop(config.ENV_APP_DIR, None)

    def test_folder_lock_unlock_roundtrip_and_history(self):
        target = Path(self.tempdir.name) / "private"
        nested = target / "nested"
        nested.mkdir(parents=True)
        (target / "note.txt").write_text("secret text", encoding="utf-8")
        (nested / "child.txt").write_text("child secret", encoding="utf-8")

        locked_path = folder_locker.lock_folder(str(target), "folder password")
        self.assertFalse(target.exists())
        self.assertTrue(Path(locked_path).exists())

        restored = folder_locker.unlock_folder(locked_path, "folder password")
        self.assertEqual(str(target.resolve()), restored)
        self.assertEqual("secret text", (target / "note.txt").read_text(encoding="utf-8"))
        self.assertEqual("child secret", (nested / "child.txt").read_text(encoding="utf-8"))
        self.assertFalse(Path(locked_path).exists())

        events = EncryptedDatabase("folder password")._data["audit_log"]
        self.assertEqual(["locked", "unlocked"], [event["action"] for event in events])

    def test_wrong_password_does_not_remove_locked_file(self):
        target = Path(self.tempdir.name) / "private"
        target.mkdir()
        (target / "note.txt").write_text("secret text", encoding="utf-8")
        locked_path = folder_locker.lock_folder(str(target), "folder password")

        with self.assertRaises(ValueError):
            folder_locker.unlock_folder(locked_path, "wrong password")
        self.assertTrue(Path(locked_path).exists())


if __name__ == "__main__":
    unittest.main()
