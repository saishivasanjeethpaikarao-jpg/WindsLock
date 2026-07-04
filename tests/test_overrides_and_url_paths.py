from datetime import timedelta
import os
import tempfile
import unittest

import config
import override_manager
import url_rule_engine


class OverrideAndUrlPathTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        os.environ[config.ENV_APP_DIR] = self.tempdir.name
        self.old_iterations = config.ITERATIONS
        config.ITERATIONS = 1000
        config.set_master_password("test password")
        override_manager.update_settings("test password", "unlock with intention", 5, 10)

    def tearDown(self):
        config.ITERATIONS = self.old_iterations
        self.tempdir.cleanup()
        os.environ.pop(config.ENV_APP_DIR, None)

    def test_wrong_phrase_is_denied_and_logged(self):
        result = override_manager.request_override("test password", "app", "notepad.exe", "wrong")
        self.assertEqual(override_manager.STATUS_DENIED, result["status"])
        events = config.load_config("test password")["audit_log"]
        self.assertEqual("denied", events[-1]["action"])

    def test_correct_phrase_cooldown_then_active_then_relocked(self):
        result = override_manager.request_override(
            "test password",
            "app",
            "notepad.exe",
            "unlock with intention",
        )
        self.assertEqual(override_manager.STATUS_COOLDOWN, result["status"])

        data = config.load_config("test password")
        self.assertFalse(override_manager.is_overridden(data, "app", "notepad.exe", override_manager.utc_now()))
        future = override_manager.from_iso(result["ready_at"]) + timedelta(seconds=1)
        self.assertTrue(override_manager.is_overridden(data, "app", "notepad.exe", future))
        later = future + timedelta(minutes=11)
        override_manager.process_overrides(data, later)
        self.assertFalse(override_manager.is_overridden(data, "app", "notepad.exe", later))

    def test_url_path_rule_matches_only_path_prefix(self):
        url_rule_engine.add_path_rule("youtube.com", "/shorts", "test password")
        data = config.load_config("test password")

        blocked = url_rule_engine.match_url("https://www.youtube.com/shorts/abc", data)
        allowed = url_rule_engine.match_url("https://www.youtube.com/watch?v=abc", data)
        other_site = url_rule_engine.match_url("https://example.com/shorts/abc", data)

        self.assertTrue(blocked.blocked)
        self.assertFalse(allowed.blocked)
        self.assertFalse(other_site.blocked)


if __name__ == "__main__":
    unittest.main()
