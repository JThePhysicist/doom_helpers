import pytest
from PIL import Image

from doomwad import Wad
from doomwad.palette import Palette
from doomwad.sprites import encode_patch
from hudface.generator import StyleKnobs
from hudface.main import (
    build_arg_parser,
    find_matching_source,
    load_reference_sprite,
    main,
    process_target,
    read_target_filenames,
    run,
)


def _ramp_palette() -> Palette:
    colors = [(i, (i * 5) % 256, (i * 9) % 256) for i in range(256)]
    return Palette(colors)


def _wad_with_stf_lump(palette: Palette, lump_name: str) -> Wad:
    wad = Wad(wad_type="IWAD")
    playpal = b"".join(bytes(c) for c in palette.colors)
    wad.add("PLAYPAL", playpal)
    sprite_image = Image.new("RGBA", (4, 4), (*palette.rgb(5), 255))
    wad.add(lump_name, encode_patch(sprite_image, 2, 4, palette))
    return wad


def test_read_target_filenames_skips_blanks_and_comments(tmp_path):
    targets_file = tmp_path / "targets.txt"
    targets_file.write_text("STFST00.png\n\n# a comment\nSTFOUCH0.png\n   \n")
    assert read_target_filenames(targets_file) == ["STFST00.png", "STFOUCH0.png"]


def test_find_matching_source_returns_first_match_in_sorted_order(tmp_path, monkeypatch):
    for name in ["c.jpg", "a.jpg", "b.jpg"]:
        (tmp_path / name).write_bytes(b"")

    def fake_validate(path: str, state: object) -> str:
        if path.endswith("b.jpg"):
            return f"aligned:{path}"
        raise ValueError("no match")

    monkeypatch.setattr("hudface.main.geometry.validate_and_align", fake_validate)

    result = find_matching_source(tmp_path, state=object())
    assert result == f"aligned:{tmp_path / 'b.jpg'}"


def test_find_matching_source_returns_none_when_nothing_matches(tmp_path, monkeypatch):
    (tmp_path / "a.jpg").write_bytes(b"")

    def always_fails(path: str, state: object) -> str:
        raise ValueError("no match")

    monkeypatch.setattr("hudface.main.geometry.validate_and_align", always_fails)

    assert find_matching_source(tmp_path, state=object()) is None


def test_load_reference_sprite_decodes_the_matching_lump():
    palette = _ramp_palette()
    wad = _wad_with_stf_lump(palette, "STFST00")
    array = load_reference_sprite(wad, palette, "STFST00")
    assert array.shape == (4, 4, 3)


def test_process_target_skips_when_no_source_matches(tmp_path, monkeypatch):
    palette = _ramp_palette()
    wad = _wad_with_stf_lump(palette, "STFST00")
    (tmp_path / "sources").mkdir()

    monkeypatch.setattr(
        "hudface.main.geometry.validate_and_align",
        lambda path, state: (_ for _ in ()).throw(ValueError("no match")),
    )

    succeeded = process_target(
        "STFST00.png", tmp_path / "sources", wad, palette, tmp_path / "out"
    )
    assert succeeded is False
    assert not (tmp_path / "out" / "STFST00.png").exists()


def test_process_target_skips_when_reference_sprite_missing(tmp_path, monkeypatch):
    palette = _ramp_palette()
    wad = Wad(wad_type="IWAD")  # no STFST00 lump
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "photo.jpg").write_bytes(b"")

    monkeypatch.setattr(
        "hudface.main.geometry.validate_and_align", lambda path, state: "aligned"
    )

    succeeded = process_target("STFST00.png", sources, wad, palette, tmp_path / "out")
    assert succeeded is False


def test_process_target_generates_quantizes_and_saves(tmp_path, monkeypatch):
    palette = _ramp_palette()
    wad = _wad_with_stf_lump(palette, "STFST00")
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "photo.jpg").write_bytes(b"")

    calls = {}

    monkeypatch.setattr(
        "hudface.main.geometry.validate_and_align", lambda path, state: "aligned-face"
    )

    def fake_generate(aligned, reference_sprite, health_tier, expression, knobs=None):
        calls["generate"] = (aligned, health_tier, expression, knobs)
        return Image.new("RGB", (2, 2), (1, 2, 3))

    def fake_quantize(image, palette_arg, size=(24, 29)):
        calls["quantize"] = True
        return Image.new("RGB", (24, 29), (0, 255, 255))

    monkeypatch.setattr("hudface.main.generator.generate", fake_generate)
    monkeypatch.setattr("hudface.main.quantizer.quantize", fake_quantize)

    out_dir = tmp_path / "out"
    knobs = StyleKnobs(wound_intensity=4, tiredness=3, gore_level=1)
    succeeded = process_target("STFST00.png", sources, wad, palette, out_dir, knobs)

    assert succeeded is True
    assert calls["generate"] == ("aligned-face", 0, "ST", knobs)
    assert calls["quantize"] is True
    assert (out_dir / "STFST00.png").exists()


def test_run_reports_failures_but_keeps_processing_remaining_targets(tmp_path, monkeypatch):
    palette = _ramp_palette()
    wad = _wad_with_stf_lump(palette, "STFST00")
    wad_path = tmp_path / "doom.wad"
    wad_path.write_bytes(wad.to_bytes())

    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "photo.jpg").write_bytes(b"")

    targets_path = tmp_path / "targets.txt"
    # STFST00 has a reference sprite in the wad; STFOUCH0 does not, so it
    # should fail without blocking STFST00 from being produced.
    targets_path.write_text("STFST00.png\nSTFOUCH0.png\n")

    monkeypatch.setattr(
        "hudface.main.geometry.validate_and_align", lambda path, state: "aligned-face"
    )
    generate_calls = []
    monkeypatch.setattr(
        "hudface.main.generator.generate",
        lambda aligned, reference_sprite, health_tier, expression, knobs=None: (
            generate_calls.append(knobs) or Image.new("RGB", (2, 2), (1, 2, 3))
        ),
    )
    monkeypatch.setattr(
        "hudface.main.quantizer.quantize",
        lambda image, palette_arg, size=(24, 29): Image.new("RGB", (24, 29), (0, 255, 255)),
    )

    out_dir = tmp_path / "out"
    knobs = StyleKnobs(wound_intensity=2, tiredness=1, gore_level=3)
    failures = run(sources, targets_path, wad_path, out_dir, knobs)

    assert failures == ["STFOUCH0.png"]
    assert (out_dir / "STFST00.png").exists()
    assert not (out_dir / "STFOUCH0.png").exists()
    # knobs must reach generator.generate for every processed target.
    assert generate_calls == [knobs]


def test_arg_parser_defaults_leave_wound_intensity_auto_and_moderate_gore():
    args = build_arg_parser().parse_args(
        ["--sources-dir=s", "--targets=t", "--iwad=i", "--output-dir=o"]
    )
    assert args.wound_intensity is None
    assert args.tiredness == 0
    assert args.gore_level == 2


def test_arg_parser_accepts_explicit_knob_values():
    args = build_arg_parser().parse_args(
        [
            "--sources-dir=s",
            "--targets=t",
            "--iwad=i",
            "--output-dir=o",
            "--wound-intensity=4",
            "--tiredness=3",
            "--gore-level=1",
        ]
    )
    assert (args.wound_intensity, args.tiredness, args.gore_level) == (4, 3, 1)


def test_arg_parser_rejects_out_of_range_knob_values():
    with pytest.raises(SystemExit):
        build_arg_parser().parse_args(
            ["--sources-dir=s", "--targets=t", "--iwad=i", "--output-dir=o", "--gore-level=9"]
        )


def test_main_builds_style_knobs_from_cli_args_and_passes_to_run(tmp_path, monkeypatch):
    captured = {}

    def fake_run(sources_dir, targets_path, iwad_path, output_dir, knobs=None):
        captured["knobs"] = knobs
        return []

    monkeypatch.setattr("hudface.main.run", fake_run)

    exit_code = main(
        [
            "--sources-dir=s",
            "--targets=t",
            "--iwad=i",
            "--output-dir=o",
            "--wound-intensity=4",
            "--tiredness=2",
            "--gore-level=0",
        ]
    )

    assert exit_code == 0
    assert captured["knobs"] == StyleKnobs(wound_intensity=4, tiredness=2, gore_level=0)
