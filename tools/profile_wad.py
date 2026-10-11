"""Compare eager and indexed archive reading with generated payloads."""
import argparse
from pathlib import Path
import tempfile
import time
import tracemalloc

from doomwad import Wad, WadReader


def measure(operation):
    tracemalloc.start();start=time.perf_counter()
    count=operation()
    elapsed=time.perf_counter()-start;_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    return count,elapsed,peak


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lumps',type=int,default=10000)
    parser.add_argument('--payload-bytes',type=int,default=1024)
    args=parser.parse_args()
    if args.lumps<=0 or args.payload_bytes<=0: parser.error('Sizes must be positive')
    with tempfile.TemporaryDirectory() as directory:
        path=Path(directory)/'large.wad';wad=Wad()
        for i in range(args.lumps): wad.add(f'{i:08d}',b'x'*args.payload_bytes)
        wad.save(path);del wad
        def lazy():
            with WadReader(path) as reader:
                assert reader.find('00000000').data==b'x'*args.payload_bytes
                return len(reader)
        print('| Reader | Lumps | Seconds | Peak Python allocation (MiB) |')
        print('| --- | ---: | ---: | ---: |')
        for name,operation in [('Eager',lambda:len(Wad.load(path))),('Indexed',lazy)]:
            count,elapsed,peak=measure(operation)
            print(f'| {name} | {count} | {elapsed:.4f} | {peak/1024/1024:.2f} |')


if __name__=='__main__': main()
