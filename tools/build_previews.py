#!/usr/bin/env python3
"""Build README preview assets from Codex Anime Pets spritesheets."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
PETS_DIR = ROOT / "pets"
ASSETS_DIR = ROOT / "assets"
PREVIEW_DIR = ASSETS_DIR / "previews"
GALLERY_DIR = ASSETS_DIR / "gallery"
CATALOG_PATH = ROOT / "catalog.json"

CELL_W = 192
CELL_H = 208
IDLE_FRAMES = 6


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def alpha_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    alpha = image.getchannel("A")
    bbox = alpha.point(lambda value: 255 if value > 8 else 0).getbbox()
    return bbox or (0, 0, image.width, image.height)


def crop_idle_frame(atlas: Image.Image, frame_index: int = 0) -> Image.Image:
    frames = []
    for col in range(IDLE_FRAMES):
        frame = atlas.crop((col * CELL_W, 0, (col + 1) * CELL_W, CELL_H))
        frames.append(frame)

    # Use a union box across idle frames so the preview stays centered.
    boxes = [alpha_bbox(frame) for frame in frames]
    left = min(box[0] for box in boxes)
    top = min(box[1] for box in boxes)
    right = max(box[2] for box in boxes)
    bottom = max(box[3] for box in boxes)
    return frames[frame_index].crop((left, top, right, bottom))


def render_preview(sprite: Image.Image, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    card = Image.new("RGBA", (360, 360), (246, 247, 251, 255))
    draw = ImageDraw.Draw(card)

    # Soft checker dots make transparent sprites readable on GitHub.
    for y in range(0, 360, 24):
        for x in range(0, 360, 24):
            fill = (236, 239, 246, 255) if (x // 24 + y // 24) % 2 else (250, 251, 253, 255)
            draw.rounded_rectangle((x + 3, y + 3, x + 18, y + 18), radius=4, fill=fill)

    bbox = alpha_bbox(sprite)
    sprite = sprite.crop(bbox)
    scale = min(280 / sprite.width, 286 / sprite.height)
    scale = max(1, int(scale))
    resized = sprite.resize((sprite.width * scale, sprite.height * scale), Image.Resampling.NEAREST)
    x = (card.width - resized.width) // 2
    y = (card.height - resized.height) // 2 - 4
    card.alpha_composite(resized, (x, y))
    card.save(output)


def render_gallery(entries: list[dict[str, str]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    cols = 4
    card_w = 300
    card_h = 350
    gap = 28
    margin = 48
    title_h = 124
    rows = (len(entries) + cols - 1) // cols
    width = margin * 2 + cols * card_w + (cols - 1) * gap
    height = margin * 2 + title_h + rows * card_h + (rows - 1) * gap

    image = Image.new("RGBA", (width, height), (250, 250, 252, 255))
    draw = ImageDraw.Draw(image)
    title_font = load_font(48)
    label_font = load_font(25)
    small_font = load_font(17)

    draw.text((margin, 36), "Codex Anime Pets", fill=(28, 31, 40, 255), font=title_font)
    draw.text(
        (margin, 94),
        "Tiny chibi companions for the Codex desktop app",
        fill=(91, 96, 112, 255),
        font=small_font,
    )

    palette = [
        (255, 244, 229, 255),
        (235, 248, 255, 255),
        (243, 240, 255, 255),
        (236, 252, 244, 255),
        (255, 241, 242, 255),
        (239, 246, 255, 255),
    ]

    for idx, entry in enumerate(entries):
        row = idx // cols
        col = idx % cols
        x = margin + col * (card_w + gap)
        y = margin + title_h + row * (card_h + gap)
        bg = palette[idx % len(palette)]

        draw.rounded_rectangle((x, y, x + card_w, y + card_h), radius=22, fill=bg)
        draw.rounded_rectangle((x, y, x + card_w, y + card_h), radius=22, outline=(220, 224, 235, 255), width=2)

        preview = Image.open(PREVIEW_DIR / f"{entry['id']}.png").convert("RGBA")
        preview = preview.resize((216, 216), Image.Resampling.LANCZOS)
        image.alpha_composite(preview, (x + 42, y + 28))

        name = entry["displayName"]
        if text_width(draw, name, label_font) > card_w - 34:
            name = entry["id"]
        name_w = text_width(draw, name, label_font)
        draw.text((x + (card_w - name_w) / 2, y + 266), name, fill=(30, 34, 46, 255), font=label_font)

        slug = entry["id"]
        slug_w = text_width(draw, slug, small_font)
        draw.text((x + (card_w - slug_w) / 2, y + 304), slug, fill=(96, 102, 120, 255), font=small_font)

    image.convert("RGB").save(output, quality=94)


def main() -> None:
    entries: list[dict[str, str]] = []
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    GALLERY_DIR.mkdir(parents=True, exist_ok=True)

    for pet_json in sorted(PETS_DIR.glob("*/pet.json")):
        pet_dir = pet_json.parent
        sprite_path = pet_dir / "spritesheet.webp"
        if not sprite_path.exists():
            continue
        data = json.loads(pet_json.read_text(encoding="utf-8"))
        pet_id = data["id"]
        display_name = data.get("displayName", pet_id)
        description = data.get("description", "")

        atlas = Image.open(sprite_path).convert("RGBA")
        idle = crop_idle_frame(atlas)
        render_preview(idle, PREVIEW_DIR / f"{pet_id}.png")
        entries.append(
            {
                "id": pet_id,
                "displayName": display_name,
                "description": description,
                "package": f"pets/{pet_id}/",
                "preview": f"assets/previews/{pet_id}.png",
                "contactSheet": f"assets/contact-sheets/{pet_id}.png",
            }
        )

    render_gallery(entries, GALLERY_DIR / "codex-anime-pets-gallery.jpg")
    CATALOG_PATH.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
