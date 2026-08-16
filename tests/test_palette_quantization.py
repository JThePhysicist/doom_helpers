# Direct tests of doomwad.palette.Palette.nearest_index -- this is the
# Euclidean-distance/PLAYPAL-mapping logic the hudface Phase 4 quantizer
# reuses (see hudface/quantizer.py:quantize_to_palette), so it's the
# mutation-testing target named by the QA spec for "Phase 4". Cases are
# chosen so that dropping/flipping any single channel's term in the
# distance formula, or the tie-break rule, changes the expected result.
from doomwad.palette import Palette


def test_exact_match_short_circuits_to_that_index():
    palette = Palette([(i, i, i) for i in range(256)])
    assert palette.nearest_index((42, 42, 42)) == 42


def test_nearest_neighbor_requires_all_three_channels():
    # Full 3-channel squared distance: (0,0,0) -> 16, (5,9,9) -> 163.
    # An r-only (or any single-channel) comparison would pick the wrong
    # index here, since on r alone (5,9,9) looks closer (1 vs 16).
    palette = Palette([(0, 0, 0), (5, 9, 9)] + [(0, 0, 0)] * 254)
    assert palette.nearest_index((4, 0, 0)) == 0


def test_nearest_neighbor_picks_closer_of_two_along_one_axis():
    palette = Palette([(0, 0, 0), (10, 0, 0), (20, 0, 0)] + [(0, 0, 0)] * 253)
    assert palette.nearest_index((14, 0, 0)) == 1


def test_tie_breaks_to_first_matching_index():
    palette = Palette([(0, 0, 0), (100, 100, 100), (102, 102, 102)] + [(0, 0, 0)] * 253)
    # (101,101,101) is equidistant (3) from indices 1 and 2 -- must pick
    # the lower index, not whichever the scan happens to see last.
    assert palette.nearest_index((101, 101, 101)) == 1


def test_duplicate_exact_colors_resolve_to_last_occurrence():
    palette = Palette([(9, 9, 9), (1, 1, 1), (9, 9, 9)] + [(0, 0, 0)] * 253)
    assert palette.nearest_index((9, 9, 9)) == 2


def test_nearest_index_result_is_cached_and_stable():
    palette = Palette([(0, 0, 0), (200, 0, 0)] + [(0, 0, 0)] * 254)
    first = palette.nearest_index((90, 0, 0))
    second = palette.nearest_index((90, 0, 0))
    assert first == second == 0
