import subprocess
import sys
from pathlib import Path

from PIL import Image

from doomwad.palette import Palette
from doomwad.sprites import encode_patch
from doomwad.wad import Wad

REPO_ROOT = Path(__file__).resolve().parent.parent
EXTRACT_SCRIPT = REPO_ROOT / "scripts" / "extract_sprite_atlas.py"
REBUILD_SCRIPT = REPO_ROOT / "scripts" / "rebuild_sprite_atlas.py"


def _grayscale_palette() -> Palette:
    return Palette([(i, i, i) for i in range(256)])


def _build_source_wad(path: Path) -> dict:
    palette = _grayscale_palette()
    playpal = bytes(c for rgb in palette.colors for c in rgb)

    sprites = {
        "TROOA1": Image.new("RGBA", (60, 90), (100, 100, 100, 255)),
        "TROOA2A8": Image.new("RGBA", (60, 90), (110, 110, 110, 255)),
        "TROOB1": Image.new("RGBA", (65, 95), (120, 120, 120, 255)),
    }

    wad = Wad(wad_type="PWAD")
    wad.add("PLAYPAL", playpal)
    wad.add("S_START", b"")
    for name, image in sprites.items():
        wad.add(name, encode_patch(image, 30, 90, palette))
    wad.add("S_END", b"")
    wad.save(path)
    return sprites


def test_extract_then_rebuild_round_trip(tmp_path):
    source_wad = tmp_path / "source.wad"
    original_sprites = _build_source_wad(source_wad)

    atlas_dir = tmp_path / "atlas"
    result = subprocess.run(
        [
            sys.executable,
            str(EXTRACT_SCRIPT),
            "--wad",
            str(source_wad),
            "--sprite",
            "TROO",
            "--output-dir",
            str(atlas_dir),
            "--atlas-size",
            "1024",
            "--padding",
            "2",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    manifest_path = atlas_dir / "TROO_manifest.json"
    assert manifest_path.exists()
    page_pngs = list(atlas_dir.glob("TROO_*.png"))
    assert len(page_pngs) == 1  # three small sprites easily fit on one page

    output_wad = tmp_path / "rebuilt.wad"
    result = subprocess.run(
        [
            sys.executable,
            str(REBUILD_SCRIPT),
            "--manifest",
            str(manifest_path),
            "--output",
            str(output_wad),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    rebuilt = Wad.load(output_wad)
    for name in original_sprites:
        assert name in rebuilt

    palette = _grayscale_palette()
    from doomwad.sprites import decode_patch

    for name, original_image in original_sprites.items():
        decoded = decode_patch(name, rebuilt.find(name).data, palette)
        assert decoded.image.size == original_image.size
        assert decoded.left_offset == 30
        assert decoded.top_offset == 90
        assert decoded.image.getpixel((5, 5)) == original_image.getpixel((5, 5))
