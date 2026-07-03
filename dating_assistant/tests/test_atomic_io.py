import os
import unittest
import unittest.mock
from pathlib import Path
from tempfile import TemporaryDirectory

from src.atomic_io import atomic_write_text


class AtomicWriteTextTest(unittest.TestCase):
    def test_writes_content_and_leaves_no_temp(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            atomic_write_text(path, '{"a": 1}\n')

            self.assertEqual(path.read_text(encoding="utf-8"), '{"a": 1}\n')
            # 一時ファイル(.tmp)が残っていないこと
            leftovers = [p.name for p in Path(tmp).iterdir() if p.name != "data.json"]
            self.assertEqual(leftovers, [])

    def test_creates_parent_directories(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "deep" / "data.json"
            atomic_write_text(path, "ok")

            self.assertEqual(path.read_text(encoding="utf-8"), "ok")

    def test_overwrite_replaces_content(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            atomic_write_text(path, "OLD")
            atomic_write_text(path, "NEW")

            self.assertEqual(path.read_text(encoding="utf-8"), "NEW")

    def test_failure_during_replace_preserves_original(self):
        # 書き込み途中のクラッシュを os.replace の失敗で模擬し、
        # 元ファイルが torn write（破損・切り詰め）にならず維持されることを検証する。
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            atomic_write_text(path, "ORIGINAL")

            with unittest.mock.patch(
                "src.atomic_io.os.replace", side_effect=OSError("simulated crash")
            ):
                with self.assertRaises(OSError):
                    atomic_write_text(path, "SHOULD-NOT-APPEAR")

            # 元の内容が壊れずに残っていること
            self.assertEqual(path.read_text(encoding="utf-8"), "ORIGINAL")
            # 失敗時に一時ファイルが掃除されていること
            leftovers = [p.name for p in Path(tmp).iterdir() if p.name != "data.json"]
            self.assertEqual(leftovers, [])

    def test_failure_before_replace_does_not_create_target(self):
        # 新規ファイルの書き込みが replace 前に失敗した場合、対象ファイルは作られない
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "new.json"

            with unittest.mock.patch(
                "src.atomic_io.os.replace", side_effect=OSError("simulated crash")
            ):
                with self.assertRaises(OSError):
                    atomic_write_text(path, "DATA")

            self.assertFalse(path.exists())
            self.assertEqual(list(Path(tmp).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
