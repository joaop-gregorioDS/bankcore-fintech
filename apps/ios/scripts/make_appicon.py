"""App icon = login BrandMark: gold rounded square + shield on Carbon ink."""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "BankCore" / "Assets.xcassets" / "AppIcon.appiconset" / "AppIcon.png"

INK = (11, 11, 12)
GOLD = (196, 163, 90)
SIZE = 1024


def quad(p0, p1, p2, steps: int = 18):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        pts.append((
            u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
            u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1],
        ))
    return pts


def shield_path(cx: float, cy: float, w: float, h: float) -> list[tuple[float, float]]:
    left, right = cx - w / 2, cx + w / 2
    top = cy - h * 0.46
    bottom = cy + h * 0.50
    r = w * 0.22
    waist = cy + h * 0.08
    pts: list[tuple[float, float]] = []
    pts += quad((left + r, top), (left, top), (left, top + r))
    pts.append((left, waist))
    pts += quad((left, waist), (left + w * 0.06, bottom - h * 0.12), (cx, bottom))
    pts += quad((cx, bottom), (right - w * 0.06, bottom - h * 0.12), (right, waist))
    pts.append((right, top + r))
    pts += quad((right, top + r), (right, top), (right - r, top))
    pts.append((left + r, top))
    return pts


def stroke_path(draw: ImageDraw.ImageDraw, pts: list[tuple[float, float]], width: int) -> None:
    draw.line(pts, fill=GOLD, width=width, joint="curve")
    # round line caps
    r = width / 2
    for x, y in (pts[0], pts[-1]):
        draw.ellipse((x - r, y - r, x + r, y + r), fill=GOLD)


def main() -> None:
    img = Image.new("RGB", (SIZE, SIZE), INK)
    draw = ImageDraw.Draw(img)

    # Login mark: rounded square, inset so the iOS squircle does not clip the stroke.
    inset = 188
    radius = 118
    box = (inset, inset, SIZE - inset, SIZE - inset)
    stroke = 22
    draw.rounded_rectangle(box, radius=radius, outline=GOLD, width=stroke)

    path = shield_path(SIZE / 2, SIZE / 2 + 6, 300, 340)
    stroke_path(draw, path, 22)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "PNG")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
