"""Create the Windows m_tree wheel without executing package managers."""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import os
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[2]
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip().replace("_", ".")
DIST_INFO = f"m_tree-{VERSION}.dist-info"
WHEEL_NAME = f"m_tree-{VERSION}-cp311-cp311-win_amd64.whl"
WHEEL_PATH = ROOT / "wheels" / WHEEL_NAME
NATIVE_PATH = ROOT / "m_tree" / "binaries" / "Release" / "m_tree.cp311-win_amd64.pyd"


def digest(data: bytes) -> str:
    encoded = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=")
    return f"sha256={encoded.decode('ascii')}"


def record_bytes(rows: list[tuple[str, str, str]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerows(rows)
    writer.writerow((f"{DIST_INFO}/RECORD", "", ""))
    return output.getvalue().encode("utf-8")


def build_wheel() -> Path:
    if sys.version_info[:2] != (3, 11):
        raise RuntimeError(f"Python 3.11 is required, got {sys.version.split()[0]}")
    if not NATIVE_PATH.is_file():
        raise FileNotFoundError(f"Native module was not built: {NATIVE_PATH}")

    native = NATIVE_PATH.read_bytes()
    if b"extract_foliage_anchors" not in native:
        raise RuntimeError("Native module is stale: foliage anchor binding is missing")

    files = {
        "m_tree/__init__.py": (ROOT / "m_tree" / "python_bindings" / "__init__.py").read_bytes(),
        "m_tree/m_tree.cp311-win_amd64.pyd": native,
        f"{DIST_INFO}/METADATA": (
            "Metadata-Version: 2.2\n"
            "Name: m_tree\n"
            f"Version: {VERSION}\n"
            "Summary: Procedural 3D tree generation library\n"
            "Requires-Python: >=3.11\n\n"
        ).encode("utf-8"),
        f"{DIST_INFO}/WHEEL": (
            "Wheel-Version: 1.0\n"
            "Generator: rbx-modular-tree-offline\n"
            "Root-Is-Purelib: false\n"
            "Tag: cp311-cp311-win_amd64\n\n"
        ).encode("utf-8"),
        f"{DIST_INFO}/licenses/LICENSE.md": (ROOT / "m_tree" / "LICENSE.md").read_bytes(),
    }

    rows = [(name, digest(data), str(len(data))) for name, data in files.items()]
    files[f"{DIST_INFO}/RECORD"] = record_bytes(rows)

    WHEEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = WHEEL_PATH.with_suffix(WHEEL_PATH.suffix + ".tmp")
    try:
        with ZipFile(temporary, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
            for name, data in files.items():
                archive.writestr(name, data)
        os.replace(temporary, WHEEL_PATH)
    finally:
        temporary.unlink(missing_ok=True)

    print(f"Created offline wheel: {WHEEL_PATH}")
    return WHEEL_PATH


if __name__ == "__main__":
    build_wheel()
