"""Copy the iOS cream+gold AppIcon into Android mipmaps and adaptive icons."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "ios" / "BankCore" / "Assets.xcassets" / "AppIcon.appiconset" / "AppIcon.png"
RES = ROOT / "android" / "app" / "src" / "main" / "res"

SIZES = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}

FOREGROUND = {
    "mipmap-mdpi": 108,
    "mipmap-hdpi": 162,
    "mipmap-xhdpi": 216,
    "mipmap-xxhdpi": 324,
    "mipmap-xxxhdpi": 432,
}


def main() -> None:
    src = Image.open(SRC).convert("RGBA")
    for folder, size in SIZES.items():
        out_dir = RES / folder
        out_dir.mkdir(parents=True, exist_ok=True)
        resized = src.resize((size, size), Image.Resampling.LANCZOS)
        resized.save(out_dir / "ic_launcher.png", "PNG")
        resized.save(out_dir / "ic_launcher_round.png", "PNG")
        print(f"wrote {out_dir / 'ic_launcher.png'}")

    for folder, size in FOREGROUND.items():
        out_dir = RES / folder
        out_dir.mkdir(parents=True, exist_ok=True)
        resized = src.resize((size, size), Image.Resampling.LANCZOS)
        resized.save(out_dir / "ic_launcher_foreground.png", "PNG")
        print(f"wrote {out_dir / 'ic_launcher_foreground.png'}")

    anydpi = RES / "mipmap-anydpi-v26"
    anydpi.mkdir(parents=True, exist_ok=True)
    xml = """<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/ic_launcher_background"/>
    <foreground android:drawable="@mipmap/ic_launcher_foreground"/>
</adaptive-icon>
"""
    (anydpi / "ic_launcher.xml").write_text(xml, encoding="utf-8")
    (anydpi / "ic_launcher_round.xml").write_text(xml, encoding="utf-8")
    print("wrote adaptive icons")


if __name__ == "__main__":
    main()
