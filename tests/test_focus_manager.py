from datetime import datetime, timedelta
import os
import tempfile
import unittest

import config
import focus_manager


class FocusManagerTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        os.environ[config.ENV_APP_DIR] = self.tempdir.name
        self.old_iterations = config.ITERATIONS
        config.ITERATIONS = 1000
        config.set_master_password("test password")

    def tearDown(self):
        config.ITERATIONS = self.old_iterations
        self.tempdir.cleanup()
        os.environ.pop(config.ENV_APP_DIR, None)

    def test_preset_adds_apps_sites_and_path_rules(self):
        focus_manager.apply_preset("test password", "Deep Work")
        data = config.load_config("test password")

        self.assertTrue(any(rule["value"] == "steam.exe" for rule in data["locked_apps"]))
        self.assertIn("reddit.com", data["blocked_sites"])
        self.assertIn({"domain": "youtube.com", "path_prefix": "/shorts"}, data["blocked_url_paths"])

    def test_focus_session_counts_as_active_in_schedule_only_mode(self):
        focus_manager.set_schedule_only_mode("test password", True)
        data = config.load_config("test password")
        self.assertFalse(focus_manager.should_enforce(data))

        focus_manager.start_focus_session("test password", 30)
        data = config.load_config("test password")
        self.assertTrue(focus_manager.should_enforce(data))

    def test_weekly_schedule_controls_enforcement(self):
        focus_manager.set_schedule_only_mode("test password", True)
        focus_manager.add_schedule("test password", "Study", [0], "09:00", "10:00")
        data = config.load_config("test password")

        monday_inside = datetime(2026, 7, 6, 9, 30)
        monday_outside = datetime(2026, 7, 6, 11, 0)
        self.assertTrue(focus_manager.should_enforce(data, monday_inside))
        self.assertFalse(focus_manager.should_enforce(data, monday_outside))


if __name__ == "__main__":
    unittest.main()
