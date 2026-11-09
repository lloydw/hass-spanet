"""Regression check: SpaNET manifest declares the JWT package it imports.

No Home Assistant runtime or cloud API calls are needed.
"""
from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "spanet"


class ManifestDependencyTests(unittest.TestCase):
    def test_pyjwt_is_declared_for_jwt_import(self):
        manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
        source = (COMPONENT / "spanet.py").read_text(encoding="utf-8")
        self.assertIn("import jwt", source)
        self.assertIn("pyjwt", [name.lower() for name in manifest["requirements"]])


if __name__ == "__main__":
    unittest.main()
