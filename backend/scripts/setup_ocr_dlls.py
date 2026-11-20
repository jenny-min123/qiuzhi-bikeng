"""Windows OCR 运行库准备（仅 onnxruntime 报 MSVCP140_1.dll 缺失时需要）。

从 PyPI 的 msvc-runtime wheel 中提取 VC++ 运行库到 backend/vendor/msvc，
供 app/ocr.py 在导入 onnxruntime 前加入 DLL 搜索目录。

运行：cd backend && python scripts/setup_ocr_dlls.py

运行库 DLL 体积约 2.4MB，已加入 .gitignore，不提交到仓库。
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

TARGET = Path(__file__).resolve().parent.parent / "vendor" / "msvc"


def main() -> int:
    if sys.platform != "win32":
        print("只有 Windows 需要这一步；其他系统直接用系统或发行版提供的运行库。")
        return 0

    TARGET.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        print("正在下载 msvc-runtime wheel…")
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "download",
                "--no-deps",
                "--quiet",
                "--dest",
                tmp,
                "msvc-runtime",
            ]
        )
        wheels = list(Path(tmp).glob("msvc_runtime-*.whl"))
        if not wheels:
            print("未下载到 msvc-runtime wheel")
            return 1

        count = 0
        with zipfile.ZipFile(wheels[0]) as archive:
            for member in archive.namelist():
                if member.lower().endswith(".dll"):
                    target = TARGET / Path(member).name
                    target.write_bytes(archive.read(member))
                    count += 1

    print(f"已提取 {count} 个 DLL 到 {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
