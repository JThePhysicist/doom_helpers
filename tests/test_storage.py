import os

import pytest

from doomwad.storage import atomic_batch, atomic_write


def test_exclusive_write_and_atomic_replacement(tmp_path):
    path = tmp_path / 'output'
    atomic_write(path, b'original', overwrite=False)
    with pytest.raises(FileExistsError): atomic_write(path, b'new', overwrite=False)
    assert path.read_bytes() == b'original'
    atomic_write(path, b'new')
    assert path.read_bytes() == b'new'
    assert list(tmp_path.iterdir()) == [path]


def test_failed_replace_preserves_original_and_cleans_staging(tmp_path, monkeypatch):
    path = tmp_path / 'output';path.write_bytes(b'original')
    def fail(*args): raise OSError('disk failure')
    monkeypatch.setattr(os, 'replace', fail)
    with pytest.raises(OSError): atomic_write(path, b'new')
    assert path.read_bytes() == b'original'
    assert list(tmp_path.iterdir()) == [path]


def test_batch_rolls_back_successful_earlier_file(tmp_path, monkeypatch):
    a, b = tmp_path / 'a', tmp_path / 'b'
    a.write_bytes(b'old-a');b.write_bytes(b'old-b')
    replace = os.replace
    def fail_once(source, target):
        if target == b: raise OSError('second write failed')
        return replace(source, target)
    monkeypatch.setattr(os, 'replace', fail_once)
    with pytest.raises(OSError): atomic_batch([(a,b'new-a'),(b,b'new-b')], overwrite=True)
    assert a.read_bytes() == b'old-a' and b.read_bytes() == b'old-b'
    assert sorted(p.name for p in tmp_path.iterdir()) == ['a','b']
