from doomwad import Lump, LumpNotFoundError, Wad


def test_round_trip_empty_wad():
    wad = Wad(wad_type="PWAD")
    data = wad.to_bytes()

    loaded = Wad.from_bytes(data)
    assert loaded.wad_type == "PWAD"
    assert len(loaded.lumps) == 0


def test_round_trip_with_lumps():
    wad = Wad(wad_type="PWAD")
    wad.add("MYLUMP", b"hello world")
    wad.add("OTHER", b"\x01\x02\x03")

    data = wad.to_bytes()
    loaded = Wad.from_bytes(data)

    assert len(loaded.lumps) == 2
    assert loaded.find("MYLUMP").data == b"hello world"
    assert loaded.find("OTHER").data == b"\x01\x02\x03"


def test_find_missing_lump_raises():
    wad = Wad()
    try:
        wad.find("NOPE")
        assert False, "expected LumpNotFoundError"
    except LumpNotFoundError:
        pass


def test_remove_and_replace():
    wad = Wad()
    wad.add("A", b"1")
    wad.add("B", b"2")

    wad.replace("A", b"changed")
    assert wad.find("A").data == b"changed"

    wad.remove("B")
    assert "B" not in wad


def test_name_truncated_to_eight_chars():
    lump = Lump(name="TOOLONGNAME", data=b"")
    wad = Wad()
    wad.lumps.append(lump)
    data = wad.to_bytes()
    loaded = Wad.from_bytes(data)
    assert loaded.lumps[0].name == "TOOLONGN"
