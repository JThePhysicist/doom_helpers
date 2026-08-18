from __future__ import annotations

from doomface.parser import iter_standard_stf_filenames, parse_stf_filename


def test_iter_standard_stf_filenames_has_exactly_42_entries() -> None:
    names = iter_standard_stf_filenames()
    assert len(names) == 42
    assert len(set(names)) == 42  # all unique


def test_every_standard_filename_round_trips_through_the_parser() -> None:
    for name in iter_standard_stf_filenames():
        parse_stf_filename(name)  # must not raise
