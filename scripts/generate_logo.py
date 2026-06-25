"""Generate a minimalist Shadow Fiend logo for shadow_fiend project.

Style reference: OpenClaw lobster logo — minimal, geometric, high contrast,
strong visual memory, works at small sizes (menu bar icon).

Shadow Fiend visual direction:
- Hooded dark silhouette with wide shoulders
- Two piercing green eyes separated in the void
- Two curved demonic horns
- Subtle skull jawline
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


def draw_shadow_fiend_logo(size: int = 512, output_path: str | Path = "assets/logo.png") -> Path:
    """Draw a minimal Shadow Fiend avatar and save as PNG."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Palette.
    bg_color = (10, 6, 14)           # deep void
    hood_color = (24, 16, 34)        # dark hood
    hood_inner = (6, 4, 10)          # inner void
    horn_color = (55, 35, 75)        # muted purple horn
    eye_outer = (20, 170, 75)        # green glow outer
    eye_mid = (55, 235, 115)         # green glow mid
    eye_inner = (160, 255, 190)      # bright core
    jaw_color = (18, 12, 26)         # subtle jaw shadow
    grin_color = (60, 50, 70)        # subtle grin

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2
    r = size // 2 - 4

    # 1. Circular background.
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=bg_color)

    # 2. Hood: wide rounded silhouette.
    hood_top = cy - int(r * 0.78)
    hood_bottom = cy + int(r * 0.58)
    hood_w = int(r * 0.85)
    hood_points = [
        (cx, hood_top),
        (cx + hood_w, hood_bottom),
        (cx + int(r * 0.30), cy + int(r * 0.42)),
        (cx, cy + int(r * 0.35)),
        (cx - int(r * 0.30), cy + int(r * 0.42)),
        (cx - hood_w, hood_bottom),
    ]
    draw.polygon(hood_points, fill=hood_color)

    # 3. Face void: the dark area inside the hood.
    void_top = cy - int(r * 0.32)
    void_bottom = cy + int(r * 0.52)
    void_w = int(r * 0.48)
    draw.pieslice(
        [cx - void_w, void_top - void_w, cx + void_w, void_top + void_w],
        start=0,
        end=180,
        fill=hood_inner,
    )
    draw.rectangle([cx - void_w, void_top, cx + void_w, void_bottom], fill=hood_inner)
    draw.pieslice(
        [cx - void_w, void_bottom - void_w, cx + void_w, void_bottom + void_w],
        start=180,
        end=360,
        fill=hood_inner,
    )

    # 4. Horns: thicker curved spikes.
    horn_base_y = hood_top + int(r * 0.50)
    horn_tip_y = hood_top - int(r * 0.42)
    horn_w = int(r * 0.14)
    left_horn = [
        (cx - int(r * 0.34), horn_base_y),
        (cx - int(r * 0.52) - horn_w, horn_tip_y),
        (cx - int(r * 0.20), horn_base_y + int(r * 0.08)),
    ]
    right_horn = [
        (cx + int(r * 0.34), horn_base_y),
        (cx + int(r * 0.52) + horn_w, horn_tip_y),
        (cx + int(r * 0.20), horn_base_y + int(r * 0.08)),
    ]
    draw.polygon(left_horn, fill=horn_color)
    draw.polygon(right_horn, fill=horn_color)

    # 5. Eyes: separated glowing ovals, high on the face.
    eye_rx, eye_ry = int(r * 0.11), int(r * 0.075)
    eye_y = cy - int(r * 0.06)
    left_eye_cx = cx - int(r * 0.24)
    right_eye_cx = cx + int(r * 0.24)

    def draw_eye(center_x: int, center_y: int, rx: int, ry: int) -> None:
        nonlocal img, draw
        for factor, color in [(2.6, (*eye_outer, 50)), (1.8, (*eye_mid, 100)), (1.0, eye_mid)]:
            if len(color) == 4:
                layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
                layer_draw = ImageDraw.Draw(layer)
                layer_draw.ellipse(
                    [
                        center_x - int(rx * factor),
                        center_y - int(ry * factor),
                        center_x + int(rx * factor),
                        center_y + int(ry * factor),
                    ],
                    fill=color,
                )
                img = Image.alpha_composite(img, layer)
                draw = ImageDraw.Draw(img)
            else:
                draw.ellipse(
                    [center_x - int(rx * factor), center_y - int(ry * factor),
                     center_x + int(rx * factor), center_y + int(ry * factor)],
                    fill=color,
                )
        draw.ellipse(
            [center_x - rx // 2, center_y - ry // 2, center_x + rx // 2, center_y + ry // 2],
            fill=eye_inner,
        )

    draw_eye(left_eye_cx, eye_y, eye_rx, eye_ry)
    draw_eye(right_eye_cx, eye_y, eye_rx, eye_ry)

    # 6. Skull jawline: subtle lighter shape below eyes.
    jaw_top = cy + int(r * 0.12)
    jaw_bottom = cy + int(r * 0.46)
    jaw_w = int(r * 0.22)
    draw.pieslice(
        [cx - jaw_w, jaw_top - jaw_w, cx + jaw_w, jaw_top + jaw_w],
        start=0,
        end=180,
        fill=jaw_color,
    )
    draw.rectangle([cx - jaw_w, jaw_top, cx + jaw_w, jaw_bottom], fill=jaw_color)
    draw.pieslice(
        [cx - jaw_w, jaw_bottom - jaw_w, cx + jaw_w, jaw_bottom + jaw_w],
        start=180,
        end=360,
        fill=jaw_color,
    )

    # 7. Subtle grin.
    grin_top = cy + int(r * 0.28)
    grin_bottom = cy + int(r * 0.38)
    draw.arc(
        [cx - int(r * 0.14), grin_top, cx + int(r * 0.14), grin_bottom],
        start=15,
        end=165,
        fill=grin_color,
        width=max(2, size // 128),
    )

    img.save(output_path)
    return output_path


if __name__ == "__main__":
    base = Path(__file__).parent.parent / "assets"
    for sz in [1024, 512, 256, 128, 64, 32, 16]:
        out = base / f"logo_{sz}.png"
        draw_shadow_fiend_logo(size=sz, output_path=out)
        print(f"Generated {out}")
