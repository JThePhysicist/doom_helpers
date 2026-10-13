"""Check or update coordinated package version declarations without publishing."""
import argparse
from pathlib import Path
import re


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version',nargs='?')
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args();root=Path(__file__).resolve().parents[1]
    files=[(root/'pyproject.toml',r'^version = "([^"]+)"'),
           (root/'doomwad/__init__.py',r'^__version__ = "([^"]+)"')]
    contents=[p.read_text() for p,_ in files]
    versions=[re.search(pattern,text,re.M).group(1) for (_,pattern),text in zip(files,contents)]
    if len(set(versions))!=1: parser.error('Package version declarations disagree')
    if args.check:
        print(f'Coordinated package version: {versions[0]}');return
    if not args.version or not re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)',args.version):
        parser.error('Provide a MAJOR.MINOR.PATCH version or --check')
    for (path,pattern),text in zip(files,contents):
        match=re.search(pattern,text,re.M)
        updated=text[:match.start(1)]+args.version+text[match.end(1):]
        if not args.dry_run: path.write_text(updated)
    print(f'{"Would prepare" if args.dry_run else "Prepared"} version {args.version}; no tag or publication created')


if __name__=='__main__': main()
