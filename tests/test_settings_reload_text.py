"""Guard the SpaNET options-flow text against stale restart instructions."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "spanet"


class OptionsReloadTextTests(unittest.TestCase):
    def test_options_strings_describe_integration_only_reload(self):
        for file in ("strings.json", "translations/en.json"):
            with self.subTest(file=file):
                data = json.loads((COMPONENT / file).read_text(encoding="utf-8"))
                description = data["options"]["step"]["settings"]["description"]
                self.assertIn("automatically reloads the SpaNET integration", description)
                self.assertIn("a full Home Assistant restart is not required", description)
                self.assertNotIn("changes require a Home Assistant restart", description)

    def test_options_flow_uses_ha_integration_reload(self):
        flow = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
        self.assertIn("class OptionsFlowHandler(OptionsFlowWithReload)", flow)


if __name__ == "__main__":
    unittest.main()
