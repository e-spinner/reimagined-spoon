"""Emit a minimal PNG icon without third-party deps (for AppImage / .desktop)."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path


def _png_rgb(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    r, g, b = rgb
    row = b"\x00" + bytes([r, g, b] * width)
    raw = row * height

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def main() -> None:
    out = Path(__file__).resolve().parent / "homework-grader.png"
    out.write_bytes(_png_rgb(256, 256, (41, 128, 185)))
    print(out)


if __name__ == "__main__":
    main()
