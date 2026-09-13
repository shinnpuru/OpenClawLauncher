import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from openclaw_launcher.core.config import Config
from openclaw_launcher.core.install_manager import InstallManager
from openclaw_launcher.core.runtime_manager import RuntimeManager


class NodeRuntimeUpdatesTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for target, name, value in (
            (Config, "CONFIG_FILE", self.root / "config.json"),
            (Config, "BASE_DIR", self.root),
            (RuntimeManager, "RUNTIME_BASE_DIR", self.root / "runtime"),
        ):
            replacement = patch.object(target, name, value)
            replacement.start()
            self.addCleanup(replacement.stop)
        self.manager = RuntimeManager()

    def installed(self, *versions):
        for version in versions:
            path = self.manager.get_runtime_path(RuntimeManager.SOFTWARE_NODE, version)
            path.mkdir(parents=True)
            (path / "install_info.json").write_text('{}', encoding="utf-8")

    def test_engine_boundaries_and_prereleases(self):
        for version, expected in (
            ("22.22.2", False), ("24.15.0", False), ("24.16.0", True),
            ("24.20.1", True), ("25.9.0", False), ("26.0.0", False),
            ("26.1.0", True), ("v26.8.2", True), ("26.9.0-rc.1", False),
            ("invalid", False),
        ):
            with self.subTest(version=version):
                self.assertEqual(self.manager.is_supported_node_version(version), expected)

    def test_feed_is_filtered_sorted_and_cached(self):
        payload = [{"version": version, "date": "2026-09-09"} for version in (
            "v24.16.0", "v25.9.0", "v26.8.2", "v26.10.0", "v27.0.0-rc.1"
        )]
        response = Mock()
        response.read.return_value = json.dumps(payload).encode()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        with patch("urllib.request.urlopen", return_value=response):
            self.manager.refresh_available_versions(RuntimeManager.SOFTWARE_NODE)
        reloaded = RuntimeManager()
        self.assertEqual(
            [item["version"] for item in reloaded.get_available_versions(RuntimeManager.SOFTWARE_NODE)],
            ["26.10.0", "26.8.2", "24.16.0"],
        )
        self.assertIsNotNone(reloaded.get_available_versions_refreshed_at(RuntimeManager.SOFTWARE_NODE))

    def test_failed_refresh_preserves_cache(self):
        cached = [{"version": "26.8.2", "date": "2026-09-09"}]
        with patch.object(self.manager, "_fetch_node_versions", return_value=cached):
            self.manager.refresh_available_versions(RuntimeManager.SOFTWARE_NODE)
        with patch("urllib.request.urlopen", side_effect=OSError("offline")):
            self.manager.refresh_available_versions(RuntimeManager.SOFTWARE_NODE)
        self.assertEqual(self.manager.get_available_versions(RuntimeManager.SOFTWARE_NODE), cached)

    def test_latest_update_installs_then_selects_compatible_version(self):
        self.installed("25.9.0")
        self.manager.set_default_version(RuntimeManager.SOFTWARE_NODE, "25.9.0")
        calls = []
        def install(software, version, callback=None):
            calls.append((software, version))
            self.installed(version)
        with patch.object(self.manager, "_fetch_node_versions", return_value=[{"version": "26.8.2"}]), \
             patch.object(self.manager, "install_version", side_effect=install):
            self.assertEqual(self.manager.ensure_latest_node_runtime(), "26.8.2")
        self.assertEqual(calls, [(RuntimeManager.SOFTWARE_NODE, "26.8.2")])
        self.assertEqual(self.manager.get_default_version(RuntimeManager.SOFTWARE_NODE), "26.8.2")

    def test_offline_update_does_not_downgrade_installed_version(self):
        self.installed("26.8.2")
        with patch.object(self.manager, "_fetch_node_versions", return_value=[]):
            self.assertEqual(self.manager.ensure_latest_node_runtime(), "26.8.2")

    def test_failed_install_does_not_change_default(self):
        self.installed("24.16.0")
        self.manager.set_default_version(RuntimeManager.SOFTWARE_NODE, "24.16.0")
        with patch.object(self.manager, "_fetch_node_versions", return_value=[{"version": "26.8.2"}]), \
             patch.object(self.manager, "install_version", side_effect=OSError("download failed")):
            with self.assertRaises(OSError):
                self.manager.ensure_latest_node_runtime()
        self.assertEqual(self.manager.get_default_version(RuntimeManager.SOFTWARE_NODE), "24.16.0")

    def test_installer_rejects_node_25_and_selects_installed_24(self):
        self.installed("24.16.0", "25.9.0")
        self.manager.set_default_version(RuntimeManager.SOFTWARE_NODE, "25.9.0")
        (self.root / "package.json").write_text(
            json.dumps({"engines": {"node": ">=24.16.0 <25 || >=26.1.0"}}), encoding="utf-8"
        )
        with patch("openclaw_launcher.core.install_manager.RuntimeManager", return_value=self.manager) as factory:
            factory.SOFTWARE_NODE = RuntimeManager.SOFTWARE_NODE
            InstallManager.ensure_node_runtime(self.root)
        self.assertEqual(self.manager.get_default_version(RuntimeManager.SOFTWARE_NODE), "24.16.0")

    def test_malformed_cache_uses_compatible_fallback(self):
        Config.set_setting(RuntimeManager.NODE_VERSIONS_CONFIG_KEY, {"bad": "payload"})
        versions = RuntimeManager().get_available_versions(RuntimeManager.SOFTWARE_NODE)
        self.assertEqual(versions[0]["version"], "24.16.0")


if __name__ == "__main__":
    unittest.main()
