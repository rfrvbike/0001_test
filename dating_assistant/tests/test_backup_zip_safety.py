import io
import sys
import unittest
import unittest.mock
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import gui_streamlit_app


def _make_zip(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


class BackupZipSafetyTest(unittest.TestCase):
    def test_safe_entries_are_restored_under_data_local(self):
        with TemporaryDirectory() as tmp:
            app_dir = Path(tmp)
            with unittest.mock.patch.object(gui_streamlit_app, "APP_DIR", app_dir):
                zip_bytes = _make_zip({
                    "data/local/partners/partner_999.yaml": b"{}",
                    "data/local/user_profile.json": b"{}",
                })
                ok, msg = gui_streamlit_app._extract_backup_zip(zip_bytes)

            self.assertTrue(ok)
            self.assertTrue((app_dir / "data" / "local" / "partners" / "partner_999.yaml").exists())
            self.assertTrue((app_dir / "data" / "local" / "user_profile.json").exists())

    def test_zip_slip_entry_is_not_written_outside(self):
        with TemporaryDirectory() as tmp:
            app_dir = Path(tmp) / "app"
            app_dir.mkdir()
            # data/local/../../ は app_dir 直下に着地する（アプリ本体ファイルを上書きしうる脅威）。
            # data/local/../../../ は app_dir の外（tmp直下）へ脱出する。両方が書かれないことを検証。
            app_root_escape = (app_dir / "evil_app.txt").resolve()
            outside_escape = (Path(tmp) / "evil_outside.txt").resolve()
            with unittest.mock.patch.object(gui_streamlit_app, "APP_DIR", app_dir):
                zip_bytes = _make_zip({
                    "data/local/partners/partner_999.yaml": b"{}",           # 正常
                    "data/local/../../evil_app.txt": b"pwned",               # app_dir直下へ脱出
                    "data/local/../../../evil_outside.txt": b"pwned",        # app_dirの外へ脱出
                })
                ok, msg = gui_streamlit_app._extract_backup_zip(zip_bytes)

            # 正常エントリは復元され、脱出エントリはいずれも書かれずスキップされること
            self.assertTrue(ok)
            self.assertTrue((app_dir / "data" / "local" / "partners" / "partner_999.yaml").exists())
            self.assertFalse(app_root_escape.exists())
            self.assertFalse(outside_escape.exists())
            self.assertIn("スキップ", msg)

    def test_only_malicious_entry_is_rejected(self):
        with TemporaryDirectory() as tmp:
            app_dir = Path(tmp) / "app"
            app_dir.mkdir()
            app_root_escape = (app_dir / "evil_app.txt").resolve()
            with unittest.mock.patch.object(gui_streamlit_app, "APP_DIR", app_dir):
                zip_bytes = _make_zip({
                    "data/local/../../evil_app.txt": b"pwned",
                })
                ok, msg = gui_streamlit_app._extract_backup_zip(zip_bytes)

            self.assertFalse(ok)
            self.assertFalse(app_root_escape.exists())

    def test_zip_without_data_local_is_rejected(self):
        with TemporaryDirectory() as tmp:
            app_dir = Path(tmp) / "app"
            app_dir.mkdir()
            with unittest.mock.patch.object(gui_streamlit_app, "APP_DIR", app_dir):
                zip_bytes = _make_zip({"other/file.txt": b"x"})
                ok, msg = gui_streamlit_app._extract_backup_zip(zip_bytes)

            self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
