# Archive reading measurements

Measured in this cloud environment using Python 3.12, 10,000 generated lumps of 1,024 bytes each. Peak numbers use tracemalloc and exclude fixture generation; they are Python allocation peaks, not process RSS.

| Reader | Lumps | Seconds | Peak Python allocation (MiB) |
| --- | ---: | ---: | ---: |
| Eager | 10000 | 0.1390 | 31.23 |
| Indexed | 10000 | 0.0905 | 2.08 |

Reproduce with `python tools/profile_wad.py`. Results vary by machine.

`WadReader` reads directory metadata once and loads payloads on demand. Use it as a context manager for large read-only archives. `Wad` remains the mutable eager API. The reader is not thread-safe and the underlying file must remain unchanged.

```python
from doomwad import WadReader
with WadReader("large.wad", max_bytes=512*1024*1024) as reader:
    print(reader.wad_type, len(reader))
    data = reader.find("PLAYPAL").data
```

The default reader limit is 512 MiB and one million lumps; patch decoding limits each image to 4,194,304 pixels. Library callers can configure those limits. Atlas processing still retains RGBA pages and patches in memory; the indexed reader does not make the editing pipeline streaming.
