"""Stage complete files beside their targets before committing replacements."""
import os
from pathlib import Path
import tempfile


def atomic_write(path, data, *, overwrite=True):
    path = Path(path)
    staged = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f'.{path.name}.', delete=False) as stream:
            staged = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if overwrite:
            os.replace(staged, path)
        else:
            # Linking creates the destination exclusively, avoiding a check/write race.
            os.link(staged, path)
            staged.unlink()
        staged = None
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)


def atomic_batch(files, *, overwrite=False):
    """Rollback this process's replacements on failure; not a crash-atomic transaction."""
    files = [(Path(path), data) for path, data in files]
    if len({path for path, _ in files}) != len(files):
        raise ValueError('Output paths must be unique')
    backups = {path: path.read_bytes() if path.exists() else None for path, _ in files}
    if not overwrite and any(data is not None for data in backups.values()):
        raise FileExistsError('Output files exist; pass --overwrite to replace them')
    written = []
    try:
        for path, data in files:
            atomic_write(path, data, overwrite=overwrite)
            written.append(path)
    except BaseException:
        for path in reversed(written):
            old = backups[path]
            if old is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write(path, old)
        raise
