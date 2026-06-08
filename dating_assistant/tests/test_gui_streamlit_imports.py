import ast
import importlib
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = APP_DIR.parent
TOOLS_DIR = ROOT_DIR / "tools"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))


class GuiStreamlitImportTests(unittest.TestCase):
    def test_gui_helpers_exports_every_name_imported_by_streamlit_app(self):
        app_file = APP_DIR / "gui_streamlit_app.py"
        tree = ast.parse(app_file.read_text(encoding="utf-8"), filename=str(app_file))
        imported_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "gui_helpers":
                imported_names.extend(alias.name for alias in node.names)

        helpers = importlib.import_module("gui_helpers")
        missing = sorted(name for name in imported_names if not hasattr(helpers, name))

        self.assertEqual(missing, [])
        self.assertIn("build_profile_save_payload", imported_names)

    def test_gui_streamlit_app_imports_without_import_error(self):
        module = importlib.import_module("gui_streamlit_app")

        self.assertTrue(hasattr(module, "main"))

    def test_preflight_script_passes(self):
        preflight = importlib.import_module("check_dating_gui_imports")

        self.assertEqual(preflight.main(), 0)


if __name__ == "__main__":
    unittest.main()
