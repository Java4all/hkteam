"""Generate favicon.ico and favicon.png from public/favicon.svg (build-time helper)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
SVG = PUBLIC / "favicon.svg"


def main() -> None:
    if not SVG.is_file():
        raise SystemExit(f"Missing {SVG}")

    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise SystemExit("Install Pillow: pip install pillow") from exc

    sizes = [(16, 16), (32, 32), (48, 48)]
    images: list[Image.Image] = []
    for size in sizes:
        im = Image.new("RGBA", size, (15, 23, 42, 255))
        draw = ImageDraw.Draw(im)
        w, h = size
        cx, cy = w // 2, h // 2
        r = max(1, min(w, h) // 8)
        pts = [
            (cx, int(h * 0.17)),
            (int(w * 0.73), int(h * 0.31)),
            (int(w * 0.73), int(h * 0.69)),
            (cx, int(h * 0.83)),
            (int(w * 0.27), int(h * 0.69)),
            (int(w * 0.27), int(h * 0.31)),
        ]
        draw.polygon(pts, outline=(8, 145, 178), width=max(1, w // 16))
        draw.ellipse(
            (cx - r, cy - r, cx + r, cy + r),
            fill=(8, 145, 178),
        )
        images.append(im)

    png_path = PUBLIC / "favicon.png"
    ico_path = PUBLIC / "favicon.ico"
    images[-1].save(png_path, format="PNG")
    images[0].save(
        ico_path,
        format="ICO",
        sizes=[(im.width, im.height) for im in images],
        append_images=images[1:],
    )
    print(f"Wrote {png_path} and {ico_path}")


if __name__ == "__main__":
    main()
