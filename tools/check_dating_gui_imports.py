from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
APP_DIR = ROOT_DIR / "dating_assistant"
APP_FILE = APP_DIR / "gui_streamlit_app.py"


def _gui_helper_import_names() -> list[str]:
    tree = ast.parse(APP_FILE.read_text(encoding="utf-8"), filename=str(APP_FILE))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "gui_helpers":
            for alias in node.names:
                names.append(alias.name)
    return sorted(set(names))


def main() -> int:
    if str(APP_DIR) not in sys.path:
        sys.path.insert(0, str(APP_DIR))

    helper_names = _gui_helper_import_names()
    helpers = importlib.import_module("gui_helpers")
    missing = [name for name in helper_names if not hasattr(helpers, name)]
    if missing:
        print("[ERROR] gui_helpers missing imports required by gui_streamlit_app.py:")
        for name in missing:
            print(f"  - {name}")
        return 1

    try:
        importlib.import_module("gui_streamlit_app")
    except Exception as exc:
        print("[ERROR] gui_streamlit_app import failed:")
        print(f"{type(exc).__name__}: {exc}")
        return 1

    print("GUI import preflight OK")
    print(f"gui_helpers: {helpers.__file__}")
    print(f"checked imports: {len(helper_names)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
