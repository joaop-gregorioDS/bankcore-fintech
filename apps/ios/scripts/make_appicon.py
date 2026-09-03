"""Carbon Ledger app icon — 1024×1024, no alpha (App Store)."""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "BankCore" / "Assets.xcassets" / "AppIcon.appiconset" / "AppIcon.png"

INK = (11, 11, 12)
GOLD = (196, 163, 90)


def main() -> None:
    img = Image.new("RGB", (1024, 1024), INK)
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle((118, 118, 906, 906), radius=196, outline=GOLD, width=18)

    # Ledger: spine + three bars
    draw.rounded_rectangle((470, 300, 554, 724), radius=18, fill=GOLD)
    for i, half in enumerate((250, 200, 150)):
        y = 360 + i * 110
        draw.rounded_rectangle((512 - half, y, 512 + half, y + 36), radius=12, fill=GOLD)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "PNG")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
