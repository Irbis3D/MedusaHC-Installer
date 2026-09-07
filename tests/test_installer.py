import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import medusahc_installer as installer


class LauncherTests(unittest.TestCase):
    def test_official_entrypoints_and_privileges(self):
        for key in ("core", "calibrate", "control", "mainsail"):
            item = installer.component(key)
            suffix = "install.sh" if key == "mainsail" else "install-online.sh"
            self.assertTrue(item.installer_url.endswith("/" + suffix))
            with patch.object(installer, "dependency_ready", return_value=True), \
                 patch.object(installer, "confirm", return_value=True), \
                 patch.object(installer, "header"), patch.object(installer, "pause"), \
                 patch.object(installer.urllib.request, "urlopen", return_value=io.BytesIO(b"#!/bin/sh\n")), \
                 patch.object(installer.subprocess, "run", return_value=Mock(returncode=0)) as run:
                installer.run_installer(item, "uninstall")
                args = run.call_args.args[0]
                self.assertEqual(args[0], "sudo" if key == "control" else "bash")
                self.assertEqual(args[-1], "uninstall")
                self.assertFalse(Path(args[-2]).exists(), "Temporary download was not removed")

    def test_manifest_detects_mainsail_outside_standard_directory(self):
        with tempfile.TemporaryDirectory() as root:
            manifest = Path(root) / "manifest.json"
            manifest.write_text('{"mainsail":{"installed":true}}', encoding="utf-8")
            item = installer.Component("mainsail", "Mainsail", "", "", (manifest,))
            self.assertTrue(installer.installed(item))
