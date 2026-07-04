import os
import tempfile
import unittest

import app_blocker
import config
import site_blocker


class RuleTests(unittest.TestCase):
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

    def test_app_rules_support_name_and_path(self):
        app_blocker.add_locked_app("Steam.exe", "test password")
        app_blocker.add_locked_app(r"C:\Games\App\game.exe", "test password")
        rules = app_blocker.list_locked_apps("test password")

        self.assertIn({"mode": "name", "value": "steam.exe"}, rules)
        self.assertTrue(any(rule["mode"] == "path" and rule["value"].endswith("game.exe") for rule in rules))

        app_blocker.remove_locked_app("steam.exe", "test password")
        remaining = app_blocker.list_locked_apps("test password")
        self.assertFalse(any(rule["value"] == "steam.exe" for rule in remaining))

    def test_site_rules_normalize_and_build_hosts_block(self):
        site_blocker.add_blocked_site("https://www.Example.com/watch", "test password")
        sites = site_blocker.list_blocked_sites("test password")
        self.assertEqual(["example.com"], sites)

        block = site_blocker.build_hosts_block(sites)
        self.assertIn("0.0.0.0 example.com", block)
        self.assertIn("0.0.0.0 www.example.com", block)

    def test_hosts_apply_and_rollback_only_touch_windslock_block(self):
        hosts = os.path.join(self.tempdir.name, "hosts")
        with open(hosts, "w", encoding="utf-8") as handle:
            handle.write("127.0.0.1 localhost\n")

        site_blocker.add_blocked_site("example.com", "test password")
        site_blocker.apply_hosts_block("test password", hosts)
        with open(hosts, "r", encoding="utf-8") as handle:
            applied = handle.read()
        self.assertIn(site_blocker.HOSTS_BEGIN, applied)
        self.assertIn("127.0.0.1 localhost", applied)

        site_blocker.rollback_hosts_block(hosts)
        with open(hosts, "r", encoding="utf-8") as handle:
            rolled_back = handle.read()
        self.assertIn("127.0.0.1 localhost", rolled_back)
        self.assertNotIn(site_blocker.HOSTS_BEGIN, rolled_back)


if __name__ == "__main__":
    unittest.main()
