"""Guard against redeclaring Home Assistant built-in dependencies.

Hassfest rejects pyjwt and requests in custom integration requirements
because Home Assistant already provides these packages. The integration
can still import jwt from the installed HA runtime.
"""
from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "spanet"


class ManifestDependencyTests(unittest.TestCase):
    def test_home_assistant_builtin_packages_not_redeclared(self):
        manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
        requirements = [name.lower() for name in manifest["requirements"]]
        self.assertNotIn("pyjwt", requirements)
        self.assertNotIn("requests", requirements)

    def test_jwt_import_still_present(self):
        source = (COMPONENT / "spanet.py").read_text(encoding="utf-8")
        self.assertIn("import jwt", source)


if __name__ == "__main__":
    unittest.main()
