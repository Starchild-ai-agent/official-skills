"""exports.py must load however a caller imports it.

Task scripts load it with importlib.util.spec_from_file_location, where the
skill directory is NOT on sys.path. 2.14.0 broke this with a bare sibling
import (ModuleNotFoundError: site_tools) and took every export down with it.
"""
import importlib.util
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTS = os.path.join(HERE, "exports.py")

PROBE = """
import importlib.util, sys, types
# stub the platform client so the test runs outside the agent runtime
core = types.ModuleType("core"); hc = types.ModuleType("core.http_client")
hc.proxied_get = hc.proxied_post = lambda *a, **k: None
core.http_client = hc; sys.modules["core"] = core; sys.modules["core.http_client"] = hc
spec = importlib.util.spec_from_file_location("skill_web_crawler", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
assert callable(m.scrape_markdown) and callable(m.fetch)
assert m.fetch.__module__ == "web_crawler_site_tools", m.fetch.__module__
print("ok")
"""


class ExportsLoadingTests(unittest.TestCase):
    def test_path_load_without_skill_dir_on_sys_path(self):
        # fresh interpreter, cwd outside the skill dir, skill dir not on sys.path
        r = subprocess.run([sys.executable, "-c", PROBE, EXPORTS], cwd="/",
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        self.assertIn("ok", r.stdout)


if __name__ == "__main__":
    unittest.main()
