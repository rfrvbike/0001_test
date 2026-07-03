from __future__ import annotations

import os
import tempfile
from pathlib import Path


def atomic_write_text(path: str | Path, text: str, encoding: str = "utf-8") -> None:
    """テキストを原子的にファイルへ書き込む。

    同じディレクトリに一時ファイルを作り、flush + fsync してから os.replace で
    差し替える。書き込み途中でクラッシュ・ディスクフルが起きても、元ファイルは
    torn write（切り詰め・半端な内容）にならず、直前の内容が保たれる。

    留意点:
    - ディレクトリ自体の fsync は行わない（Windows では非対応のため）。
      目的である「破損・切り詰めファイルを作らない」は temp + os.replace で達成する。
      完全な電源断耐性（ディレクトリエントリの永続化）まではここでは保証しない。
    - OneDrive などが対象ファイルを同期ロックしている場合、os.replace は失敗しうるが、
      これは従来の write_text でも同様に失敗する挙動で、悪化はしない。
      むしろ書きかけファイルが残る torn write は防げる。
    - 改行コードは write_text と同じ扱い（newline=None）にして既存ファイルの挙動を変えない。
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        # os.replace 前の失敗なら元ファイルは無傷。一時ファイルを掃除して例外を伝播する。
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
