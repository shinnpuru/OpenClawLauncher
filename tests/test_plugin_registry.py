import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from openclaw_launcher.core.plugin_manager import list_installed_plugins
from openclaw_launcher.core.config import Config
from openclaw_launcher.ui.panels.plugin_panel import PluginUninstallWorker


class PluginRegistryTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)

    def package(self, relative, name, version):
        root = self.home / relative
        root.mkdir(parents=True)
        (root / "package.json").write_text(json.dumps({"name": name, "version": version}))
        return root

    def read_plugins(self, records):
        result = Mock(returncode=0, stdout=json.dumps({"plugins": records}))
        with patch("openclaw_launcher.core.plugin_manager.InstallManager.get_runtime_env", return_value={}), \
             patch("openclaw_launcher.core.plugin_manager.InstallManager.resolve_runtime_tool", return_value="node"), \
             patch("openclaw_launcher.core.plugin_manager.subprocess.run", return_value=result):
            return list_installed_plugins(self.home, "test")

    def test_registry_excludes_uninstalled_projects_and_old_generations(self):
        self.package(".openclaw/npm/projects/old/node_modules/@openclaw/qqbot", "@openclaw/qqbot", "2026.6.5")
        self.package(".openclaw/npm/projects/weixin-old/node_modules/weixin", "weixin", "2.4.9")
        current = self.package(".openclaw/npm/projects/weixin-new/node_modules/weixin", "weixin", "2.4.10")
        plugins = self.read_plugins([
            {"id": "openclaw-weixin", "rootDir": str(current), "origin": "global", "version": "2.4.10"},
            {"id": "bundled", "rootDir": str(current), "origin": "bundled"},
        ])
        self.assertEqual(plugins, [{"id": "openclaw-weixin", "name": "weixin", "version": "2.4.10", "path": current}])
        # Even if the project still exists, uninstalling its registry entry removes the row.
        self.assertEqual(self.read_plugins([]), [])

    def test_registry_failure_is_not_reported_as_an_empty_success(self):
        with patch("openclaw_launcher.core.plugin_manager.InstallManager.get_runtime_env", return_value={}), \
             patch("openclaw_launcher.core.plugin_manager.InstallManager.resolve_runtime_tool", return_value="node"), \
             patch("openclaw_launcher.core.plugin_manager.subprocess.run", return_value=Mock(returncode=1, stderr="registry unavailable", stdout="")):
            with self.assertRaisesRegex(RuntimeError, "registry unavailable"):
                list_installed_plugins(self.home, "test")

    def test_uninstall_uses_plugin_id_after_gui_confirmation(self):
        process = Mock(stdout=iter(["Uninstalled plugin\n"]))
        process.wait.return_value = 0
        with patch.object(Config, "LOGS_DIR", self.home / "logs"), \
             patch("openclaw_launcher.ui.panels.plugin_panel.ProcessManager.get_status", return_value="Stopped"), \
             patch("openclaw_launcher.ui.panels.plugin_panel.InstallManager.get_runtime_env", return_value={}), \
             patch("openclaw_launcher.ui.panels.plugin_panel.InstallManager.resolve_runtime_tool", return_value="node"), \
             patch("openclaw_launcher.ui.panels.plugin_panel.subprocess.Popen", return_value=process) as popen:
            worker = PluginUninstallWorker(self.home, "test", "@vendor/package", self.home / "removed", "plugin-id")
            completed = Mock()
            worker.completed.connect(completed)
            worker.run()
            self.assertEqual(popen.call_args.args[0], ["node", "openclaw.mjs", "plugins", "uninstall", "plugin-id", "--force"])
            self.assertEqual(popen.call_args.kwargs["stdin"], subprocess.DEVNULL)
            completed.assert_called_once_with("@vendor/package", False, str(self.home / "removed"))


if __name__ == "__main__":
    unittest.main()
